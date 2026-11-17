"""Independent geometry/cost/bound audit plus untimed heap/memory instrumentation."""
import sys,json,gzip,math,heapq,argparse,tracemalloc,statistics
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent));from maps import ROOT,geometry_hash
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.strategic.local_routes import LocalRouteProvider
from llmastar.research.strategic.providers import StaticProvider,GeometricRouteProvider
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree


def main():
 p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--development-cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 with gzip.open(a.evaluation/'results.json.gz','rt') as f:data=json.load(f)
 with gzip.open(a.evaluation/'cases.json.gz','rt') as f:cases=json.load(f)
 with gzip.open(a.development_cases,'rt') as f:development=json.load(f)
 assert not {geometry_hash(c['query']) for c in cases}&{geometry_hash(c['query']) for c in development}
 bymap=defaultdict(list)
 for c in cases:bymap[c['map_id']].append(c)
 checks=cost_checks=bound_checks=reference_checks=0;maps={};free_masks={}
 for mid,group in bymap.items():
  q=group[0]['query'];walls=[LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']]
  tree=STRtree(walls);maps[mid]=tree
  # Independently rasterize occupancy with installed Shapely point intersections.
  free=set()
  for x in range(q['range_x'][0]+1,q['range_x'][1]-1):
   for y in range(q['range_y'][0]+1,q['range_y'][1]-1):
    if not len(tree.query(Point(x,y),predicate='intersects')):free.add((x,y))
  free_masks[mid]=free
  for c in group:
   goal=tuple(c['query']['goal']);start=tuple(c['query']['start']);dist={goal:0.};queue=[(0.,goal)]
   while queue:
    cost,node=heapq.heappop(queue)
    if cost!=dist[node]:continue
    x,y=node
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
     other=x+dx,y+dy
     if other not in free:continue
     new=cost+math.hypot(dx,dy)
     if new<dist.get(other,math.inf)-1e-12:dist[other]=new;heapq.heappush(queue,(new,other))
   optimum=dist.get(start)
   assert (optimum is None)==(c['optimal_cost'] is None)
   if optimum is not None:assert abs(optimum-c['optimal_cost'])<1e-7
   reference_checks+=1
   potential=CutPotential(c['query'],goal)
   # All reachable states, not only points the proposed search happened to visit.
   for node,truecost in dist.items():assert potential.value(node)<=truecost+1e-7;bound_checks+=1
  print('Independent map audit',mid,flush=True)
 for row in data['runs']:
  if not row['valid']:continue
  tree=maps[row['map_id']];free=free_masks[row['map_id']];path=[tuple(p) for p in row['path']]
  for x,y in zip(path,path[1:]):
   assert x in free and y in free and max(abs(x[0]-y[0]),abs(x[1]-y[1]))==1
   assert not len(tree.query(LineString([x,y]),predicate='intersects'));checks+=1
  cost=sum(math.dist(x,y) for x,y in zip(path,path[1:]));assert abs(cost-row['length'])<1e-7;cost_checks+=1
  if not row['mode'].startswith(('original','witness')):assert cost<=(1 if row['mode']=='astar' else data['args']['bound'])*row['optimal_cost']+1e-7
 # Counter and memory pass is separate from native timing. Every loaded module
 # shares heapq, so local repair and global heaps are both counted.
 rows=[];selected=[c for c in cases if c['family'] in ['open','random_walls','rooms','tree_maze','bottlenecks'] and c['id'].endswith('_0')]
 for c in selected:
  for mode in ['weighted','witness','cut_none','local_none','local_raw','local_portfolio','cut_oracle']:
   counts={'push_calls':0,'pop_calls':0,'heapify_calls':0,'heapify_items':0};original=(heapq.heappush,heapq.heappop,heapq.heapify)
   def push(q,item):counts['push_calls']+=1;return original[0](q,item)
   def pop(q):counts['pop_calls']+=1;return original[1](q)
   def heapify(q):counts['heapify_calls']+=1;counts['heapify_items']+=len(q);return original[2](q)
   heapq.heappush,heapq.heappop,heapq.heapify=push,pop,heapify;tracemalloc.start()
   try:
    q=c['query'];g=SegmentGridGraph(q);provider=None
    if mode=='local_raw':provider=LocalRouteProvider(StaticProvider(c['response'],c['source']),g)
    elif mode=='local_none':provider=LocalRouteProvider(GeometricRouteProvider(),g)
    elif mode=='local_portfolio':provider=LocalRouteProvider(StaticProvider(c.get('portfolio',{'strategies':[]}), 'synthetic_imperfect_portfolio',parser_limits={'max_points':100000}),g)
    elif mode=='cut_oracle':provider=StaticProvider({'strategies':[{'id':'oracle','waypoints':c['oracle_waypoints']}]},'oracle',parser_limits={'max_points':100000})
    if mode=='weighted':r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=2).search(q,[],g)
    elif mode=='witness':r=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,fallback_engine='lean',reuse_validation=True).search(q,[],g)
    else:r=CutStrategySearch(bound=2,max_segments=20000 if mode=='cut_oracle' else 512).search(q,provider,g)
    current,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();heapq.heappush,heapq.heappop,heapq.heapify=original
   expected=next(x for x in data['runs'] if x['case_id']==c['id'] and x['mode']==mode and x['repeat']==0)
   assert r['valid']==expected['valid'] and (not r['valid'] or abs(r['length']-expected['length'])<1e-7)
   assert counts['pop_calls']==r.get('total_heap_pops',r['operation']),(c['id'],mode,counts,r.get('total_heap_pops',r['operation']))
   rows.append(dict(counts,case_id=c['id'],map_id=c['map_id'],family=c['family'],mode=mode,peak_python_bytes=peak,unique_total=r.get('unique_total',r['unique']),global_storage=r['storage']))
 summary={'fresh_maps':len(bymap),'reference_queries_checked':reference_checks,'admissible_state_bounds_checked':bound_checks,'valid_paths_independently_checked':cost_checks,'unit_edges_independently_checked':checks,'map_disjoint_from_development':True,'counter_trials':len(rows),'actual_api_calls':0,'memory_scope':'tracemalloc peak of Python allocations in one cold search, including provider, graph, path, queues and returned metrics; excludes preloaded response fixtures, native-library allocations, process RSS and imports. Instrumented times are NOT used as runtime results.','heap_scope':'Exact heapq API call counts including local/global heaps; heapify item count separate because heapify is linear, not a unit-cost push. Paths/status must match timed deterministic trials.'}
 (a.output/'audit.json').write_text(json.dumps({'summary':summary,'instrumented_runs':rows},indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
