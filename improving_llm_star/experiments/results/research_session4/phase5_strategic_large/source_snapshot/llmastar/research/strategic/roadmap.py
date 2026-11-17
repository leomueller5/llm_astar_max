"""Lazy edge-search over geometric and proposed strategic targets.

This is a candidate generator, not a claim of grid optimality/completeness. Every
accepted edge is an actual shortest lattice walk. The caller must certify the
result or retain a complete grid fallback. Work budgets cover failed probes.
"""
import heapq,math
from time import perf_counter
from ..search import octile
from ..geometry import SegmentGridGraph,expand_lattice_route
from .schema import parse_guidance
from .providers import StaticProvider


class LazyRoadmap:
    def __init__(self,max_geometry=48,max_advice=24,max_probes=256,max_events=4096,weight=1.):
        if min(max_geometry,max_advice,max_probes,max_events)<0 or weight<1:raise ValueError('Invalid roadmap budget')
        self.max_geometry=max_geometry;self.max_advice=max_advice;self.max_probes=max_probes;self.max_events=max_events;self.weight=weight

    def propose(self,query,waypoints=(),graph=None):
        began=perf_counter();graph=graph or SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal'])
        if not graph.valid_point(start) or not graph.valid_point(goal):return {'path':[],'valid':False,'seconds':perf_counter()-began,'probes':0,'pops':0,'expanded':0,'vertices':0}
        geometry=[]
        for x,lo,hi in query['vertical_barriers']:
            if lo==hi:continue
            for y in [lo-1,hi+1]:geometry.extend([(x,y),(x-1,y),(x+1,y)])
        for y,lo,hi in query['horizontal_barriers']:
            if lo==hi:continue
            for x in [lo-1,hi+1]:geometry.extend([(x,y),(x,y-1),(x,y+1)])
        seen={start,goal};geo=[];hints=[]
        for point in sorted(set(geometry),key=lambda p:(octile(start,p)+octile(p,goal),p)):
            if point not in seen and graph.valid_point(point):geo.append(point);seen.add(point)
            if len(geo)>=self.max_geometry:break
        if self.max_geometry==0:geo=[];seen={start,goal}
        # Advice supplements the same geometric set; it cannot erase the fallback.
        for point in waypoints:
            if len(hints)>=self.max_advice:break
            p=tuple(point)
            if p not in seen and graph.valid_point(p):hints.append(p);seen.add(p)
        vertices=[start,goal]+geo+hints;g={0:0.};parent={};paths={};closed={};queue=[];probes=pops=expanded=stale=0
        def expand(u):
            for v,p in enumerate(vertices):
                if v==u:continue
                cost=g[u]+octile(vertices[u],p)
                if cost<g.get(v,math.inf)-1e-12:
                    heapq.heappush(queue,(cost+self.weight*octile(p,goal),v,u,g[u],cost))
        expand(0);route=[]
        while queue and probes<self.max_probes and pops<self.max_events:
            _,v,u,old,cost=heapq.heappop(queue);pops+=1
            if old!=g[u] or cost>=g.get(v,math.inf)-1e-12:stale+=1;continue
            probes+=1;piece=graph.lattice_segment(vertices[u],vertices[v])
            if not piece:continue
            g[v]=cost;parent[v]=u;paths[v]=piece;expanded+=1;closed[v]=cost
            if v==1:
                links=[];node=1
                while node:links.append(paths[node]);node=parent[node]
                route=[start]
                for piece in reversed(links):route.extend(expand_lattice_route(piece)[1:])
                break
            expand(v)
        return {'path':route,'valid':bool(route),'length':sum(math.dist(a,b) for a,b in zip(route,route[1:])) if route else None,'seconds':perf_counter()-began,'probes':probes,'pops':pops,'expanded':expanded,'stale':stale,'vertices':len(vertices),'geometry_vertices':len(geo),'advice_vertices':len(hints),'budget_exhausted':not route and bool(queue)}


class RoadmapProvider(StaticProvider):
    """Classical candidate generation, optionally augmented by cached advice.

    Provider requests are interface invocations, not model calls. Source and
    roadmap metrics explicitly identify this distinction.
    """
    def __init__(self,waypoints=(),source='geometry_roadmap',**settings):
        super().__init__({},source);self.waypoints=waypoints;self.planner=LazyRoadmap(**settings);self.roadmaps=[]
    def propose(self,context):
        self.calls+=1;self.events.append(context.event);began=perf_counter()
        r=self.planner.propose(context.query,self.waypoints);self.roadmaps.append({k:v for k,v in r.items() if k!='path'})
        self.processing_seconds+=perf_counter()-began
        response={'strategies':[{'id':self.source,'waypoints':r['path']}]} if r['valid'] else {'abstain':True}
        return parse_guidance(response,source=self.source,max_points=100000)
