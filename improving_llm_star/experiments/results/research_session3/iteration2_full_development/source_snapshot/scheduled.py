"""One-shot certificate evaluation after observed search effort, with matched control."""
import heapq,math
from time import perf_counter
from .efficient import EfficientCertificateSearch
from .geometry import SegmentGridGraph


class ScheduledCertificateSearch:
    def __init__(self,threshold=32,use_waypoints=True,direct=True):
        if threshold<1:raise ValueError('Positive expansion threshold required')
        self.threshold=threshold;self.use_waypoints=use_waypoints;self.direct=direct

    def search(self,query,waypoints,graph=None):
        graph=graph or SegmentGridGraph(query);began=perf_counter();preprocessing=0.;checks=0
        start,goal=tuple(query['start']),tuple(query['goal'])
        queue=[(2*math.dist(start,goal),start,0.)];g={start:0.};closed={};parents={start:start}
        pops=expanded=stale=duplicates=reopens=0;path=[];certified=False;attempted=False
        if self.direct:
            r=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,prepare_only=True).search(query,[],graph)
            preprocessing+=r['total_seconds'];checks+=r['visibility_calls']
            if r['valid']:path=r['path'];certified=True;queue=[]
        while queue:
            _,node,old=heapq.heappop(queue);pops+=1
            if old!=g[node]:stale+=1;duplicates+=int(node in closed);continue
            if node in closed and old>=closed[node]:duplicates+=1;continue
            reopens+=int(node in closed);closed[node]=old;expanded+=1
            if node==goal:
                path=[node]
                while path[-1]!=start:path.append(parents[path[-1]])
                path.reverse();break
            if self.use_waypoints and not attempted and expanded>=self.threshold:
                attempted=True
                r=EfficientCertificateSearch(segment_mode='analytic',compress=True,prepare_only=True).search(query,waypoints,graph)
                preprocessing+=r['total_seconds'];checks+=r['visibility_calls']
                if r['valid']:path=r['path'];certified=True;break
            for other,edge in graph.adj.get(node,[]):
                new=old+edge
                if new<g.get(other,math.inf)-1e-12:
                    g[other]=new;parents[other]=node;heapq.heappush(queue,(new+2*math.dist(other,goal),other,new))
        valid=graph.valid_point(start) and graph.valid_point(goal) and bool(path) and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        if not valid:path=[]
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        return dict(path=path,length=length,valid=valid,operation=pops,expanded=expanded,unique=len(closed),duplicates=duplicates,stale=stale,reopens=reopens,rebuilds=0,storage=len(g),switches=[],alpha_events=[],
          preprocess_seconds=preprocessing,search_seconds=perf_counter()-began-preprocessing,total_seconds=perf_counter()-began,visibility_calls=checks,visibility_edge_checks=0,certified_early_return=certified,certificate_attempted=attempted)
