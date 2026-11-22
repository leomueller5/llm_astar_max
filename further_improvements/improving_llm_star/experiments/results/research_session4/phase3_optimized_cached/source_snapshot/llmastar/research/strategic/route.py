"""Unrestricted ordered-subgoal pilot: a potential test, NOT a bounded planner."""
import math
from types import SimpleNamespace
from time import perf_counter
from ..geometry import SegmentGridGraph,expand_lattice_route
from ..efficient import compress_collinear
from ..scheduled import ScheduledCertificateSearch


class RouteRefinementSearch:
    """All cost is accounted. Valid routes may be suboptimal without a global bound.

    This pilot tests whether oracle coordinate hints can be used at all, before
    building a safe strategic architecture. Wrong subgoal legs fall back globally.
    """
    def __init__(self,enabled=True,leg_search=True,max_targets=256):
        self.enabled=enabled;self.leg_search=leg_search;self.max_targets=max_targets

    def search(self,query,points,graph=None):
        graph=graph or SegmentGridGraph(query);began=perf_counter();start,goal=tuple(query['start']),tuple(query['goal'])
        targets=compress_collinear([start]+list(points)+[goal]) if self.enabled else [start,goal]
        targets=[p for p in targets if graph.valid_point(p)]
        if not targets or targets[0]!=start:targets.insert(0,start)
        if targets[-1]!=goal:targets.append(goal)
        path=[start];expanded=pops=0;states=set();segment_calls=0;failed=False;leg_seconds=0.
        class Recorder:
            def get(self,node,default=None):states.add(node);return graph.adj.get(node,default)
        viewgraph=SimpleNamespace(adj=Recorder(),cost=graph.cost,valid_point=graph.valid_point)
        for target in targets[1:self.max_targets+1]:
            a=path[-1];segment_calls+=1;segment=graph.lattice_segment(a,target)
            if segment:part=expand_lattice_route(segment)
            elif self.leg_search:
                tick=perf_counter();view=dict(query,start=a,goal=target)
                r=ScheduledCertificateSearch(use_waypoints=False,direct=False).search(view,[],viewgraph)
                leg_seconds+=perf_counter()-tick;expanded+=r['expanded'];pops+=r['operation']
                # State counts are per-leg sums; union instrumentation added by harness.
                if not r['valid']:failed=True;break
                part=r['path'];states.add(target)
            else:failed=True;break
            path.extend(part[1:])
        if not path or path[-1]!=goal:failed=True
        if failed:
            r=ScheduledCertificateSearch(use_waypoints=False,direct=False).search(query,[],viewgraph)
            path=r['path'];expanded+=r['expanded'];pops+=r['operation']
            if r['valid']:states.add(goal)
        valid=graph.valid_point(start) and graph.valid_point(goal) and bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        if not valid:path=[]
        return dict(path=path,valid=valid,length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None,
            operation=pops,expanded=expanded,unique=len(states),rebuilds=0,storage=None,search_seconds=leg_seconds,
            preprocess_seconds=0.,total_seconds=perf_counter()-began,segment_calls=segment_calls,route_failed=failed,
            guarantee='validity_only; no global quality bound for subgoal concatenation')
