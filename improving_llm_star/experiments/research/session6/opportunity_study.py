"""Predeclared adaptive macro-opportunity ablations, no network calls."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import random
import shutil
import statistics
from pathlib import Path
from time import perf_counter

from hybrid import portfolio,ROOT,clean
from strategic import strict_messages
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.macro_guidance import MacroGuidedSearch

spec=importlib.util.spec_from_file_location('session6_opportunity_heap',Path(__file__).with_name('evaluate.py'))
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)

CONFIGS={'given':{},'regret':{'target_order':'regret'},
         'portfolio_given':{},'portfolio_regret':{'target_order':'regret'},
         'consensus':{},'consensus_rank':{},
         'priority_descent':{'target_order':'priority','require_descent':True},
         'adaptive_descent':{'target_order':'adaptive','require_descent':True},
         'portfolio_priority':{'target_order':'priority','require_descent':True},
         'portfolio_adaptive':{'target_order':'adaptive','require_descent':True}}


def run(case,response,config,source,weight=2.):
    began=perf_counter();q=case['query'];grid=SegmentGridGraph(q)
    proposal=portfolio(q,grid);geometry_seconds=perf_counter()-began
    gate=proposal['candidates'][0]['failed_links']==0
    if source=='llm':
        points=response['points']
        routes=response['meta'].get('routes') or [points]
        if not gate:strict_messages(q,proposal,'multi_strict')
    elif source=='geometry':
        points=proposal['geometry_best'];routes=[r['route'] for r in proposal['candidates'][:3]]
    elif source=='all':
        points=list(proposal['points'].values());routes=[points]
    elif source=='none':
        points=[];routes=[]
    else:
        raise ValueError(source)
    # Every matched source uses identical verified geometric advice on easy cases.
    if gate and source in ['llm','geometry','all']:
        points=proposal['geometry_best'];routes=[points]
    if config.startswith('portfolio'):
        points=[route[i] for i in range(max(map(len,routes),default=0)) for route in routes if i<len(route)]
    elif config in ['consensus','consensus_rank']:
        votes={};positions={};order={}
        for route in routes:
            seen=set()
            for i,raw in enumerate(route):
                p=tuple(raw)
                if p in seen:continue
                seen.add(p);order.setdefault(p,len(order));votes[p]=votes.get(p,0)+1
                positions[p]=positions.get(p,0.)+i
        if config=='consensus':
            points=[p for p in order if votes[p]>=len(routes)//2+1]
        else:
            points=sorted(order,key=lambda p:(-votes[p],positions[p]/votes[p],order[p]))
    r=MacroGuidedSearch(weight=weight,heuristic='cut',**CONFIGS[config]).search(q,points,grid)
    elapsed=perf_counter()-began;path=r.pop('path',[]);r.pop('trace',None);r.pop('events',None)
    if r['valid']:
        assert r['length']<=weight*case['optimal_cost']+1e-7
        assert abs(r['length']-sum(math.dist(a,b) for a,b in zip(path,path[1:])))<1e-7
        assert all(math.isfinite(grid.cost(a,b)) for a,b in zip(path,path[1:]))
    r.update(seconds=elapsed,geometry_seconds=geometry_seconds,geometry_gate=gate,
        cost_ratio=r['length']/case['optimal_cost'] if r['valid'] else None)
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--configs',nargs='+',default=list(CONFIGS))
    p.add_argument('--sources',nargs='+',default=['llm','geometry','all','none'])
    p.add_argument('--weight',type=float,default=2.);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    inputs=json.load(gzip.open(a.responses,'rt'))['runs']
    source_files=[Path(__file__),Path(__file__).with_name('hybrid.py'),ROOT/'llmastar/research/macro_guidance.py']
    manifest={}
    for source in source_files:
        dest=a.output/'sources'/source.relative_to(ROOT.parent);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest);manifest[str(source.relative_to(ROOT.parent))]=hashlib.sha256(source.read_bytes()).hexdigest()
    (a.output/'manifest.json').write_text(json.dumps({'sources':manifest,'args':vars(a)},default=str,indent=2))
    rng=random.Random(66861);rows=[];choices=[(c,s) for c in a.configs for s in a.sources]
    for response in inputs:
        case=cases[response['case_id']]
        for config,source in choices:run(case,response,config,source,a.weight)
        for rep in [-1]+list(range(a.repeats)):
            order=list(choices);rng.shuffle(order)
            for config,source in order:
                with evaluation.heap_audit(rep==-1) as counts:r=run(case,response,config,source,a.weight)
                rows.append(dict(r,case_id=case['id'],map_id=case['map_id'],family=case['family'],
                    config=config,source=source,rep=rep,audit=counts if rep==-1 else None))
        if len(rows)//len(choices)%10==0:print(case['id'],'completed',flush=True)
        with gzip.open(a.output/'checkpoint.json.gz','wt') as f:json.dump({'runs':rows},f)
    summary={}
    for config,source in choices:
        rr=[r for r in rows if (r['config'],r['source'])==(config,source)];one=[r for r in rr if r['rep']==-1]
        summary[config+'/'+source]={'cases':len(one),'valid':sum(r['valid'] for r in one),
            'mean_ms':1000*statistics.mean(statistics.median(r['seconds'] for r in rr if r['case_id']==c['case_id'] and r['rep']>=0) for c in one),
            'mean_heap_pops':statistics.mean(r['audit']['pop'] for r in one),
            'mean_heap_pushes':statistics.mean(r['audit']['push'] for r in one),
            'mean_search_pops':statistics.mean(r['heap_pops'] for r in one),
            'mean_unique':statistics.mean(r['unique'] for r in one),
            'mean_probes':statistics.mean(r['macro_probes'] for r in one),
            'mean_trust_updates':statistics.mean(r['trust_updates'] for r in one),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in one if r['valid'])),
            'max_cost_ratio':max(r['cost_ratio'] for r in one if r['valid'])}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'runs':rows,'summary':summary},f)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2))
    drift=[name for name,h in manifest.items() if hashlib.sha256((ROOT.parent/name).read_bytes()).hexdigest()!=h]
    (a.output/'source_drift.json').write_text(json.dumps(drift))


if __name__=='__main__':main()
