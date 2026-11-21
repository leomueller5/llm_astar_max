"""Falsification stress for the derived Euclidean waypoint-weight bound.

Synthetic adversarial targets, not real/model/oracle performance evidence.
Original search code is executed with offline replies and equivalent collision
geometry. Independent Shapely Dijkstra supplies only evaluation targets.
"""
import argparse,contextlib,io,json,random,math
from common import read_cases,dump
from independent_reference import case,independent_distances
from native_benchmark import legacy
from llmastar.research.geometry import SegmentGridGraph

def check(seed,engines):
 q=case(seed);reference=independent_distances(q);start=tuple(q['start'])
 if start not in reference:return []
 rng=random.Random(690000+seed);graph=SegmentGridGraph(q);available=[(x,y) for x in range(graph.x0+1,graph.x1) for y in range(graph.y0+1,graph.y1) if graph.valid_point((x,y))];rows=[]
 for order in range(4):
  targets=rng.sample(available,min(1+order*2,len(available)));raw='Generated Path: '+json.dumps([q['start']]+targets+[q['goal']])
  for alpha in [0.,.5,1.]:
   planner=engines.Original() if alpha==1. else engines.Current(alpha=alpha,robust_search=False);planner.model=legacy.evaluation.replay.OfflineModel(raw);planner.cost=graph.cost;planner.is_collision=graph.collision
   with contextlib.redirect_stdout(io.StringIO()):r=planner.searching(json.loads(json.dumps(q)))
   path=planner.plot.path;assert path and path[0]==tuple(q['start']) and path[-1]==tuple(q['goal']);actual=sum(math.dist(a,b) for a,b in zip(path,path[1:]));assert abs(actual-r['length'])<1e-7;assert actual<=(1+alpha)*reference[start]+1e-7,(seed,order,alpha,actual/reference[start]);rows.append({'seed':seed,'order':order,'alpha':alpha,'bound':1+alpha,'cost_ratio':actual/reference[start] if reference[start] else 1.,'operations':r['operation']})
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--maps',type=int,default=100);p.add_argument('--output',required=True);a=p.parse_args();engines=legacy.Engines();rows=[]
 for seed in range(a.maps):rows+=check(seed,engines)
 dump(a.output,{'scope':'Conditional mathematical relationship, not a newly claimed search theorem: Euclidean h_goal+alpha*d_target has edge difference at most(1+alpha)*edge_cost. Global alpha/target changes preserve the fixed L argument if every OPEN priority is refreshed, fresh best-g labels remain available, and CLOSED is monotone as in frozen original. Independent reference and synthetic random/adversarial point sequences only. Numerical tests support but do not prove the general proposition.','maps_attempted':a.maps,'reachable_maps':len({r['seed'] for r in rows}),'runs':rows,'max_observed_ratio_by_alpha':{str(alpha):max((r['cost_ratio'] for r in rows if r['alpha']==alpha),default=None) for alpha in [0.,.5,1.]},'all_conditional_bounds_passed':True});print(len(rows),'conditional waypoint-bound checks passed')
if __name__=='__main__':main()
