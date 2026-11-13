"""Use LLM waypoints as verified upper bounds rather than compulsory targets."""
import heapq
import math
from time import perf_counter
from .search import GridGraph, octile


class IncumbentSearch:
    def __init__(self, certificate=1.02, goal_weight=2.0, use_waypoints=True,
                 prune=True, visibility_budget=4096, bound_stop="anchor",
                 certificate_only=False, repair_radius=0, repair_endpoints=False,
                 obstacle_certificate=False, lazy_certificate=False, certificate_pruning=False):
        if certificate<1 or goal_weight<1 or visibility_budget<0:
            raise ValueError('Require certificate/goal weight >=1 and nonnegative budget')
        if bound_stop not in ['anchor','weighted'] or repair_radius not in [0,1]:
            raise ValueError('Unknown stopping rule or repair radius')
        self.certificate_pruning=certificate_pruning
        self.lazy_certificate=lazy_certificate
        self.repair_endpoints=repair_endpoints;self.obstacle_certificate=obstacle_certificate
        self.bound_stop=bound_stop;self.certificate_only=certificate_only;self.repair_radius=repair_radius
        self.certificate=certificate;self.weight=goal_weight;self.use_waypoints=use_waypoints
        self.prune=prune;self.visibility_budget=visibility_budget

    def search(self,query,waypoints,graph=None):
        graph=graph or GridGraph(query);started=perf_counter()
        start,goal=tuple(query['start']),tuple(query['goal'])
        edge_checks=visibility_calls=0
        # Certify the actual emitted unit edges. The budget covers failed probes too.
        def shortcut(a,b):
            nonlocal edge_checks,visibility_calls
            visibility_calls+=1
            for diagonal_first in [True,False]:
                p=a;path=[a]
                while p!=b:
                    if edge_checks>=self.visibility_budget:return None
                    dx=(b[0]>p[0])-(b[0]<p[0]);dy=(b[1]>p[1])-(b[1]<p[1])
                    if not diagonal_first and dx and dy:
                        if abs(b[0]-p[0])>abs(b[1]-p[1]):dy=0
                        elif abs(b[1]-p[1])>abs(b[0]-p[0]):dx=0
                    q=p[0]+dx,p[1]+dy;edge_checks+=1
                    if not math.isfinite(graph.cost(p,q)):break
                    path.append(q);p=q
                if p==b:return path
            return None
        lower=obstacle_lower_bound(graph,start,goal) if self.obstacle_certificate else octile(start,goal)
        valid_endpoints=graph.valid_point(start) and graph.valid_point(goal)
        incumbent=shortcut(start,goal) if valid_endpoints else None
        candidate_cost=octile(start,goal) if incumbent else math.inf
        candidate_source='direct' if incumbent else None
        if valid_endpoints and not incumbent and self.use_waypoints and (not self.certificate_only or math.isfinite(lower)):
            seen={start,goal};points=[start];layers=[[0]]
            for p in waypoints:
                if not isinstance(p,(list,tuple)) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p):continue
                t=tuple(p);layer=[]
                if t in [start,goal] and not self.repair_endpoints:continue
                offsets=[(0,0)] if not self.repair_radius else [(0,0),(-1,0),(1,0),(0,-1),(0,1)]
                for dx,dy in offsets:
                    q=t[0]+dx,t[1]+dy
                    if self.certificate_only and self.certificate_pruning and octile(start,q)+octile(q,goal)>self.certificate*lower+1e-10:continue
                    if q not in seen and graph.valid_point(q):
                        layer.append(len(points));points.append(q);seen.add(q)
                if layer:layers.append(layer)
            points.append(goal);k=len(points);layers.append([k-1])
            edges={}
            pairs=set((i,j) for left,right in zip(layers,layers[1:]) for i in left for j in right if i<j)
            pairs.update((0,j) for j in range(1,k));pairs.update((i,k-1) for i in range(k-1))
            if self.certificate_only and self.certificate_pruning:
                pairs={ij for ij in pairs if octile(start,points[ij[0]])+octile(points[ij[0]],points[ij[1]])+octile(points[ij[1]],goal)<=self.certificate*lower+1e-10}
            costs={0:0.};parent={};outgoing={}
            def key(ij):
                i,j=ij
                if self.lazy_certificate:
                    return (octile(start,points[i])+octile(points[i],points[j])+octile(points[j],goal),octile(points[i],points[j]),ij)
                return (octile(points[i],points[j]),ij)
            for i,j in sorted(pairs,key=key):
                if edge_checks>=self.visibility_budget:break
                route=shortcut(points[i],points[j])
                if not route:continue
                edges[i,j]=route;outgoing.setdefault(i,[]).append(j)
                if i in costs and costs[i]+octile(points[i],points[j])<costs.get(j,math.inf):
                    costs[j]=costs[i]+octile(points[i],points[j]);parent[j]=i
                    changed=[j]
                    while changed:
                        u=changed.pop()
                        for v in outgoing.get(u,[]):
                            new=costs[u]+octile(points[u],points[v])
                            if new<costs.get(v,math.inf):costs[v]=new;parent[v]=u;changed.append(v)
                if self.lazy_certificate and costs.get(k-1,math.inf)<=self.certificate*lower+1e-10:break
            if k-1 in costs:
                links=[];j=k-1
                while j: i=parent[j];links.append(edges[i,j]);j=i
                incumbent=[start]
                for link in reversed(links):incumbent.extend(link[1:])
                candidate_cost=costs[k-1];candidate_source='waypoint_dag'
        preprocess=perf_counter()-started
        path=incumbent;upper=candidate_cost;certified=False
        pops=expanded=duplicates=stale=reopens=pruned=bound_pops=0;closed={};g={start:0.};parents={start:start}
        pending={start:0.};anchor=[]
        if incumbent and upper<=self.certificate*lower+1e-10:
            certified=True
        else:
            if self.certificate_only:incumbent=None;path=None;upper=math.inf
            if incumbent:anchor=[(octile(start,goal),start,0.)]
            queue=[(self.weight*math.dist(start,goal),start,0.)]
            while queue:
                if incumbent and self.bound_stop=='anchor':
                    while anchor and (anchor[0][1] not in pending or anchor[0][2]!=pending[anchor[0][1]]):
                        heapq.heappop(anchor);bound_pops+=1
                    if not anchor or upper<=self.certificate*anchor[0][0]+1e-10:
                        certified=True;break
                f,s,old=heapq.heappop(queue);pops+=1
                if old!=g[s]:stale+=1;duplicates+=int(s in closed);continue
                if s in closed and old>=closed[s]:duplicates+=1;continue
                pending.pop(s,None)
                # Historical loose weighted bound, retained only as an ablation.
                if incumbent and self.bound_stop=='weighted' and upper<=f+1e-12:break
                if self.prune and old+math.dist(s,goal)>=upper-1e-12:pruned+=1;continue
                reopens+=int(s in closed);closed[s]=old;expanded+=1
                if s==goal:
                    path=[s]
                    while path[-1]!=start:path.append(parents[path[-1]])
                    path.reverse();upper=old;break
                for n,e in graph.adj.get(s,[]):
                    new=old+e
                    if self.prune and new+math.dist(n,goal)>=upper-1e-12:continue
                    if new<g.get(n,math.inf)-1e-12:
                        g[n]=new;parents[n]=s;pending[n]=new
                        if incumbent:heapq.heappush(anchor,(new+octile(n,goal),n,new))
                        heapq.heappush(queue,(new+self.weight*math.dist(n,goal),n,new))
        valid=valid_endpoints and bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        if not valid:path=[]
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        return {'operation':pops+bound_pops,'selection_pops':pops,'bound_heap_pops':bound_pops,'expanded':expanded,'unique':len(closed),'duplicates':duplicates,
                'stale':stale,'reopens':reopens,'rebuilds':0,'storage':len(g),'length':length,
                'valid':valid,'path':path,'switches':[],'alpha_events':[],
                'preprocess_seconds':preprocess,'search_seconds':perf_counter()-started-preprocess,
                'total_seconds':perf_counter()-started,'visibility_edge_checks':edge_checks,
                'visibility_calls':visibility_calls,'candidate_source':candidate_source,
                'candidate_cost':candidate_cost if math.isfinite(candidate_cost) else None,
                'certified_early_return':certified,'start_lower_bound':lower,'pruned_expansions':pruned}


def obstacle_lower_bound(graph,start,goal):
    """Admissible grid cut bound, taking a MAX over independently crossed walls.

    A unit grid path crossing x=wall_x must contain a state on that column.
    If the direct segment crosses the blocked interval, the least octile detour
    crossing outside it is attained at one of its adjacent integer endpoints.
    Other walls are ignored, making each bound optimistic; summing would be unsafe.
    """
    lower=octile(start,goal)
    for swap,walls in [(False,graph.vertical),(True,graph.horizontal)]:
        a=(start[1],start[0]) if swap else start
        b=(goal[1],goal[0]) if swap else goal
        for coordinate,lo,hi in walls:
            if lo==hi:continue  # Degenerate Shapely lines may be nonblocking.
            if not min(a[0],b[0])<coordinate<max(a[0],b[0]):continue
            crossing=a[1]+(b[1]-a[1])*(coordinate-a[0])/(b[0]-a[0])
            if not lo<=crossing<=hi:continue
            candidates=[(coordinate,lo-1),(coordinate,hi+1)]
            if swap:candidates=[(y,x) for x,y in candidates]
            values=[octile(start,p)+octile(p,goal) for p in candidates if graph.inside(p)]
            lower=max(lower,min(values,default=math.inf))
    return lower
