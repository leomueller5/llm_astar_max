"""Proof-checked strategic route proposals with a cut-relaxation anchor.

Advice affects only primal paths and verified prefix seeds. It never supplies an
unchecked lower bound. Queue priorities remain fixed during interventions.
"""
import heapq,math
from time import perf_counter
from .cuts import CutPotential,AxisCutPotential
from .providers import GuidanceContext
from .local_routes import bypass_targets
from ..geometry import SegmentGridGraph,expand_lattice_route
from ..efficient import EfficientCertificateSearch,compress_collinear
from ..incumbent import IncumbentSearch
from ..search import octile


def legacy_bypasses(query,points):
    """Extract only unambiguous free-end crossings; reject wall-crossing claims."""
    points=[tuple(query['start'])]+[tuple(p) for p in points]+[tuple(query['goal'])]
    result=[];invalid=ambiguous=0
    for kind,key in [('v','vertical_barriers'),('h','horizontal_barriers')]:
        for i,(fixed,lo,hi) in enumerate(query[key]):
            if lo==hi:continue
            sides=set()
            for a,b in zip(points,points[1:]):
                u,v=(a[0],b[0]) if kind=='v' else (a[1],b[1])
                if u==v or not min(u,v)<=fixed<=max(u,v):continue
                other=(a[1]+(b[1]-a[1])*(fixed-u)/(v-u)) if kind=='v' else (a[0]+(b[0]-a[0])*(fixed-u)/(v-u))
                if other<lo:sides.add('below' if kind=='v' else 'left')
                elif other>hi:sides.add('above' if kind=='v' else 'right')
                else:invalid+=1
            if len(sides)==1:result.append((kind,i,next(iter(sides))))
            elif len(sides)>1:ambiguous+=1
    return result,invalid,ambiguous


def digital_walk(graph,a,b,budget):
    """Bresenham8 is a shortest lattice walk; its actual unit edges are checked."""
    x,y=a;u,v=b;dx=abs(u-x);dy=abs(v-y);sx=1 if x<u else -1;sy=1 if y<v else -1;err=dx-dy
    path=[a];checks=0
    while (x,y)!=(u,v):
        if checks>=budget:return None,checks
        old=x,y;e2=2*err
        if e2>-dy:err-=dy;x+=sx
        if e2<dx:err+=dx;y+=sy
        checks+=1
        if not math.isfinite(graph.cost(old,(x,y))):return None,checks
        path.append((x,y))
    return path,checks


