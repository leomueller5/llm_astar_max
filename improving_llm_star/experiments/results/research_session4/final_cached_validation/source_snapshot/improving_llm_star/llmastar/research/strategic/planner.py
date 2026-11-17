"""Bounded persistent corridor search with event-driven strategic intervention."""
import heapq,math
from time import perf_counter
from .abstraction import RasterGridGraph,TileHierarchy
from .compiler import compile_strategy
from .providers import GuidanceContext
from ..geometry import SegmentGridGraph
from ..scheduled import ScheduledCertificateSearch
from ..incumbent import IncumbentSearch


class StrategicSearch:
    def __init__(self,block_size=8,bound=1.1,corridor=True,budget_scale=2.,max_interventions=1,
                 dynamic=True,anchor_heuristic='portal',route_padding=0):
        if block_size<2 or bound<1 or budget_scale<=0 or max_interventions<0:raise ValueError('Invalid strategy search settings')
        if anchor_heuristic not in ['portal','octile','euclidean']:raise ValueError('Unknown heuristic')
        self.block_size=block_size;self.bound=bound;self.corridor=corridor;self.budget_scale=budget_scale
        self.max_interventions=max_interventions;self.dynamic=dynamic;self.heuristic_kind=anchor_heuristic;self.padding=route_padding

    def search(self,query,provider=None,hierarchy=None):
        began=perf_counter();map_seconds=0.
        if hierarchy is None:
            t=perf_counter()
            try:hierarchy=TileHierarchy(RasterGridGraph(query),self.block_size)
            except ValueError:
                graph=SegmentGridGraph(query)
                setup_seconds=perf_counter()-t
                r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=self.bound,certificate_only=True).search(query,[],graph)
                r.update(total_seconds=perf_counter()-began,unsupported_hierarchy=True,map_preprocess_seconds=setup_seconds,actual_api_calls=0,provider_requests=0)
                r['preprocess_seconds']+=setup_seconds
                return r
            map_seconds=perf_counter()-t
        graph=hierarchy.graph;start,goal=tuple(query['start']),tuple(query['goal'])
        tick=perf_counter();pq=hierarchy.query(start,goal);query_preprocess=perf_counter()-tick
        context=GuidanceContext(query,'initial',0,None,pq.lower_bound,(),{'region_count':len(hierarchy.regions),'portal_count':len(hierarchy.portals)})
        compile_seconds=0.;provider_seconds=0.;request_count=0;strategies=[];warnings=[];events=[];attempted=[]
        def request(event,expanded,upper):
            nonlocal compile_seconds,provider_seconds,request_count
            if provider is None:return
            ctx=GuidanceContext(query,event,expanded,upper if math.isfinite(upper) else None,pq.lower_bound,tuple(attempted),context.region_summary)
            tick=perf_counter();advice=provider.propose(ctx);provider_seconds+=perf_counter()-tick;request_count+=1
            tick=perf_counter()
            for strategy in advice.strategies:
                compiled=compile_strategy(strategy,hierarchy,start,goal)
                warnings.extend(compiled.warnings)
                if compiled.route:strategies.append(compiled)
            compile_seconds+=perf_counter()-tick
        if hierarchy.region_of(start)>=0 and hierarchy.region_of(goal)>=0 and math.isfinite(pq.lower_bound):request('initial',0,math.inf)
        geometric=pq.geometric_route()
        pending={start:0.};g={start:0.};parent={start:start};closed={};active=[];anchor=[];deferred={}
        unrestricted=not self.corridor;allowed=set();pops=anchor_pops=expanded=stale=duplicates=reopens=activation_pushes=0
        incumbent=[];upper=math.inf;certificate=None;guide_expansions=0;interventions=0;corridor_changes=0
        def h(n):
            if self.heuristic_kind=='euclidean':return math.dist(n,goal)
            if self.heuristic_kind=='octile':
                dx,dy=abs(n[0]-goal[0]),abs(n[1]-goal[1]);return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)
            return pq.fast_bound(n)
        def valid_entry(entry):
            _,n,old=entry
            return pending.get(n)==old and g.get(n)==old
        def push(n):
            old=g[n];pending[n]=old;heur=h(n);heapq.heappush(anchor,(old+heur,n,old))
            if unrestricted or hierarchy.region_of(n) in allowed:heapq.heappush(active,(old+self.bound*heur,n,old))
            else:deferred[n]=old
        def anchor_min():
            nonlocal anchor_pops
            while anchor and not valid_entry(anchor[0]):heapq.heappop(anchor);anchor_pops+=1
            return anchor[0][0] if anchor else math.inf
        def add_corridor(route,reason):
            nonlocal corridor_changes,activation_pushes,guide_expansions
            added=set(route)
            for _ in range(self.padding):added.update(n for r in list(added) for n in hierarchy.region_neighbors.get(r,()))
            allowed.update(added);corridor_changes+=1;guide_expansions=0
            for n,old in list(deferred.items()):
                if pending.get(n)!=old:deferred.pop(n,None);continue
                if hierarchy.region_of(n) in allowed:
                    heapq.heappush(active,(old+self.bound*h(n),n,old));activation_pushes+=1;deferred.pop(n,None)
            events.append({'event':reason,'expanded':expanded,'allowed_regions':len(allowed),'deferred':len(deferred)})
        def widen_all(reason):
            nonlocal unrestricted,activation_pushes
            unrestricted=True
            for n,old in deferred.items():
                if pending.get(n)==old:heapq.heappush(active,(old+self.bound*h(n),n,old));activation_pushes+=1
            deferred.clear();events.append({'event':reason,'expanded':expanded,'unrestricted':True})
        if self.corridor:
            if strategies:
                first=strategies.pop(0);attempted.append(first.identifier);add_corridor(first.route,'initial_strategy')
            else:add_corridor(geometric,'initial_geometric')
        if hierarchy.region_of(start)<0 or hierarchy.region_of(goal)<0 or not math.isfinite(pq.lower_bound):
            pending.clear()
        else:push(start)
        preprocessing=perf_counter()-began
        effort_budget=max(64,int(self.budget_scale*max(1,pq.lower_bound))) if math.isfinite(pq.lower_bound) else 64
        while pending:
            lower=max(pq.lower_bound,anchor_min())
            if incumbent and upper<=self.bound*lower+1e-9:certificate='anchor_bound';break
            while active and not valid_entry(active[0]):heapq.heappop(active);pops+=1;stale+=1
            if not active:
                if unrestricted:break
                if strategies:
                    s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'next_candidate');continue
                if self.dynamic and provider is not None and getattr(provider,'can_revise',False) and interventions<self.max_interventions:
                    interventions+=1;request('corridor_exhausted',expanded,upper)
                    if strategies:
                        s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'provider_revision');continue
                widen_all('corridor_exhausted_fallback');continue
            priority,node,old=heapq.heappop(active);pops+=1
            if not valid_entry((priority,node,old)):stale+=1;continue
            pending.pop(node,None);deferred.pop(node,None)
            if node in closed and old>=closed[node]:duplicates+=1;continue
            reopens+=int(node in closed);closed[node]=old;expanded+=1;guide_expansions+=1
            if node==goal:
                if old<upper:
                    path=[node]
                    while path[-1]!=start:path.append(parent[path[-1]])
                    incumbent=list(reversed(path));upper=sum(math.dist(a,b) for a,b in zip(incumbent,incumbent[1:]))
                if unrestricted:certificate='unrestricted_weighted_goal';break
                if upper<=self.bound*max(pq.lower_bound,anchor_min())+1e-9:certificate='corridor_bound';break
                events.append({'event':'quality_bound_not_met','expanded':expanded,'incumbent':upper,'lower':max(pq.lower_bound,anchor_min())})
                if strategies:
                    s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'alternative_after_quality_failure')
                elif self.dynamic and provider is not None and getattr(provider,'can_revise',False) and interventions<self.max_interventions:
                    interventions+=1;request('quality_bound_not_met',expanded,upper)
                    if strategies:
                        s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'revision_after_quality_failure')
                    else:widen_all('quality_fallback')
                else:widen_all('quality_fallback')
                continue
            for other,cost in graph.adj.get(node,[]):
                new=old+cost
                if new<g.get(other,math.inf)-1e-12:
                    g[other]=new;parent[other]=node;push(other)
            if not unrestricted and guide_expansions>=effort_budget:
                events.append({'event':'effort_budget','expanded':expanded,'budget':effort_budget})
                if strategies:
                    s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'next_candidate_budget')
                elif self.dynamic and provider is not None and getattr(provider,'can_revise',False) and interventions<self.max_interventions:
                    interventions+=1;request('effort_budget',expanded,upper)
                    if strategies:
                        s=strategies.pop(0);attempted.append(s.identifier);add_corridor(s.route,'revision_after_effort')
                    else:widen_all('effort_fallback')
                else:widen_all('effort_fallback')
        path=incumbent
        if path and not pending and certificate is None:certificate='frontier_exhausted'
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        if not valid:path=[]
        return {'path':path,'valid':valid,'length':sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None,
          'unique':len(closed),'expanded':expanded,'operation':pops+anchor_pops,'selection_pops':pops,'anchor_pops':anchor_pops,
          'stale':stale,'duplicates':duplicates,'reopens':reopens,'storage':len(g),'rebuilds':0,
          'total_seconds':perf_counter()-began,'search_seconds':perf_counter()-began-preprocessing,
          'preprocess_seconds':preprocessing,'map_preprocess_seconds':map_seconds,'query_preprocess_seconds':query_preprocess,
          'compile_seconds':compile_seconds,'provider_seconds':provider_seconds,'provider_requests':request_count,
          'actual_api_calls':getattr(provider,'actual_api_calls',0),'actual_tokens':None,'actual_cost':0.,
          'simulated_latency_seconds':getattr(provider,'simulated_latency_seconds',0.),
          'events':events,'attempted_strategies':attempted,'warnings':warnings,'corridor_changes':corridor_changes,
          'activation_pushes':activation_pushes,'unrestricted_fallback':unrestricted,'certificate':certificate,
          'start_lower_bound':pq.lower_bound,'abstract_heap_pops':pq.heap_pops,'map_cells':hierarchy.preprocessing_cells,
          'hierarchy_regions':len(hierarchy.regions),'hierarchy_portals':len(hierarchy.portals),
          'hierarchy_connectivity_tests':hierarchy.connectivity_edge_tests,'hierarchy_edges':hierarchy.portal_edges}
