"""Search-work ablations with quality-matched random and oracle guidance.

No timing claims: runs are heap-instrumented. Geometry-gated easy cases receive
identical geometry in every control. Random seeds vary advice, not maps.
"""
import argparse
import gzip
import importlib.util
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from hybrid import ROOT,clean
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile
from llmastar.research.efficient import compress_collinear

spec=importlib.util.spec_from_file_location('session6_evaluate',Path(__file__).with_name('evaluate.py'))
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)


def bootstrap(rows,a,b,metric='pops',samples=2000):
    by=defaultdict(dict)
    for r in rows:
        by[r['case_id']].setdefault(r['control'],[]).append(r)
    groups=defaultdict(list)
    for cid,data in by.items():
        if a in data and b in data:
            groups[data[a][0]['map_id']].append((statistics.mean(x[metric] for x in data[a]),statistics.mean(x[metric] for x in data[b])))
    keys=list(groups);rng=random.Random(202611186);values=[]
    for _ in range(samples):
        pairs=[p for k in rng.choices(keys,k=len(keys)) for p in groups[k]]
        values.append(sum(x for x,y in pairs)/max(1e-12,sum(y for x,y in pairs)))
    values.sort();pairs=[p for v in groups.values() for p in v]
    return {'ratio_of_means':sum(x for x,y in pairs)/max(1e-12,sum(y for x,y in pairs)),
            'ci95':[values[int(.025*samples)],values[int(.975*samples)]],
            'maps':len(groups),'cases':len(by)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--seeds',type=int,default=10)
    p.add_argument('--method',default='macro_cut');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    responses=json.load(gzip.open(a.responses,'rt'))['runs'];runs=[]
    evaluation.replay.BACKEND='installed'
    Original=evaluation.replay.load_planner(evaluation.WORKSPACE/'llm-astar',response='')
    for response in responses:
        case=cases[response['case_id']];q=case['query'];proposal=response['proposal']
        graph=SegmentGridGraph(q);points=clean(q,response['points'],graph)[1:-1]
        n=len(points);pool=list(proposal['points'].values());gate=response['meta'].get('api_skipped',False)
        potential=CutPotential(q,tuple(q['goal']))
        geometric=proposal['geometry_best'];start,goal=tuple(q['start']),tuple(q['goal'])
        reference=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],graph)
        oracle=compress_collinear(reference['path'])
        deterministic={'llm':points,'geometry':geometric,'none':[],
            'cheap_regret':sorted(pool,key=lambda t:(octile(start,t)+potential.value(t),t))[:n],
            'far_detour':sorted(pool,key=lambda t:(-octile(start,t)-octile(t,goal),t))[:n],
            'oracle_full':oracle}
        for control in ['llm','geometry','none','cheap_regret','far_detour','oracle_full','shuffled','random_endpoint','random_free']:
            for seed in range(a.seeds if control in ['shuffled','random_endpoint','random_free'] else 1):
                rng=random.Random(f's6:{case["id"]}:{seed}')
                if control in deterministic:advice=deterministic[control]
                elif control=='shuffled':advice=list(points);rng.shuffle(advice)
                elif control=='random_endpoint':advice=rng.sample(pool,min(n,len(pool)))
                else:
                    advice=[]
                    while len(advice)<n:
                        t=(rng.randrange(graph.x0+1,graph.x1),rng.randrange(graph.y0+1,graph.y1))
                        if graph.valid_point(t) and t not in advice and t not in [start,goal]:advice.append(t)
                if gate and control not in ['none','oracle_full']:
                    advice=geometric
                with evaluation.heap_audit(True) as counts:
                    r=evaluation.execute(case,advice,a.method,Original,{},'multi_strict')
                runs.append({'case_id':case['id'],'map_id':case['map_id'],'family':case['family'],
                    'control':control,'seed':seed,'geometry_gate':gate,'target_count':n,
                    'valid':r['valid'],'pops':counts['pop'],'pushes':counts['push'],
                    'queue_operations':counts['pop']+counts['push'],
                    'unique':r.get('unique_total',r.get('unique',0)),
                    'cost_ratio':r['length']/case['optimal_cost'] if r['valid'] else None,
                    'macro_probes':r.get('macro_probes',0)})
        print(case['id'],'completed',flush=True)
    summary={}
    for control in deterministic.keys() | {'shuffled','random_endpoint','random_free'}:
        rr=[r for r in runs if r['control']==control]
        summary[control]={'trials':len(rr),'valid':sum(r['valid'] for r in rr),
            'mean_pops':statistics.mean(r['pops'] for r in rr),
            'mean_unique':statistics.mean(r['unique'] for r in rr),
            'mean_queue_operations':statistics.mean(r['queue_operations'] for r in rr),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr if r['valid']))}
    comparisons={b:bootstrap(runs,'llm',b) for b in ['geometry','cheap_regret','shuffled','random_endpoint','random_free']}
    for b in ['geometry','random_endpoint','shuffled']:
        comparisons[b+'_hard_only']=bootstrap([r for r in runs if not r['geometry_gate']],'llm',b)
    data={'method':a.method,'scope':'Heap-instrumented work only. Ten advice seeds averaged within each case before map-cluster bootstrap. Oracle receives an optimal reference path and is explicitly not real LLM guidance. Geometry gate held identical across controls.','summary':summary,'comparisons':comparisons,'runs':runs}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(data,f)
    (a.output/'summary.json').write_text(json.dumps({'summary':summary,'comparisons':comparisons},indent=2))


if __name__=='__main__':main()
