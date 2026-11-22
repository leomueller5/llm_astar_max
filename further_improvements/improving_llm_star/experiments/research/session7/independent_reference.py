"""Reference Dijkstra with independent Shapely-only successor construction."""
import argparse,heapq,math,random
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from common import dump

def independent_distances(q):
 walls=[LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']];tree=STRtree(walls)
 def clear(shape):return not any(shape.intersects(walls[int(k)]) for k in tree.query(shape))
 free={(x,y) for x in range(q['range_x'][0]+1,q['range_x'][1]-1) for y in range(q['range_y'][0]+1,q['range_y'][1]-1) if clear(Point(x,y))};goal=tuple(q['goal'])
 if goal not in free:return {}
 dist={goal:0.};queue=[(0.,goal)]
 while queue:
  cost,n=heapq.heappop(queue)
  if cost>dist[n]+1e-12:continue
  for dx in [-1,0,1]:
   for dy in [-1,0,1]:
    if not (dx or dy):continue
    m=(n[0]+dx,n[1]+dy)
    if m not in free or not clear(LineString([n,m])):continue
    new=cost+math.hypot(dx,dy)
    if new<dist.get(m,math.inf)-1e-12:dist[m]=new;heapq.heappush(queue,(new,m))
 return dist

def case(seed):
 rng=random.Random(47100000+seed);x0=rng.randrange(-9,3);y0=rng.randrange(-9,3);w=rng.randrange(9,18);h=rng.randrange(9,20);q={'range_x':[x0,x0+w],'range_y':[y0,y0+h],'start':[x0+1,y0+1],'goal':[x0+w-2,y0+h-2],'horizontal_barriers':[],'vertical_barriers':[]}
 for _ in range(rng.randrange(1,10)):
  axis=rng.randrange(2);base=x0 if axis else y0;other=y0 if axis else x0;size=w if axis else h;other_size=h if axis else w;fixed=base+rng.randrange(1,size-1)+(.5 if seed%3==0 else 0);lo=other+rng.randrange(0,other_size-3);hi=other+rng.randrange(lo-other+1,other_size);q['vertical_barriers' if axis else 'horizontal_barriers'].append([fixed,lo,hi])
 return q

def check(seed):
 from oracle import anchor
 from llmastar.research.spatial_guidance import SpatialSearch,RegionField
 q=case(seed);reference=independent_distances(q);h=anchor(q,'cut');start=tuple(q['start']);rng=random.Random(seed);f=RegionField(q,4);f.update([{'region_id':r['id'],'detour':rng.random()*1000,'priority':rng.random(),'confidence':rng.random()} for r in f.regions]);rows=[]
 for n,cost in reference.items():assert h(n)<=cost+1e-7,(seed,'anchor inadmissible',n,h(n),cost)
 for bound in [1.,1.05,2.]:
  r=SpatialSearch(mode='heuristic_envelope',bound=bound,base_weight=1.).search(q,f)
  assert r['valid']==(start in reference),(seed,'reachability')
  if r['valid']:assert r['length']<=bound*reference[start]+1e-7,(seed,bound,r['length'],reference[start])
  rows.append({'seed':seed,'bound':bound,'valid':r['valid'],'reference':reference.get(start),'length':r['length'] if r['valid'] else None})
 return rows,len(reference)

def main():
 p=argparse.ArgumentParser();p.add_argument('--maps',type=int,default=100);p.add_argument('--output',required=True);a=p.parse_args();rows=[];states=0
 for seed in range(a.maps):
  rr,n=check(seed);rows+=rr;states+=n
 dump(a.output,{'scope':'Reference uses only Shapely wall/edge predicates and independent eight-neighbour Dijkstra, never SegmentGridGraph successors/costs. Negative nonsquare maps, fractional walls, unreachable or blocked endpoints, arbitrary guidance. All reachable anchor values checked against reference, and w=1/1.05/2 actual path bounds checked.','maps':a.maps,'runs':rows,'anchor_states_checked':states,'all_checks_passed':True});print(len(rows),'independent reference searches passed')
if __name__=='__main__':main()
