"""Use LLM waypoints as verified upper bounds rather than compulsory targets."""
import heapq
import math
from time import perf_counter
from .search import GridGraph, octile


class IncumbentSearch:
    def __init__(self, certificate=1.02, goal_weight=2.0, use_waypoints=True,
                 prune=True, visibility_budget=4096):
        if certificate<1 or goal_weight<1 or visibility_budget<0:
            raise ValueError('Require certificate/goal weight >=1 and nonnegative budget')
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
        incumbent=shortcut(start,goal)
        candidate_cost=octile(start,goal) if incumbent else math.inf
        candidate_source='direct' if incumbent else None
        if not incumbent and self.use_waypoints:
            seen={start,goal};points=[start]
            for p in waypoints:
                t=tuple(p)
                if t not in seen and graph.valid_point(t):points.append(t);seen.add(t)
            points.append(goal);k=len(points)
            edges={}
            pairs=set((i,i+1) for i in range(k-1))
            pairs.update((0,j) for j in range(1,k));pairs.update((i,k-1) for i in range(k-1))
            # Short proposed links first, so dense waypoint lists respect the work cap.
            for i,j in sorted(pairs,key=lambda ij:(octile(points[ij[0]],points[ij[1]]),ij)):
                if edge_checks>=self.visibility_budget:break
                route=shortcut(points[i],points[j])
                if route:edges[i,j]=route
            costs={0:0.};parent={}
            for j in range(1,k):
                for i in range(j):
                    if i in costs and (i,j) in edges:
                        cost=costs[i]+octile(points[i],points[j])
                        if cost<costs.get(j,math.inf):costs[j]=cost;parent[j]=i
            if k-1 in costs:
                links=[];j=k-1
                while j: i=parent[j];links.append(edges[i,j]);j=i
                incumbent=[start]
                for link in reversed(links):incumbent.extend(link[1:])
                candidate_cost=costs[k-1];candidate_source='waypoint_dag'
        preprocess=perf_counter()-started
        path=incumbent;upper=candidate_cost;certified=False
        pops=expanded=duplicates=stale=reopens=pruned=0;closed={};g={start:0.};parents={start:start}
        if incumbent and upper<=self.certificate*octile(start,goal)+1e-10:
            certified=True
        else:
            queue=[(self.weight*math.dist(start,goal),start,0.)]
            while queue:
                f,s,old=heapq.heappop(queue);pops+=1
                if old!=g[s]:stale+=1;duplicates+=int(s in closed);continue
                if s in closed and old>=closed[s]:duplicates+=1;continue
                # Candidate no worse than the next weighted search solution.
                if incumbent and upper<=f+1e-12:break
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
                        g[n]=new;parents[n]=s
                        heapq.heappush(queue,(new+self.weight*math.dist(n,goal),n,new))
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        return {'operation':pops,'expanded':expanded,'unique':len(closed),'duplicates':duplicates,
                'stale':stale,'reopens':reopens,'rebuilds':0,'storage':len(g),'length':length,
                'valid':valid,'path':path,'switches':[],'alpha_events':[],
                'preprocess_seconds':preprocess,'search_seconds':perf_counter()-started-preprocess,
                'total_seconds':perf_counter()-started,'visibility_edge_checks':edge_checks,
                'visibility_calls':visibility_calls,'candidate_source':candidate_source,
                'candidate_cost':candidate_cost if math.isfinite(candidate_cost) else None,
                'certified_early_return':certified,'pruned_expansions':pruned}
