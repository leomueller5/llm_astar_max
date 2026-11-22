"""Frozen secondary test: identical ungated portfolios for all advisory controls."""
import argparse,gzip,json,random,statistics,math
from pathlib import Path
from time import perf_counter
import numpy as np
from final_benchmark import CachedProvider,evaluation
from llmastar.research.hybrid_guidance import HybridWaypointPlanner,normalize_routes
from llmastar.research.geometry import SegmentGridGraph

class Provider:
    def __init__(self,mode,row,seed):self.mode=mode;self.row=row;self.seed=seed
    def propose(self,q,c):
        if self.mode=='geometry_best':return [c['geometry_best']]
        if self.mode=='geometry_consensus':return [r['route'] for r in c['candidates'][:3]]
        if self.mode=='all_endpoints':return [list(c['points'].values())]
        real=CachedProvider(self.row).propose(q,c)
        if self.mode=='random_endpoint':
            routes=normalize_routes(real,SegmentGridGraph(q)); ends=[tuple(q['start']),tuple(q['goal'])]
            unique=list(dict.fromkeys(p for r in routes for p in r if p not in ends))
            pool=list(dict.fromkeys(tuple(p) for p in c['points'].values()))
            rng=random.Random(f'{self.row["case_id"]}:{self.seed}')
            mapping=dict(zip(unique,rng.sample(pool,len(unique))))
            return [[mapping.get(p,p) for p in r] for r in routes]
        return real

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True)
    cases=json.load(gzip.open(a.cases,'rt'));responses={r['case_id']:r for r in json.load(gzip.open(a.responses,'rt'))['runs']};rows=[]
    for c in cases:
        tasks=[(m,s) for m in ['real','geometry_best','geometry_consensus','all_endpoints','random_endpoint'] for s in range(5 if m=='random_endpoint' else 1)]
        random.Random(c['id']).shuffle(tasks)
        for mode,seed in tasks:
            provider=Provider(mode,responses[c['id']],seed)
            planner=HybridWaypointPlanner(provider=provider,source='hybrid_always')
            planner.search(c['query'])
            times=[]
            for _ in range(5):
                t=perf_counter();r=planner.search(c['query']);times.append(perf_counter()-t)
            with evaluation.heap_audit(True) as counts:r=planner.search(c['query'])
            assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],mode=mode,seed=seed,pops=counts['pop'],pushes=counts['push'],unique=r['unique'],cost_ratio=r['length']/c['optimal_cost'],seconds=statistics.median(times),valid=r['valid']))
        print(c['id'],'matched ungated complete',flush=True)
    summary={};paired={};rng=np.random.default_rng(2026111906)
    for mode in sorted(set(r['mode'] for r in rows)):
        rr=[r for r in rows if r['mode']==mode]
        bycase={c['id']:[r for r in rr if r['case_id']==c['id']] for c in cases}
        mean=lambda key:statistics.mean(statistics.mean(r[key] for r in group) for group in bycase.values())
        summary[mode]=dict(valid=sum(r['valid'] for r in rr),trials=len(rr),mean_pops=mean('pops'),mean_seconds=mean('seconds'),gm_cost_ratio=math.exp(statistics.mean(statistics.mean(math.log(r['cost_ratio']) for r in g) for g in bycase.values())))
        if mode!='real':
            d={}
            for key in ['pops','seconds','cost_ratio']:
                x=np.array([next(r[key] for r in rows if r['case_id']==c['id'] and r['mode']=='real') for c in cases]);y=np.array([statistics.mean(r[key] for r in bycase[c['id']]) for c in cases]);ix=rng.integers(0,len(cases),(4000,len(cases)));ratios=x[ix].mean(1)/y[ix].mean(1)
                d[key]={'ratio_of_means':float(x.mean()/y.mean()),'paired_map_bootstrap_ci95':np.quantile(ratios,[.025,.975]).tolist()}
            paired[mode]=d
    result={'scope':'Secondary preregistered follow-up, twenty new map-disjoint geometries. No primary candidate changes. All modes bypass the same geometry validity gate. Offline cached model replay; random seeds averaged within case, maps are bootstrap units. Nominal confidence intervals, no multiplicity adjustment.','summary':summary,'paired_real_over_control':paired,'runs':rows}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(result,f)
    (a.output/'summary.json').write_text(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))
if __name__=='__main__':main()
