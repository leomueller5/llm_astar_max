"""Experimental bounded corridor attempt with fully accounted global fallback."""
import math
from time import perf_counter
from .geometry import SegmentGridGraph
from .incumbent import IncumbentSearch,obstacle_lower_bound
from .efficient import compress_collinear,incumbent_fallback
from .search import octile


class _RegionAdjacency:
    def __init__(self,base,allowed,cap):self.base=base;self.allowed=allowed;self.cap=cap;self.expanded=set()
    def get(self,node,default=None):
        self.expanded.add(node)
        if len(self.expanded)>self.cap:return []
        return [(n,c) for n,c in self.base.adj.get(node,[]) if self.allowed is None or n in self.allowed]


class _RegionGraph:
    def __init__(self,base,allowed,cap):self.base=base;self.adj=_RegionAdjacency(base,allowed,cap)
    def cost(self,a,b):return self.base.cost(a,b)
    def valid_point(self,p):return self.base.valid_point(p)


class CorridorSearch:
    def __init__(self,radius=1,max_cells=4096,expansion_cap=256,incumbent=True):
        if radius<0 or max_cells<1 or expansion_cap<1:raise ValueError('Invalid corridor budget')
        self.radius=radius;self.max_cells=max_cells;self.cap=expansion_cap;self.incumbent=incumbent

    def search(self,query,waypoints,graph=None):
        graph=graph or SegmentGridGraph(query);began=perf_counter();start,goal=tuple(query['start']),tuple(query['goal'])
        hints=compress_collinear([start]+list(waypoints)+[goal]);region=set();aborted=False
        # A finite coordinate-valid corridor, with an explicit memory budget.
        if not all(all(v==int(v) for v in p) and graph.inside(p) for p in hints):aborted=True
        if not aborted:
            for a,b in zip(hints,hints[1:]):
                p=a
                while True:
                    for dx in range(-self.radius,self.radius+1):
                        for dy in range(-self.radius,self.radius+1):
                            n=p[0]+dx,p[1]+dy
                            if graph.inside(n):region.add(n)
                    if len(region)>self.max_cells:aborted=True;break
                    if p==b:break
                    p=p[0]+(b[0]>p[0])-(b[0]<p[0]),p[1]+(b[1]>p[1])-(b[1]<p[1])
                if aborted:break
        preprocessing=perf_counter()-began;partial=None;states=set()
        if not aborted:
            view=_RegionGraph(graph,region,self.cap)
            partial=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True,goal_weight=1).search(query,[],view)
            states.update(view.adj.expanded)
            if partial['valid']:states.add(goal)
        lower=obstacle_lower_bound(graph,start,goal) if graph.indexed else octile(start,goal)
        if partial and partial['valid'] and partial['length']<=2*lower+1e-10:
            r=partial;used=True;fallback=False
        else:
            view=_RegionGraph(graph,None,math.inf)
            if partial and partial['valid'] and self.incumbent:r=incumbent_fallback(query,view,partial['path'],weighted_stop=True)
            else:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True).search(query,[],view)
            states.update(view.adj.expanded)
            if r['valid']:states.add(goal)
            used=bool(r.get('incumbent_used'));fallback=True
            if partial:
                for k in ['operation','expanded','duplicates','stale','reopens']:r[k]+=partial[k]
        r['unique']=len(states);r.update(preprocess_seconds=preprocessing,total_seconds=perf_counter()-began,
           search_seconds=perf_counter()-began-preprocessing,corridor_cells=len(region),corridor_aborted=aborted,
           corridor_used=used,fallback=fallback,certified_early_return=False,candidate_source='corridor' if used else None,
           visibility_edge_checks=0)
        return r
