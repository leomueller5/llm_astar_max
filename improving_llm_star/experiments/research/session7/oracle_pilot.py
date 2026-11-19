"""Representation/architecture ceiling before paid spatial advice experiments."""
import argparse,random,statistics,math
from time import perf_counter
from common import read_cases,dump
from oracle import remaining_costs,regional_reference,FineOracle
from llmastar.research.spatial_guidance import SpatialSearch,RegionField
from llmastar.research.hybrid_guidance import HybridWaypointPlanner

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases=read_cases(a.cases);rows=[];refs=[]
    for c in cases:
        q=c['query'];costs,work=remaining_costs(q);refs.append(dict(case_id=c['id'],**work));assert abs(costs[tuple(q['start'])]-c['optimal_cost'])<1e-7
        for kind in ['octile','cut']:
            coarse=regional_reference(q,4,costs,kind);fine=FineOracle(q,costs,kind)
            rng=random.Random(c['id']);randomfield=RegionField(q,4)
            randomfield.update([{'region_id':r['id'],'detour':rng.random()*math.hypot(randomfield.width,randomfield.height)*.5,'priority':rng.random(),'confidence':1.} for r in randomfield.regions])
            noisy=regional_reference(q,4,costs,kind,noise=.1,seed=761)
            for fieldname,field in [('none',None),('oracle4',coarse),('oracle_fine',fine),('noisy_oracle4',noisy),('random4',randomfield)]:
                for mode,signal,weight in [('envelope','detour',1.),('envelope','priority',1.5),('focal','priority',1.),('tie','detour',1.5)]:
                    tick=perf_counter();r=SpatialSearch(mode=mode,base_weight=weight,heuristic=kind,signal=signal).search(q,field);elapsed=perf_counter()-tick
                    assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
                    rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=f'{kind}_{mode}_{signal}_{fieldname}',pops=r['heap_pops'],pushes=r['heap_pushes'],unique=r['unique'],expanded=r['expanded'],seconds=elapsed,cost_ratio=r['length']/c['optimal_cost'],valid=r['valid']))
            for w in [1.,1.05,1.5,2.]:
                r=SpatialSearch(mode='weighted',base_weight=w,heuristic=kind).search(q)
                rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=f'{kind}_weighted{w}',pops=r['heap_pops'],pushes=r['heap_pushes'],unique=r['unique'],expanded=r['expanded'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost'],valid=r['valid']))
        for source in ['all_endpoints','geometry_consensus']:
            r=HybridWaypointPlanner(source=source).search(q)
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method='vm_'+source,pops=r['total_heap_pops'],pushes=r['total_heap_pushes'],unique=r['unique'],expanded=r['expanded'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost'],valid=r['valid']))
        print(c['id'],'oracle architecture pilot complete',flush=True)
    summary={}
    for m in sorted({r['method'] for r in rows}):
        rr=[r for r in rows if r['method']==m];summary[m]={'mean_pops':statistics.mean(r['pops'] for r in rr),'mean_unique':statistics.mean(r['unique'] for r in rr),'mean_ms':1000*statistics.mean(r['seconds'] for r in rr),'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr))}
    dump(a.output,{'scope':'Development representation/architecture ceiling. Exact reverse-Dijkstra and oracle fields are offline diagnostics, never supplied to actual models; their work is separately recorded. Single native timing per pilot only.','summary':summary,'runs':rows,'reference_generation':refs})
    for m,v in summary.items():print(m,round(v['mean_pops'],1),round(v['mean_unique'],1),round(v['gm_cost_ratio'],4))
if __name__=='__main__':main()
