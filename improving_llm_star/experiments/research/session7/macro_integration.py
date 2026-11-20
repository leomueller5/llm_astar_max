"""Same geometric macro engine, new model costs for priority or probe allocation."""
import argparse,math,statistics
from common import read_cases,dump
from prompts_spatial import decode
from cost_controls import Scaled
from evaluate import permuted
from llmastar.research.spatial_guidance import SpatialSearch
from llmastar.research.hybrid_guidance import HybridWaypointPlanner
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.geometric_advice import portfolio

def plan(q,field=None,base=2.,bound=2.,order='given',mode='weighted'):
    from time import perf_counter
    began=perf_counter();graph=SegmentGridGraph(q);candidates=portfolio(q,graph,budget=12)
    gate=bool(candidates['candidates']) and candidates['candidates'][0]['failed_links']==0
    targets=candidates['geometry_best'] if gate else list(candidates['points'].values())
    r=SpatialSearch(mode=mode,bound=bound,base_weight=base,macro=True,target_order=order).search(q,field,graph,targets)
    r.update(total_heap_pops=r['heap_pops']+candidates['heap_pops'],total_heap_pushes=r['heap_pushes']+candidates['heap_pushes'],total_seconds=perf_counter()-began,candidate_gate=gate);return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alpha=read_cases(a.coefficients)['full_development_alpha']['image'];rows=[]
    for rr in read_cases(a.responses)['runs']:
        if rr['representation']!='image':continue
        c=cases[rr['case_id']];q=c['query'];raw,_=decode(q,rr['response']['choices'][0]['message']['content'],4,'cost');f=Scaled(raw,alpha);shuffled=Scaled(permuted(raw,c['id']),alpha)
        for method,field,base,bound,order,mode in [('vm2',None,2.,2.,'given','weighted'),('vm105',None,1.05,1.05,'given','weighted'),('rank2_geo',None,2.,2.,'cost','weighted'),('rank2_real',f,2.,2.,'cost','weighted'),('rank2_shuffled',shuffled,2.,2.,'cost','weighted'),('rank105_geo',None,1.05,1.05,'cost','weighted'),('rank105_real',f,1.05,1.05,'cost','weighted'),('spatial_macros',f,1.,2.,'given','heuristic_envelope'),('tight_spatial_macros',f,1.,1.05,'given','heuristic_envelope'),('spatial_ranked',f,1.,2.,'cost','heuristic_envelope')]:
            r=plan(q,field,base,bound,order,mode)
            if method in ['vm2','vm105']:
                original=HybridWaypointPlanner(source='all_endpoints',weight=base).search(q)
                assert r['total_heap_pops']==original['total_heap_pops'] and r['total_heap_pushes']==original['total_heap_pushes'] and abs(r['length']-original['length'])<1e-7,(c['id'],method,'engine parity mismatch')
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=method,pops=r['total_heap_pops'],pushes=r['total_heap_pushes'],queue_operations=r['total_heap_pops']+r['total_heap_pushes'],unique=r['unique'],cost_ratio=r['length']/c['optimal_cost'],seconds=r['total_seconds']))
        print(c['id'],'frozenVM parity + model macro allocation',flush=True)
    summary={}
    for method in sorted({r['method'] for r in rows}):
        rr=[r for r in rows if r['method']==method];summary[method]=dict(pops=statistics.mean(r['pops'] for r in rr),queue_operations=statistics.mean(r['queue_operations'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='New spatial field integrated with identical macro construction. Exact pop/push/path-cost parity against frozenVM checked per case for both no-field weights. Inference/field construction excluded from these pilot times; no additional API calls.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
