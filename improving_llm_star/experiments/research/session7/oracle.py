"""Explicit offline reference information. Never used by a real prompt builder."""
import heapq,math,random
from time import perf_counter
from common import ROOT
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.spatial_guidance import RegionField
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile

def remaining_costs(query):
    began=perf_counter();g=SegmentGridGraph(query);goal=tuple(query['goal']);dist={goal:0.};q=[(0.,goal)];pops=pushes=1
    if not g.valid_point(goal):return {},{'seconds':perf_counter()-began,'pops':0,'pushes':0}
    pops=0
    while q:
        cost,n=heapq.heappop(q);pops+=1
        if cost>dist[n]+1e-12:continue
        for other,edge in g.adj.get(n,[]):
            v=cost+edge
            if v<dist.get(other,math.inf)-1e-12:dist[other]=v;heapq.heappush(q,(v,other));pushes+=1
    return dist,{'seconds':perf_counter()-began,'pops':pops,'pushes':pushes,'states':len(dist)}

def oracle_path(query,costs):
    n=tuple(query['start']);goal=tuple(query['goal']);g=SegmentGridGraph(query);path=[n]
    if n not in costs:return []
    while n!=goal:
        n=min(g.adj.get(n,[]),key=lambda e:e[1]+costs.get(e[0],math.inf))[0];path.append(n)
        if len(path)>len(costs):raise AssertionError('Oracle path cycle')
    return path

def anchor(query,kind):
    goal=tuple(query['goal'])
    if kind=='cut':
        try:
            potential=CutPotential(query,goal);return potential.value
        except ValueError:pass
    return lambda n:octile(n,goal)

def regional_reference(query,side,costs,kind='cut',noise=0.,seed=0):
    field=RegionField(query,side);h=anchor(query,kind);path=oracle_path(query,costs);rng=random.Random(seed);scale=math.hypot(field.width,field.height)
    values=[]
    for r in field.regions:
        p=tuple(r['sample']) if r['sample'] else None
        if p is None or p not in costs:continue
        delta=max(0.,costs[p]-h(p));near=min(math.dist(p,n) for n in path) if path else scale
        values.append({'region_id':r['id'],'detour':max(0.,delta+rng.gauss(0,noise*scale)),
            'priority':max(0.,min(1.,1-near/(scale*.25)+rng.gauss(0,noise))), 'confidence':1.})
    field.update(values);return field

class FineOracle:
    def __init__(self,query,costs,kind='cut'):
        self.costs=costs;self.h=anchor(query,kind);self.path=oracle_path(query,costs);self.pathset=set(self.path)
    def value(self,n):return max(0.,self.costs.get(n,1e6)-self.h(n)),float(n in self.pathset),1.
