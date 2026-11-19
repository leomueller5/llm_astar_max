"""Offline oracle ceiling for query-specific policy/direction selection."""
import argparse,statistics,math,random
from time import perf_counter
from common import read_cases,dump
from examples import features
from llmastar.research.spatial_guidance import SpatialSearch
from llmastar.research.hybrid_guidance import HybridWaypointPlanner
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch

def reverse_query(q):return dict(q,start=q['goal'],goal=q['start'])
def local_volume(q,start,radius=8):
    g=SegmentGridGraph(q);seen={tuple(start)};front=list(seen)
    for _ in range(radius):
        nxt=[]
        for p in front:
            for n,c in g.adj.get(p,[]):
                if n not in seen:seen.add(n);nxt.append(n)
        front=nxt
    return len(seen)

def run(q,method):
    if method.startswith('vm'):return HybridWaypointPlanner(source='all_endpoints',weight=1.05 if method.endswith('105') else 2.).search(q)
    if method=='witness':return EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,fallback_engine='lean',reuse_validation=True).search(q,[],SegmentGridGraph(q))
    kind='octile' if method.startswith('octile') else 'cut';w=1 if method.endswith('_1') else 1.05 if method.endswith('_105') else 2.
    return SpatialSearch(mode='weighted',base_weight=w,heuristic=kind).search(q)

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=3);a=p.parse_args();rows=[];selection=[]
    for c in read_cases(a.cases):
        q=c['query'];policies=[f'{m}/{d}' for m in ['cut_1','cut_105','cut_2','octile_2','vm2','vm105','witness'] for d in ['forward','reverse']];random.Random(c['id']).shuffle(policies);local={d:local_volume(q,q['start'] if d=='forward' else q['goal']) for d in ['forward','reverse']}
        for policy in policies:
            method,direction=policy.split('/');qq=q if direction=='forward' else reverse_query(q);run(qq,method);times=[]
            for _ in range(a.repeats):
                t=perf_counter();r=run(qq,method);times.append(perf_counter()-t)
            assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],policy=policy,pops=r.get('total_heap_pops',r.get('heap_pops',r['operation'])),unique=r['unique'],seconds=statistics.median(times),cost_ratio=r['length']/c['optimal_cost']))
        rr=[r for r in rows if r['case_id']==c['id']];selection.append(dict(case_id=c['id'],family=c['family'],features=features(q),local_volume=local,best_ms_policy=min(rr,key=lambda r:r['seconds'])['policy'],best_cut_pops_direction=min([r for r in rr if r['policy'].startswith('cut_105/')],key=lambda r:r['pops'])['policy'].split('/')[1]))
        print(c['id'],'policy/direction ceiling',flush=True)
    summaries={}
    for policy in sorted({r['policy'] for r in rows}):
        rr=[r for r in rows if r['policy']==policy];summaries[policy]=dict(mean_pops=statistics.mean(r['pops'] for r in rr),mean_ms=1000*statistics.mean(r['seconds'] for r in rr),gm_cost_ratio=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    oracle={}
    for metric in ['pops','seconds']:
        for pool in ['cut_105','cut_2','all']:
            groups=[[r for r in rows if r['case_id']==s['case_id'] and (pool=='all' or r['policy'].startswith(pool+'/'))] for s in selection]
            oracle[pool+'/'+metric]=statistics.mean(min(g,key=lambda r:r[metric])[metric] for g in groups)
    dump(a.output,{'scope':'Development oracle ceiling only, no model. Every policy is a genuine independent run with fresh preprocessing. Reverse direction valid because original graph is undirected. Oracle policy selection uses observed outcomes and cannot be deployed as a predictor.','summary':summaries,'oracle_mean_metric':oracle,'selection':selection,'runs':rows});print(summaries);print(oracle)
if __name__=='__main__':main()
