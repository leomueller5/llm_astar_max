"""Cold/warm potential pilot on matched hierarchy, sources and quality bounds."""
import sys,json,gzip,random,math,statistics,argparse,hashlib
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
from maps import ROOT,generate
from llmastar.research.strategic.abstraction import RasterGridGraph,TileHierarchy
from llmastar.research.strategic.planner import StrategicSearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.strategic.compiler import region_trace
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--block',type=int,default=8);p.add_argument('--portal-span',type=int);p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 with gzip.open(a.cases,'rt') as f:cases=json.load(f)
 rng=random.Random(171120264);by_map={}
 for c in cases:by_map.setdefault(c['map_id'],[]).append(c)
 rows=[];setups=[]
 modes=['flat11','flat2','witness','portal11','corridor_geo11','corridor_oracle11','corridor_imperfect11','corridor_random11']
 for mi,(map_id,group) in enumerate(by_map.items()):
  # Separate map structures per method. Warm reuse never leaks across algorithms.
  structures={}
  for mode in modes:
   t=perf_counter()
   if mode.startswith(('portal','corridor')):structures[mode]=TileHierarchy(RasterGridGraph(group[0]['query']),a.block,a.portal_span)
   else:structures[mode]=SegmentGridGraph(group[0]['query'])
   setups.append({'map_id':map_id,'mode':mode,'seconds':perf_counter()-t})
  for c in group:
   for repeat in range(a.repeats):
    order=list(modes);rng.shuffle(order)
    for mode in order:
     structure=structures[mode];t=perf_counter();provider=None
     if mode.startswith(('portal','corridor')):
      if mode=='corridor_oracle11':
       regions=[structure.regions[r]['id'] for r in region_trace(structure,c['oracle_path'])]
       provider=StaticProvider({'version':1,'strategies':[{'id':'oracle','regions':regions}]},'oracle')
      elif mode=='corridor_imperfect11':
       route=region_trace(structure,c['oracle_path']);noisy=list(route)
       local=random.Random(sum(map(ord,c['id'])))
       for i in range(1,len(noisy)-1):
        if local.random()<.15:
         choices=list(structure.region_neighbors.get(noisy[i],()))
         if choices:noisy[i]=local.choice(choices)
       provider=StaticProvider({'strategies':[{'id':'noisy','regions':[structure.regions[r]['id'] for r in noisy]}]},'imperfect_oracle')
      elif mode=='corridor_random11':
       route=[rng.randrange(len(structure.regions)) for _ in range(max(2,min(8,len(c['oracle_waypoints']))))]
       provider=StaticProvider({'strategies':[{'id':'random','regions':[structure.regions[r]['id'] for r in route]}]},'random')
      r=StrategicSearch(block_size=a.block,bound=1.1,corridor=mode!='portal11',dynamic=False).search(c['query'],provider,structure)
     elif mode=='witness':r=EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,fallback_engine='lean',reuse_validation=True).search(c['query'],[],structure)
     else:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1.1 if mode=='flat11' else 2).search(c['query'],[],structure)
     seconds=perf_counter()-t;r.pop('path',None)
     rows.append(dict(r,case_id=c['id'],map_id=map_id,family=c['family'],mode=mode,repeat=repeat,query_seconds=seconds,optimal_cost=c['optimal_cost']))
  print(mi+1,'/',len(by_map),'maps',flush=True)
 summary={}
 for mode in modes:
  rr=[r for r in rows if r['mode']==mode];one=[r for r in rr if r['repeat']==0]
  times=[statistics.median(r['query_seconds'] for r in rr if r['case_id']==c['id']) for c in cases]
  setup=sum(r['seconds'] for r in setups if r['mode']==mode)
  ratio=[r['length']/r['optimal_cost'] for r in one if r['valid']]
  summary[mode]={'mean_query_median_ms':statistics.mean(times)*1000,'map_setup_ms_per_query':setup/len(cases)*1000,
    'amortized_ms':(statistics.mean(times)+setup/len(cases))*1000,'mean_unique':statistics.mean(r['unique'] for r in one),
    'gm_cost_ratio':math.exp(statistics.mean(math.log(x) for x in ratio)),'valid':sum(r['valid'] for r in one),
    'mean_start_bound_ratio':statistics.mean(r['start_lower_bound']/r['optimal_cost'] for r in one if r['valid'] and 'start_lower_bound' in r) if mode.startswith(('portal','corridor')) else None}
 data={'scope':'Warm per-map structures, separate method caches; setup fully charged once per map and amortized over actual query count. Repeated trials are not counted as extra amortization queries. Oracle guidance generation/ref search excluded as labelled potential only.','block_size':a.block,'portal_span':a.portal_span,'summary':summary,'setups':setups,'runs':rows}
 from benchmark import finite_json
 with gzip.open(a.output/'results.json.gz','wt') as f:f.write(json.dumps(finite_json(data),separators=(',',':')))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
