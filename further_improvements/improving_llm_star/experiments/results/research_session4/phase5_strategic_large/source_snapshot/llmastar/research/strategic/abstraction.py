"""Exact region connectivity with an admissible relaxed-portal lower bound.

Region preprocessing is classical work, not attributed to LLM guidance. All cell,
edge and portal construction work is logged for cold/amortized comparisons.
"""
from dataclasses import dataclass
from collections import deque,defaultdict
import heapq,math
from time import perf_counter
import numpy as np
from ..geometry import SegmentGridGraph
from ..search import MOTIONS,octile


class RasterGridGraph(SegmentGridGraph):
    """Fresh dense point-occupancy raster, same original unit-edge semantics."""
    def __init__(self,query):
        began=perf_counter();super().__init__(query)
        if not self.indexed or any(type(v) not in [int,float] or int(v)!=v for v in [self.x0,self.x1,self.y0,self.y1]):
            raise ValueError('Raster hierarchy supports integer walls and bounds')
        self.min_x=int(self.x0+1);self.min_y=int(self.y0+1)
        self.width=int(self.x1-self.x0-1);self.height=int(self.y1-self.y0-1)
        if self.width<1 or self.height<1:raise ValueError('Empty raster')
        self.free=np.ones((self.width,self.height),dtype=bool)
        for y,lo,hi in self.horizontal:
            if lo==hi or not self.min_y<=y<self.min_y+self.height:continue
            left=max(self.min_x,lo);right=min(self.min_x+self.width-1,hi)
            if left<=right:self.free[int(left-self.min_x):int(right-self.min_x+1),int(y-self.min_y)]=False
        for x,lo,hi in self.vertical:
            if lo==hi or not self.min_x<=x<self.min_x+self.width:continue
            bottom=max(self.min_y,lo);top=min(self.min_y+self.height-1,hi)
            if bottom<=top:self.free[int(x-self.min_x),int(bottom-self.min_y):int(top-self.min_y+1)]=False
        self.preprocess_seconds=perf_counter()-began

    def blocked(self,p):
        if not self.inside(p):return True
        return not self.free[int(p[0]-self.min_x),int(p[1]-self.min_y)]


@dataclass(frozen=True)
class Portal:
    region:int
    axis:str      # x: x fixed, varying y; y: y fixed, varying x
    fixed:int
    lo:int
    hi:int

    def endpoints(self):
        return ((self.fixed,self.lo),(self.fixed,self.hi)) if self.axis=='x' else ((self.lo,self.fixed),(self.hi,self.fixed))


def _interval_gap(a,b,c,d):return max(0,max(a,c)-min(b,d))

def portal_distance(a,b):
    if a.axis==b.axis:
        fixed=abs(a.fixed-b.fixed);gap=_interval_gap(a.lo,a.hi,b.lo,b.hi)
        dx,dy=(fixed,gap) if a.axis=='x' else (gap,fixed)
    else:
        h,v=(a,b) if a.axis=='y' else (b,a)
        dx=_interval_gap(h.lo,h.hi,v.fixed,v.fixed)
        dy=_interval_gap(v.lo,v.hi,h.fixed,h.fixed)
    return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)


def point_portal_distance(point,portal):
    x,y=point
    dx,dy=(abs(x-portal.fixed),_interval_gap(y,y,portal.lo,portal.hi)) if portal.axis=='x' else (_interval_gap(x,x,portal.lo,portal.hi),abs(y-portal.fixed))
    return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)


