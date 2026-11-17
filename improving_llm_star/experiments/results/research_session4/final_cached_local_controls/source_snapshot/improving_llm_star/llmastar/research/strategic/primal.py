"""Primal-first strategic search: advice supplies routes, never trusted bounds.

Cheap admissible certificates precede expensive relaxations. A bounded complete
weighted grid search is the final fallback. Choosing a shorter verified candidate
than that fallback preserves its quality bound. Geometry-only and advice variants
share exactly the same engine and budgets.
"""
import math
from time import perf_counter
from .roadmap import LazyRoadmap
from .cut_search import legacy_bypasses,digital_walk
from .providers import GuidanceContext
from .cuts import CutPotential
from .local_routes import bypass_targets
from ..search import octile
from ..geometry import SegmentGridGraph,expand_lattice_route
from ..incumbent import IncumbentSearch,obstacle_lower_bound
from ..efficient import EfficientCertificateSearch,compress_collinear


class PrimalFirstSearch:
    def __init__(self,bound=1.1,roadmap=True,advice_graph=True,cut_certificate=True,
                 max_geometry=48,max_probes=256,max_advice_probes=64,intervention='initial',
                 witness=True,interpret_bypasses=True,fallback='weighted',max_segments=20000):
        if bound<1 or intervention not in ['initial','blocked','none'] or fallback not in ['weighted','cut']:raise ValueError('Unknown primal search setting')
        self.bound=bound;self.roadmap=roadmap;self.advice_graph=advice_graph;self.cut_certificate=cut_certificate
        self.max_geometry=max_geometry;self.max_probes=max_probes;self.max_advice_probes=max_advice_probes
        self.intervention=intervention;self.witness=witness;self.interpret_bypasses=interpret_bypasses;self.fallback=fallback;self.max_segments=max_segments

    def search(self,query,provider=None,graph=None):
        began=perf_counter();graph=graph or SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal'])
        rows=[];best=[];upper=math.inf;source=None;events=[];calls=checks=0;provider_seconds=route_seconds=roadmap_seconds=cut_seconds=0.;roadmap_pops=roadmap_probes=roadmap_expanded=0
        if not graph.valid_point(start) or not graph.valid_point(goal):
            return dict(path=[],valid=False,length=None,unique=0,expanded=0,operation=0,storage=0,total_seconds=perf_counter()-began,provider_requests=0,actual_api_calls=0)
        lower=octile(start,goal)
        if self.witness:
            r=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,prepare_only=True,reuse_validation=True).search(query,[],graph)
            if r['valid']:
                r.update(total_seconds=perf_counter()-began,provider_requests=0,actual_api_calls=0,actual_cost=0.,actual_tokens=None,events=[],accepted_source='witness',roadmap_pops=0,roadmap_probes=0,roadmap_expanded=0,roadmap_seconds=0.,cut_seconds=0.)
                return r
            lower=r['start_lower_bound']
        elif getattr(graph,'indexed',False):lower=obstacle_lower_bound(graph,start,goal)
        def keep(path,label):
            nonlocal best,upper,source
            cost=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
            if path and path[0]==start and path[-1]==goal and cost<upper:
                best=path;upper=cost;source=label
        def route(points,label):
            nonlocal checks,route_seconds
            tick=perf_counter();points=compress_collinear([start]+[tuple(p) for p in points if graph.valid_point(p)]+[goal]);path=[start];ok=True
            if len(points)>self.max_segments+1:ok=False
            if ok:
                for point in points[1:]:
                    piece=graph.lattice_segment(path[-1],point);checks+=1
                    if not piece:ok=False;break
                    path.extend(expand_lattice_route(piece)[1:])
            if ok:keep(path,label)
            rows.append({'id':label,'valid':ok,'segments_checked':checks,'cost':sum(math.dist(a,b) for a,b in zip(path,path[1:])) if ok else None})
            route_seconds+=perf_counter()-tick
        def road(points,label,geometry):
            nonlocal roadmap_seconds,roadmap_pops,roadmap_probes,roadmap_expanded
            tick=perf_counter();r=LazyRoadmap(max_geometry=self.max_geometry if geometry else 0,max_advice=24,max_probes=self.max_probes if geometry else self.max_advice_probes).propose(query,points,graph)
            roadmap_seconds+=perf_counter()-tick;roadmap_pops+=r['pops'];roadmap_probes+=r['probes'];roadmap_expanded+=r['expanded']
            if r['valid']:keep(r['path'],label)
            rows.append(dict({k:v for k,v in r.items() if k not in ['path','seconds']},id=label))
        def certified():return bool(best) and upper<=self.bound*lower+1e-9
        def request(event):
            nonlocal calls,provider_seconds
            if provider is None or calls:return
            tick=perf_counter();advice=provider.propose(GuidanceContext(query,event,0,upper if best else None,lower,(),{'candidate_log':rows[-4:]}));provider_seconds+=perf_counter()-tick;calls+=1
            events.append({'event':event,'expanded':0,'strategies':[s.identifier for s in advice.strategies]})
            for s in advice.strategies:
                if s.waypoints:route(s.waypoints,s.identifier+'_chain')
                if s.bypasses:route(bypass_targets(query,s),s.identifier+'_ordered_gates')
                if certified():return
                targets=list(s.waypoints)
                if self.interpret_bypasses:
                    bypasses=[(b.obstacle_id[0],int(b.obstacle_id[1:]),b.side) for b in s.bypasses]
                    if s.waypoints:bypasses+=legacy_bypasses(query,s.waypoints)[0]
                    for kind,i,side in bypasses:
                        walls=query['vertical_barriers'] if kind=='v' else query['horizontal_barriers']
                        if i>=len(walls):continue
                        fixed,lo,hi=walls[i]
                        if kind=='v' and side in ['above','below']:targets.append((fixed,hi+1 if side=='above' else lo-1))
                        elif kind=='h' and side in ['right','left']:targets.append((hi+1 if side=='right' else lo-1,fixed))
                if self.advice_graph and targets:road(targets,s.identifier+'_sparse_graph',False)
                if certified():return
        if self.intervention=='initial':request('initial')
        if not certified() and self.roadmap:road([],'geometry_roadmap',True)
        if not certified() and self.intervention=='blocked':request('classical_candidate_failed_or_uncertified')
        certificate='single_wall_bound' if certified() else None
        if not certificate and best and self.cut_certificate:
            tick=perf_counter()
            try:potential=CutPotential(query,goal);lower=max(lower,potential.value(start))
            except ValueError:pass
            cut_seconds=perf_counter()-tick
            if certified():certificate='cut_start_bound'
        prep=perf_counter()-began
        fallback_result=None
        if certificate is None:
            if self.fallback=='cut':
                from .cut_search import CutStrategySearch
                from .providers import StaticProvider
                advice=StaticProvider({'strategies':[{'id':'verified_incumbent','waypoints':compress_collinear(best)}]},'internal_candidate') if best else None
                fallback_result=CutStrategySearch(bound=self.bound,witness=False,geometry_candidates=False,intervention='initial').search(query,advice,graph)
            else:fallback_result=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=self.bound,certificate_only=True).search(query,[],graph)
            if fallback_result['valid']:keep(fallback_result['path'],'grid_fallback')
            certificate='bounded_grid_fallback' if best else None
        valid=bool(best) and best[0]==start and best[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(best,best[1:]))
        if not valid:best=[];upper=None
        base=fallback_result or {}
        return dict(path=best,valid=valid,length=upper,unique=base.get('unique',0),expanded=base.get('expanded',0),operation=base.get('operation',0),storage=base.get('storage',0),stale=base.get('stale',0),duplicates=base.get('duplicates',0),reopens=base.get('reopens',0),rebuilds=0,
           total_seconds=perf_counter()-began,preprocess_seconds=prep,search_seconds=perf_counter()-began-prep,route_seconds=route_seconds,roadmap_seconds=roadmap_seconds,cut_seconds=cut_seconds,provider_seconds=provider_seconds,
           provider_requests=calls,actual_api_calls=getattr(provider,'actual_api_calls',0),actual_tokens=None,actual_cost=0.,simulated_latency_seconds=getattr(provider,'simulated_latency_seconds',0.),events=events,candidate_log=rows,
           roadmap_pops=roadmap_pops,roadmap_probes=roadmap_probes,roadmap_expanded=roadmap_expanded,total_heap_pops=base.get('operation',0)+roadmap_pops,accepted_source=source,certificate=certificate,start_lower_bound=lower,fallback_executed=fallback_result is not None,segment_calls=checks)
