"""Fresh matched vote-preserving random/shuffle and explicit oracle controls.

Work metrics only. Reference search is recorded separately and is never passed
to a real model. Random endpoint bijections preserve the entire overlap/vote
structure of the genuine response, avoiding a weak low-consensus random control.
"""
import argparse
import gzip
import importlib.util
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from hybrid import ROOT
from llmastar.research.hybrid_guidance import HybridWaypointPlanner,normalize_routes
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import compress_collinear
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.strategic.schema import StrategicGuidance,Strategy

spec=importlib.util.spec_from_file_location('session6_control_heap',Path(__file__).with_name('evaluate.py'))
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seeds',type=int,default=10);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases=json.load(gzip.open(a.root/'heldout_factorial.json.gz','rt'))
    responses={r['case_id']:r for r in json.load(gzip.open(a.root/'heldout_hybrid/responses.json.gz','rt'))['runs']}
    rows=[];reference_work=[]
    for c in cases:
        q=c['query'];response=responses[c['id']];g=SegmentGridGraph(q)
        routes=normalize_routes({'routes':response['meta'].get('routes') or [response['points']]},g)
        start,goal=tuple(q['start']),tuple(q['goal'])
        unique=list(dict.fromkeys(p for r in routes for p in r if p not in [start,goal]))
        pool=list(dict.fromkeys(tuple(p) for p in response['proposal']['points'].values()))
        ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],g)
        oracle=compress_collinear(ref['path'])
        reference_work.append({'case_id':c['id'],'operation':ref['operation'],'unique':ref['unique']})
        modes=['real','geometry','all_endpoints','shuffled','random_endpoint','random_free','oracle_same_engine','oracle_verified_incumbent']
        for mode in modes:
            for seed in range(a.seeds if mode in ['shuffled','random_endpoint','random_free'] else 1):
                rng=random.Random(f'heldout-votes:{c["id"]}:{seed}')
                advice=[list(r) for r in routes];kwargs={}
                if mode=='geometry':kwargs['source']='geometry_consensus'
                elif mode=='all_endpoints':kwargs['source']='all_endpoints'
                elif mode=='shuffled':
                    for route in advice:rng.shuffle(route)
                elif mode in ['random_endpoint','random_free']:
                    if mode=='random_endpoint':sample=rng.sample(pool,min(len(unique),len(pool)))
                    else:
                        sample=[]
                        while len(sample)<len(unique):
                            p=(rng.randrange(g.x0+1,g.x1),rng.randrange(g.y0+1,g.y1))
                            if g.valid_point(p) and p not in sample and p not in [start,goal]:sample.append(p)
                    mapping=dict(zip(unique,sample));advice=[[mapping.get(p,p) for p in r] for r in routes]
                elif mode=='oracle_same_engine':advice=[oracle,oracle,oracle]
                graph=SegmentGridGraph(q)
                with evaluation.heap_audit(True) as counts:
                    if mode=='oracle_verified_incumbent':
                        guidance=StrategicGuidance((Strategy('explicit_optimal_oracle',waypoints=tuple(oracle)),),'oracle')
                        r=CutStrategySearch(bound=2).search(q,StaticProvider(guidance,'oracle'),graph)
                    else:r=HybridWaypointPlanner(**kwargs).search(q,routes={'routes':advice})
                assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
                rows.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],
                    'mode':mode,'seed':seed,'pops':counts['pop'],'pushes':counts['push'],
                    'queue_operations':counts['pop']+counts['push'],'unique':r.get('unique_total',r.get('unique',0)),
                    'cost_ratio':r['length']/c['optimal_cost'],'valid':r['valid'],
                    'geometry_gate':response['meta'].get('api_skipped',False)})
        print(c['id'],'controls completed',flush=True)
    summary={}
    for mode in modes:
        rr=[r for r in rows if r['mode']==mode]
        summary[mode]={'trials':len(rr),'valid':sum(r['valid'] for r in rr),
            'mean_pops':statistics.mean(r['pops'] for r in rr),
            'mean_unique':statistics.mean(r['unique'] for r in rr),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr))}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'scope':'Forty predeclared query/map cases; ten random seeds are not independent maps. All model guidance fixed. Oracle reference-generation work excluded from oracle planning counters and explicitly recorded; no oracle data enters any API request.','summary':summary,'runs':rows,'oracle_reference_work':reference_work},f)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
