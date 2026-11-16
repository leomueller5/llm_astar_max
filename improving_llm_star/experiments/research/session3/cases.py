"""Independent procedural families for session 2. Oracle fixtures are not LLM data."""
import sys,random,math,json,gzip,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datasets import make_map,FAMILIES
from benchmark import ROOT
from llmastar.research.geometry import IndexedGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import compress_collinear

ALL_FAMILIES=FAMILIES+['large_random','large_maze']
BASES={'development':770000,'validation':880000,'fresh_test':990000}


def generate(split,maps_per_family=2):
 cases=[]
 for fi,family in enumerate(ALL_FAMILIES):
  for mi in range(maps_per_family):
   seed=BASES[split]+fi*1000+mi;rng=random.Random(seed)
   source={'large_random':'random_walls','large_maze':'maze'}.get(family,family)
   q=make_map(source,seed)
   if True:
    sx,sy=(5,3) if family.startswith('large_') else ((2,3) if mi%2==0 else (3,2))
    q={'range_x':[0,(q['range_x'][1]-1)*sx+1],'range_y':[0,(q['range_y'][1]-1)*sy+1],
       'horizontal_barriers':[[y*sy,lo*sx,hi*sx] for y,lo,hi in q['horizontal_barriers']],
       'vertical_barriers':[[x*sx,lo*sy,hi*sy] for x,lo,hi in q['vertical_barriers']]}
   graph=IndexedGridGraph(q)
   # Sample free coordinates without materializing the full adjacency graph.
   for qi in range(2):
    for attempt in range(200):
     start=(rng.randrange(1,graph.x1),rng.randrange(1,graph.y1));goal=(rng.randrange(1,graph.x1),rng.randrange(1,graph.y1))
     if not graph.valid_point(start) or not graph.valid_point(goal):continue
     if math.dist(start,goal)<min(graph.x1,graph.y1)/3:continue
     if family=='disconnected' and (start[0]<graph.x1//2)==(goal[0]<graph.x1//2):continue
     query=dict(q,start=list(start),goal=list(goal))
     optimal=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True,goal_weight=1).search(query,[],graph)
     if family=='disconnected' or optimal['valid']:break
    else:raise RuntimeError('No usable start/goal')
    corners=compress_collinear(optimal['path']) if optimal['path'] else [start,goal]
    # Deterministic misleading corner, independent of tested algorithms' behavior.
    freecorners=[p for p in [(1,1),(1,graph.y1-1),(graph.x1-1,1),(graph.x1-1,graph.y1-1)] if graph.valid_point(p)]
    far=max(freecorners,key=lambda p:math.dist(start,p)+math.dist(p,goal))
    if q['horizontal_barriers']:
     y,lo,hi=q['horizontal_barriers'][0];blocked=((lo+hi)//2,y)
    elif q['vertical_barriers']:
     x,lo,hi=q['vertical_barriers'][0];blocked=(x,(lo+hi)//2)
    else:blocked=(0,graph.y1//2)
    if family=='enclosed':blocked=(graph.x1//2,graph.y1//2)
    for quality,points in [('oracle_corners',corners),('misleading',[start,far,goal]),('blocked_or_unreachable',[start,blocked,goal]),('none',[start,goal])]:
     cases.append(dict(id=f's2_{seed}_{qi}_{quality}',map_id=f's2_{seed}',split=split,family=family,
       source='deterministic_fixture_'+quality,query=query,points=points,response='Generated Path: '+json.dumps(points),
       optimal_cost=optimal['length'],oracle_definition='Full collinear-compressed exact optimal path, fixture creation only; not a real LLM response'))
 return cases


def main():
 p=argparse.ArgumentParser();p.add_argument('--split',choices=BASES,required=True);p.add_argument('--maps-per-family',type=int,default=2);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 cases=generate(a.split,a.maps_per_family)
 with gzip.open(a.output,'wt') as f:json.dump(cases,f,separators=(',',':'))
 print(len(cases),'cases',len({c['map_id'] for c in cases}),'independent maps')
if __name__=='__main__':main()