class TileHierarchy:
    def __init__(self,graph,block_size=8,max_portal_span=None):
        if not isinstance(graph,RasterGridGraph) or block_size<2:raise ValueError('Raster graph and block size>=2 required')
        if max_portal_span is not None and max_portal_span<1:raise ValueError('Positive portal span required')
        began=perf_counter();self.graph=graph;self.block_size=int(block_size);self.max_portal_span=max_portal_span
        self.components=np.full(graph.free.shape,-1,dtype=np.int32);self.regions=[];self.names={}
        self.region_portals=defaultdict(list);self.portals=[];self.members=defaultdict(list)
        self.connectivity_edge_tests=0;self.preprocessing_cells=graph.width*graph.height
        self.nx=(graph.width+block_size-1)//block_size;self.ny=(graph.height+block_size-1)//block_size
        free=graph.free;comp=self.components;degen=bool(graph._degenerate)
        for bx in range(self.nx):
            for by in range(self.ny):
                x0=bx*block_size;x1=min(graph.width,(bx+1)*block_size)
                y0=by*block_size;y1=min(graph.height,(by+1)*block_size);local=0
                for x in range(x0,x1):
                    for y in range(y0,y1):
                        if not free[x,y] or comp[x,y]>=0:continue
                        cid=len(self.regions);name=f'b{bx}_{by}.c{local}';local+=1
                        comp[x,y]=cid;queue=deque([(x,y)]);size=0
                        while queue:
                            u,v=queue.popleft();size+=1
                            for dx,dy in MOTIONS:
                                a,b=u+dx,v+dy
                                if x0<=a<x1 and y0<=b<y1 and free[a,b] and comp[a,b]<0:
                                    self.connectivity_edge_tests+=1
                                    if degen and graph.degenerate_collision((u+graph.min_x,v+graph.min_y),(a+graph.min_x,b+graph.min_y)):continue
                                    comp[a,b]=cid;queue.append((a,b))
                        self.regions.append({'id':name,'block':[bx,by],'bbox':[x0+graph.min_x,y0+graph.min_y,x1-1+graph.min_x,y1-1+graph.min_y],'size':size,'representative':[x+graph.min_x,y+graph.min_y]})
                        self.names[name]=cid
                sides=[('x',x0,y0,y1),('x',x1-1,y0,y1),('y',y0,x0,x1),('y',y1-1,x0,x1)]
                for axis,fixed,lo,hi in sides:
                    run_start=None;old=-1
                    for z in range(lo,hi+1):
                        cid=int(comp[fixed,z] if axis=='x' and z<hi else comp[z,fixed] if axis=='y' and z<hi else -1)
                        if cid!=old:
                            if old>=0:
                                span=max_portal_span or (z-run_start)
                                for begin in range(run_start,z,span):
                                    stop=min(z-1,begin+span-1)
                                    portal=Portal(old,axis,fixed+(graph.min_x if axis=='x' else graph.min_y),begin+(graph.min_y if axis=='x' else graph.min_x),stop+(graph.min_y if axis=='x' else graph.min_x))
                                    if portal.lo==portal.hi:
                                        point=portal.endpoints()[0];portal=Portal(old,'x',point[0],point[1],point[1])
                                    existing=next((p for p in self.region_portals[old] if self.portals[p]==portal),None)
                                    if existing is None:
                                        pid=len(self.portals);self.portals.append(portal);self.region_portals[old].append(pid)
                                    else:pid=existing
                                    for k in range(portal.lo,portal.hi+1):
                                        point=(portal.fixed,k) if portal.axis=='x' else (k,portal.fixed)
                                        if pid not in self.members[point]:self.members[point].append(pid)
                            run_start=z;old=cid
        edges={};self.region_neighbors=defaultdict(set);self.cross_edge_tests=0
        def connect(a,b,cost):
            if a==b:return
            key=(a,b) if a<b else (b,a)
            if cost<edges.get(key,math.inf):edges[key]=cost
        for c,pids in self.region_portals.items():
            for i,p in enumerate(pids):
                for q in pids[i+1:]:connect(p,q,portal_distance(self.portals[p],self.portals[q]))
        for point,pids in self.members.items():
            x,y=point;region=self.region_of(point)
            for dx,dy in MOTIONS:
                other=x+dx,y+dy
                if point>=other:continue
                other_pids=self.members.get(other)
                if not other_pids:continue
                other_region=self.region_of(other)
                if other_region==region:continue
                if self.regions[region]['block']==self.regions[other_region]['block']:continue
                self.cross_edge_tests+=1
                if graph.degenerate_collision(point,other):continue
                self.region_neighbors[region].add(other_region);self.region_neighbors[other_region].add(region)
                for p in pids:
                    for q in other_pids:connect(p,q,math.hypot(dx,dy))
        self.adj=[[] for _ in self.portals]
        for (a,b),cost in edges.items():self.adj[a].append((b,cost));self.adj[b].append((a,cost))
        self.portal_edges=len(edges);self.preprocess_seconds=perf_counter()-began

    def region_of(self,point):
        x,y=point
        if not self.graph.inside(point) or x!=int(x) or y!=int(y):return -1
        return int(self.components[int(x-self.graph.min_x),int(y-self.graph.min_y)])

    def query(self,start,goal):return PortalQuery(self,tuple(start),tuple(goal))


class PortalQuery:
    def __init__(self,hierarchy,start,goal):
        began=perf_counter();self.hierarchy=hierarchy;self.start=start;self.goal=goal
        self.start_region=hierarchy.region_of(start);self.goal_region=hierarchy.region_of(goal)
        self.dist=[math.inf]*len(hierarchy.portals);self.parent={};queue=[];self.heap_pops=0
        if self.goal_region>=0:
            for p in hierarchy.region_portals[self.goal_region]:
                d=point_portal_distance(goal,hierarchy.portals[p]);self.dist[p]=d;self.parent[p]=None;heapq.heappush(queue,(d,p))
        while queue:
            d,p=heapq.heappop(queue);self.heap_pops+=1
            if d!=self.dist[p]:continue
            for q,cost in hierarchy.adj[p]:
                new=d+cost
                if new<self.dist[q]-1e-12:
                    self.dist[q]=new;self.parent[q]=p;heapq.heappush(queue,(new,q))
        self.region_lower=[math.inf]*len(hierarchy.regions)
        for region,pids in hierarchy.region_portals.items():self.region_lower[region]=min((self.dist[p] for p in pids),default=math.inf)
        if self.goal_region>=0:self.region_lower[self.goal_region]=0.
        self.lower_bound=self.point_bound(start)
        self.preprocess_seconds=perf_counter()-began

    def point_bound(self,point):
        h=self.hierarchy;region=h.region_of(point)
        if region<0:return math.inf
        value=octile(point,self.goal) if region==self.goal_region else math.inf
        for p in h.region_portals[region]:value=min(value,point_portal_distance(point,h.portals[p])+self.dist[p])
        return value

    def fast_bound(self,point):
        region=self.hierarchy.region_of(point)
        if region<0:return math.inf
        return max(octile(point,self.goal),self.region_lower[region])

    def geometric_route(self,start=None):
        h=self.hierarchy;start=self.start if start is None else start;r=h.region_of(start)
        if r<0 or self.goal_region<0:return []
        if r==self.goal_region:return [r]
        candidates=[(point_portal_distance(start,h.portals[p])+self.dist[p],p) for p in h.region_portals[r]]
        if not candidates:return []
        value,p=min(candidates)
        if not math.isfinite(value):return []
        route=[r];seen=set()
        while p is not None:
            if p in seen:raise AssertionError('Portal parent cycle')
            seen.add(p);c=h.portals[p].region
            if c!=route[-1]:route.append(c)
            p=self.parent.get(p)
        if route[-1]!=self.goal_region:route.append(self.goal_region)
        return route
