"""Cold roadmap completion benchmark, including matched geometric controls."""
import argparse
import gzip
import importlib.util
import itertools
import json
import math
import random
import statistics
from pathlib import Path
from time import perf_counter

from hybrid import ROOT
from roadmap import Roadmap,complete_routes,roadmap_messages
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.search import octile

spec=importlib.util.spec_from_file_location('session6_heap',Path(__file__).with_name('evaluate.py'))
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)


def run(case,response,mode):
    tick=perf_counter();q=case['query'];grid=SegmentGridGraph(q);s,t=tuple(q['start']),tuple(q['goal'])
    grid_closed=set();original_adj=grid.adj
    class Recorder:
        def get(self,node,default=None):grid_closed.add(node);return original_adj.get(node,default)
    grid.adj=Recorder()
    geometry=completion=0.;candidate=None;roadmap=None;unknown=0;new_edges=0;candidate_cost=None
    if mode!='cut_only':
        k=8 if mode=='geometry8' else None if mode=='geometry_full' else 4
        roadmap=Roadmap(q,grid,k=k);initial=roadmap.shortest();geometry=perf_counter()-tick
        if mode in ['llm','graph_only']:
            roadmap_messages(q,roadmap.proposal(initial),'complete' if mode=='llm' else 'graph_only')
            candidates,unknown=complete_routes(roadmap,response['routes'])
            new_edges=sum(1 for row in candidates if row['valid'])
        elif mode in ['random_complete','greedy_complete','lazy_matched','lazy_full']:
            known=set(roadmap.status)
            pairs={tuple(sorted((a,b))) for raw in response['routes'][:2] if isinstance(raw,list)
                   for a,b in zip(raw,raw[1:]) if a in roadmap.points and b in roadmap.points and a!=b}
            unknown=len(pairs-known)
            if mode.startswith('lazy'):
                roadmap.lazy_augment(len(roadmap.points)**2 if mode=='lazy_full' else unknown)
            else:
                pool=[p for p in itertools.combinations(roadmap.points,2) if tuple(sorted(p)) not in known]
                if mode=='random_complete':random.Random('s6roadmap'+case['id']).shuffle(pool)
                else:
                    pool.sort(key=lambda ab:min(octile(s,roadmap.points[ab[0]])+octile(roadmap.points[ab[0]],roadmap.points[ab[1]])+octile(roadmap.points[ab[1]],t),
                        octile(s,roadmap.points[ab[1]])+octile(roadmap.points[ab[1]],roadmap.points[ab[0]])+octile(roadmap.points[ab[0]],t)))
                for a,b in pool[:unknown]:roadmap.verify(a,b)
        ids,candidate_cost,work=roadmap.shortest()
        candidate=[roadmap.points[i] for i in ids]
        completion=perf_counter()-tick-geometry
    cut=CutPotential(q,t);lower=cut.value(s)
    certified=bool(candidate) and candidate_cost<=1.05*lower+1e-9
    if certified:
        path=roadmap.dense_path(ids)
        result={'valid':True,'length':candidate_cost,'expanded':0,'operation':0,'unique':0,'storage':0,'accepted_source':'roadmap_certificate'}
    else:
        provider=StaticProvider({'strategies':[{'id':'roadmap','waypoints':candidate}]},'roadmap') if candidate else None
        result=CutStrategySearch(bound=1.05).search(q,provider,grid)
        path=result.pop('path',[])
        if result.get('accepted_source')=='grid_search':grid_closed.add(t)
    elapsed=perf_counter()-tick
    if result['valid']:
        assert path and path[0]==s and path[-1]==t
        assert abs(result['length']-sum(math.dist(a,b) for a,b in zip(path,path[1:])))<1e-7
        assert all(math.isfinite(grid.cost(a,b)) for a,b in zip(path,path[1:]))
        assert result['length']<=1.05*case['optimal_cost']+1e-7
    abstract=roadmap.expanded_points if roadmap else set()
    return {'valid':result['valid'],'length':result['length'],'cost_ratio':result['length']/case['optimal_cost'] if result['valid'] else None,
        'seconds':elapsed,'geometry_seconds':geometry,'completion_seconds':completion,
        'unique_grid':len(grid_closed),'unique_abstract':len(abstract),'unique_union':len(grid_closed|abstract),
        'grid_pops':result.get('operation',0),'grid_expanded':result.get('expanded',0),
        'visibility_probes':roadmap.probes if roadmap else 0,'new_visibility_budget':unknown,
        'valid_llm_routes':new_edges,'candidate_cost':candidate_cost if candidate_cost and math.isfinite(candidate_cost) else None,
        'certificate':certified,'accepted_source':result.get('accepted_source')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=5);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    inputs=json.load(gzip.open(a.responses,'rt'))['runs'];rng=random.Random(18611);rows=[]
    for response in inputs:
        if response['prompt']!='complete':continue
        case=cases[response['case_id']]
        modes=['llm','geometry4','geometry8','geometry_full','random_complete','greedy_complete','lazy_matched','lazy_full','cut_only']
        for mode in modes:run(case,response,mode)
        for rep in [-1]+list(range(a.repeats)):
            order=list(modes);rng.shuffle(order)
            for mode in order:
                with evaluation.heap_audit(rep==-1) as counts:r=run(case,response,mode)
                rows.append(dict(r,case_id=case['id'],map_id=case['map_id'],mode=mode,rep=rep,audit=counts if rep==-1 else None,
                    api_skipped=response.get('api_skipped',False)))
        print(case['id'],'completed',flush=True)
    summary={}
    for mode in modes:
        rr=[r for r in rows if r['mode']==mode];one=[r for r in rr if r['rep']==-1]
        summary[mode]={'cases':len(one),'valid':sum(r['valid'] for r in one),
            'mean_ms':1000*statistics.mean(statistics.median(r['seconds'] for r in rr if r['case_id']==c['case_id'] and r['rep']>=0) for c in one),
            'mean_heap_pops':statistics.mean(r['audit']['pop'] for r in one),
            'mean_heap_pushes':statistics.mean(r['audit']['push'] for r in one),
            'mean_unique_union':statistics.mean(r['unique_union'] for r in one),
            'mean_probes':statistics.mean(r['visibility_probes'] for r in one),
            'certificates':sum(r['certificate'] for r in one),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in one if r['valid']))}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'summary':summary,'runs':rows},f)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