class CutStrategySearch:
    def __init__(self,bound=1.1,selection='all',cut_limit=8,geometry_candidates=True,
                 intervention='blocked',max_requests=2,digital=True,max_segments=512,
                 seed_prefix=True,budget_scale=2.,interpret_legacy=False,witness=True,cache_heuristic=True,legacy_budget=8192):
        if bound<1 or max_requests<0 or max_segments<1 or budget_scale<=0:raise ValueError('Invalid cut-search settings')
        if intervention not in ['initial','blocked','effort','none']:raise ValueError('Unknown intervention mode')
        self.legacy_budget=legacy_budget
        self.cache_heuristic=cache_heuristic
        self.bound=bound;self.selection=selection;self.cut_limit=cut_limit;self.geometry_candidates=geometry_candidates
        self.intervention=intervention;self.max_requests=max_requests;self.digital=digital;self.max_segments=max_segments
        self.seed_prefix=seed_prefix;self.budget_scale=budget_scale;self.interpret_legacy=interpret_legacy;self.witness=witness

    def search(self,query,provider=None,graph=None):
        graph=graph or SegmentGridGraph(query);began=perf_counter();start,goal=tuple(query['start']),tuple(query['goal'])
        if self.witness:
            certificate=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,prepare_only=True,reuse_validation=True).search(query,[],graph)
            if certificate['valid']:
                certificate.update(total_seconds=perf_counter()-began,provider_requests=0,actual_api_calls=0,actual_tokens=None,actual_cost=0.,simulated_latency_seconds=0.,events=[],cut_count=0,accepted_source='witness',guide_paths=0)
                return certificate
        tick=perf_counter()
        try:potential=CutPotential(query,goal,self.selection,self.cut_limit)
        except ValueError:
            r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=self.bound,certificate_only=True).search(query,[],graph)
            r.update(total_seconds=perf_counter()-began,unsupported_cuts=True,provider_requests=0,actual_api_calls=0);return r
        cut_seconds=perf_counter()-tick
        valid_endpoints=graph.valid_point(start) and graph.valid_point(goal)
        lower=potential.value(start) if valid_endpoints else math.inf
        g={start:0.};parent={start:start};macro={};closed={};queue=[];events=[];warnings=[]
        upper=math.inf;incumbent=[];source=None;requests=segments=unit_checks=guide_paths=seed_count=0
        provider_seconds=candidate_seconds=0.;invalid_legacy=ambiguous_legacy=0;last_failure=None
        candidate_log=[];proposed_ids=[];search_started=False;geometric_routes=[]
        h_cache={}
        def h(n):
            if not self.cache_heuristic:return potential.value(n)
            value=h_cache.get(n)
            if value is None:value=potential.value(n);h_cache[n]=value
            return value
        def record_prefix(node,cost,pieces,count):
            nonlocal seed_count
            if not self.seed_prefix or not count or node==goal:return
            if cost+self.bound*h(node)>=self.bound*lower-1e-10:return
            if cost<g.get(node,math.inf)-1e-12:
                g[node]=cost;parent[node]=start;macro[node]=(pieces,count);seed_count+=1
                if search_started:heapq.heappush(queue,(cost+self.bound*h(node),node,cost))
        def try_route(points,label):
            nonlocal upper,incumbent,source,segments,unit_checks,guide_paths,last_failure,candidate_seconds
            tick=perf_counter();points=compress_collinear([start]+list(points)+[goal]);points=[p for p in points if graph.valid_point(p)]
            if not points or points[0]!=start or points[-1]!=goal:return False
            path=[start];ok=True;pieces=[];cost=0.
            for target in points[1:]:
                if segments>=self.max_segments:ok=False;last_failure={'reason':'segment_budget'};break
                a=path[-1];segments+=1;piece=graph.lattice_segment(a,target)
                part=expand_lattice_route(piece) if piece else None
                if part is None and self.digital:
                    part,checks=digital_walk(graph,a,target,max(0,4096-unit_checks));unit_checks+=checks
                if part is None:ok=False;last_failure={'reason':'blocked_segment','from':a,'to':target};break
                path.extend(part[1:]);pieces.append(part);cost+=octile(a,target)
                record_prefix(target,cost,pieces,len(pieces))
            if ok and path[-1]==goal:
                guide_paths+=1
                if cost<upper:upper=cost;incumbent=path;source=label
            candidate_log.append({'id':label,'valid_route':ok,'prefix_steps':len(path)-1,'cost':cost if ok else None})
            candidate_seconds+=perf_counter()-tick
            return ok
        def geometric():
            if self.geometry_candidates:
                for axis in [potential.x,potential.y]:
                    points=axis.gate_route(start)
                    if points:
                        geometric_routes.append(points);try_route(points,'geometric_'+axis.axis)
                    if incumbent and upper<=self.bound*lower+1e-9:return
        def request(event,expanded):
            nonlocal requests,provider_seconds,invalid_legacy,ambiguous_legacy
            if provider is None or requests>=self.max_requests:return
            if requests and not getattr(provider,'can_revise',False):return
            ctx=GuidanceContext(query,event,expanded,upper if math.isfinite(upper) else None,lower,tuple(proposed_ids),
                 {'failed_segment':last_failure,'cut_count':potential.cut_count,'candidate_log':candidate_log[-4:],'geometric_routes':geometric_routes})
            tick=perf_counter();advice=provider.propose(ctx);provider_seconds+=perf_counter()-tick;requests+=1;warnings.extend(advice.warnings)
            events.append({'event':event,'expanded':expanded,'strategies':[s.identifier for s in advice.strategies]})
            for strategy in advice.strategies:
                proposed_ids.append(strategy.identifier)
                chain_valid=try_route(strategy.waypoints,strategy.identifier+'_waypoints') if strategy.waypoints else False
                if incumbent and upper<=self.bound*lower+1e-9:return
                if strategy.bypasses:try_route(bypass_targets(query,strategy),strategy.identifier+'_ordered_gates')
                if incumbent and upper<=self.bound*lower+1e-9:return
                bypasses=[]
                if self.interpret_legacy and strategy.waypoints and not chain_valid and len(strategy.waypoints)*(len(query['vertical_barriers'])+len(query['horizontal_barriers']))<=self.legacy_budget:
                    inferred,invalid,ambiguous=legacy_bypasses(query,strategy.waypoints);bypasses+=inferred;invalid_legacy+=invalid;ambiguous_legacy+=ambiguous
                for bypass in strategy.bypasses:
                    kind=bypass.obstacle_id[0];i=int(bypass.obstacle_id[1:]);walls=query['vertical_barriers'] if kind=='v' else query['horizontal_barriers']
                    if i>=len(walls):warnings.append('unknown_obstacle');continue
                    if bypass.side not in (['above','below'] if kind=='v' else ['left','right']):warnings.append('incompatible_bypass');continue
                    bypasses.append((kind,i,bypass.side))
                for axis,kind in [(potential.x,'v'),(potential.y,'h')]:
                    preferences={};coords=list(axis.cuts)
                    for k,i,side in bypasses:
                        if k!=kind:continue
                        fixed,lo,hi=(query['vertical_barriers'] if kind=='v' else query['horizontal_barriers'])[i]
                        preferences.setdefault(fixed,[]).append((side,lo,hi));coords.append(fixed)
                    if not preferences:continue
                    primal=AxisCutPotential(query,goal,coords,axis.axis)
                    points=primal.gate_route(start,preferences)
                    if points:try_route(points,strategy.identifier+'_bypass_'+axis.axis)
                    if incumbent and upper<=self.bound*lower+1e-9:return
        if valid_endpoints and math.isfinite(lower):
            if self.intervention=='initial':request('initial',0)
            if not incumbent or upper>self.bound*lower+1e-9:geometric()
            if (not incumbent or upper>self.bound*lower+1e-9) and self.intervention=='blocked':request('candidate_failed_or_uncertified',0)
        preprocessing=perf_counter()-began
        pops=expanded=stale=duplicates=reopens=0;certificate_kind=None
        if incumbent and upper<=self.bound*lower+1e-9:certificate_kind='cut_start_bound'
        elif valid_endpoints and math.isfinite(lower):
            search_started=True
            queue[:]=[(cost+self.bound*h(n),n,cost) for n,cost in g.items()];heapq.heapify(queue)
            budget=max(64,int(self.budget_scale*max(1,lower)));next_budget=budget
            while queue:
                priority,node,old=heapq.heappop(queue);pops+=1
                if old!=g[node]:stale+=1;continue
                if node in closed and old>=closed[node]:duplicates+=1;continue
                if incumbent and upper<=priority+1e-9:certificate_kind='weighted_frontier';break
                if incumbent and old+h(node)>=upper-1e-12:continue
                reopens+=int(node in closed);closed[node]=old;expanded+=1
                if node==goal:
                    tail=[];p=node
                    while p!=start and p not in macro:tail.append(p);p=parent[p]
                    if p in macro:
                        pieces,count=macro[p];prefix=[start]
                        for piece in pieces[:count]:prefix.extend(piece[1:])
                    else:prefix=[start]
                    path=prefix+list(reversed(tail))
                    cost=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
                    if cost<upper:upper=cost;incumbent=path;source='grid_search'
                    certificate_kind='weighted_goal';break
                for other,edge in graph.adj.get(node,[]):
                    new=old+edge
                    if new<g.get(other,math.inf)-1e-12:
                        estimate=h(other)
                        if incumbent and new+estimate>=upper-1e-12:continue
                        g[other]=new;parent[other]=node;macro.pop(other,None);heapq.heappush(queue,(new+self.bound*estimate,other,new))
                if self.intervention in ['effort','blocked'] and provider is not None and expanded>=next_budget and requests<self.max_requests:
                    request('excess_search_effort',expanded);next_budget+=budget
                    if incumbent and upper<=self.bound*lower+1e-9:certificate_kind='intervention_start_bound';break
            if incumbent and certificate_kind is None:certificate_kind='frontier_exhausted'
        valid=valid_endpoints and bool(incumbent) and incumbent[0]==start and incumbent[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(incumbent,incumbent[1:]))
        path=incumbent if valid else []
        return {'path':path,'valid':valid,'length':sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None,
          'provider_unique':len(getattr(provider,'expanded_states',())),
          'unique_total':len(set(closed).union(getattr(provider,'expanded_states',()))),'provider_expanded':getattr(provider,'local_expanded',0),'provider_pops':getattr(provider,'local_pops',0),
          'total_heap_pops':pops+getattr(provider,'local_pops',0),'unique':len(closed),'expanded':expanded,'operation':pops,'stale':stale,'duplicates':duplicates,'reopens':reopens,'storage':len(g),'rebuilds':0,
          'total_seconds':perf_counter()-began,'preprocess_seconds':preprocessing,'search_seconds':perf_counter()-began-preprocessing,
          'cut_preprocess_seconds':cut_seconds,'lazy_heuristic_seconds':potential.lazy_seconds,'cut_count':potential.cut_count,
          'heuristic_cache_entries':len(h_cache),'cut_cache_payload_bytes':potential.cache_bytes,'cut_transforms':potential.x.transform_count+potential.y.transform_count,
          'candidate_seconds':candidate_seconds,'provider_seconds':provider_seconds,'provider_requests':requests,
          'actual_api_calls':getattr(provider,'actual_api_calls',0),'actual_tokens':None,'actual_cost':0.,
          'simulated_latency_seconds':getattr(provider,'simulated_latency_seconds',0.),'events':events,'warnings':warnings,
          'candidate_log':candidate_log,'accepted_source':source,'guide_paths':guide_paths,'seed_count':seed_count,
          'legacy_invalid_crossings':invalid_legacy,'legacy_ambiguous_crossings':ambiguous_legacy,
          'start_lower_bound':lower,'certificate':certificate_kind,'segment_calls':segments,'digital_edge_tests':unit_checks}
