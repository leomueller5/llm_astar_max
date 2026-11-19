"""Geometry-gated consensus guidance with verified A* macro transitions.

Providers return advisory routes, never trusted costs or collision claims.
No API is called unless a provider is explicitly supplied. Existing frozen
LLM-A* and constant/adaptive-alpha implementations remain independently runnable.
"""
import math
import json
from time import perf_counter
from typing import Protocol

from .geometry import SegmentGridGraph
from .geometric_advice import portfolio
from .macro_guidance import MacroGuidedSearch
from .strategic.cuts import CutPotential


class GuidanceProvider(Protocol):
    def propose(self,query,candidates):
        """Return {'routes': [coordinate_sequence, ...]}, or abstain with None."""


def normalize_routes(value,graph,max_routes=3,max_points=256):
    if isinstance(value,dict):value=value.get('routes',[])
    if not isinstance(value,(list,tuple)):return []
    if value and isinstance(value[0],(list,tuple)) and len(value[0])==2 and all(type(x) in [int,float] for x in value[0]):
        value=[value]
    result=[]
    for raw in value[:max_routes]:
        if not isinstance(raw,(list,tuple)):continue
        route=[]
        for p in raw[:max_points]:
            if not isinstance(p,(list,tuple)) or len(p)!=2 or not all(type(x) in [int,float] and math.isfinite(x) for x in p):continue
            t=tuple(p)
            if graph.valid_point(t) and (not route or t!=route[-1]):route.append(t)
        result.append(route)
    return result


def select_targets(routes,mode='consensus'):
    if mode not in ['first','consensus','consensus_rank','portfolio']:
        raise ValueError('Unknown route-selection mechanism')
    if not routes:return []
    if mode=='first':return list(routes[0])
    if mode=='portfolio':return [r[i] for i in range(max(map(len,routes),default=0)) for r in routes if i<len(r)]
    votes={};positions={};order={}
    for route in routes:
        seen=set()
        for i,p in enumerate(route):
            p=tuple(p)
            if p in seen:continue
            seen.add(p);order.setdefault(p,len(order));votes[p]=votes.get(p,0)+1
            positions[p]=positions.get(p,0.)+i
    if mode=='consensus':return [p for p in order if votes[p]>=len(routes)//2+1]
    return sorted(order,key=lambda p:(-votes[p],positions[p]/votes[p],order[p]))


class HybridWaypointPlanner:
    """Input: original structured query. Output: original keys plus diagnostics.

    geometry_best / geometry_consensus / all_endpoints are explicit no-LLM
    controls. goal_only omits route preprocessing; llm_only omits geometric
    candidate guidance and requires precomputed routes or an appropriate provider.
    """
    def __init__(self,provider=None,weight=2.,selection='consensus',
                 source='hybrid',portfolio_budget=12,share_anchor=True,
                 target_order='given',require_descent=False,interval=8,
                 probe_budget=256,probes_per_event=3,heuristic='cut'):
        if source not in ['hybrid','hybrid_always','geometry_best','geometry_consensus','all_endpoints','goal_only','llm_only']:
            raise ValueError('Unknown guidance source')
        if selection not in ['first','consensus','consensus_rank','portfolio']:
            raise ValueError('Unknown selection')
        if type(portfolio_budget) is not int or portfolio_budget<1:
            raise ValueError('Positive integer portfolio budget required')
        self.provider=provider;self.weight=weight;self.selection=selection;self.source=source
        self.heuristic=heuristic
        self.portfolio_budget=portfolio_budget;self.share_anchor=share_anchor
        self.engine=MacroGuidedSearch(weight=weight,heuristic=heuristic,interval=interval,
            probe_budget=probe_budget,probes_per_event=probes_per_event,
            target_order=target_order,require_descent=require_descent)

    def search(self,query,routes=None,graph=None,record_trace=False):
        began=perf_counter();parse_calls=0;query_parse_seconds=0.
        if isinstance(query,str):
            tick=perf_counter()
            try:query=json.loads(query)
            except ValueError:
                if self.provider is None or not hasattr(self.provider,'parse_query'):
                    raise ValueError('Natural-language input requires a provider parser; structured queries and JSON strings work offline') from None
                try:query=self.provider.parse_query(query);parse_calls=1
                except Exception as exc:raise ValueError('Planning query parser unavailable: '+type(exc).__name__) from None
            query_parse_seconds=perf_counter()-tick
        if not isinstance(query,dict):raise ValueError('Expected original structured query format')
        tick=perf_counter();graph=graph or SegmentGridGraph(query)
        grid_seconds=perf_counter()-tick
        start,goal=tuple(query['start']),tuple(query['goal'])
        provider_seconds=processing_seconds=0.;provider_calls=0;provider_error=None
        anchor=None;proof_unreachable=False
        tick=perf_counter()
        if self.share_anchor and self.heuristic=='cut':
            try:
                anchor=CutPotential(query,goal)
                if graph.valid_point(start) and graph.valid_point(goal):
                    proof_unreachable=math.isinf(anchor.value(start))
            except ValueError:anchor=None
        lower_bound_seconds=perf_counter()-tick
        if not graph.valid_point(start) or not graph.valid_point(goal) or proof_unreachable:
            return {'operation':0,'storage':0,'length':None,'llm_output':[start,goal],
                'path':[],'valid':False,'unique':0,'expanded':0,'heap_pops':0,'heap_pushes':0,
                'total_heap_pops':0,'total_heap_pushes':0,'provider_calls':0,'provider_seconds':0.,
                'geometry_gate':True,'proof_unreachable':proof_unreachable,
                'geometry_preprocess_seconds':perf_counter()-began,'total_seconds':perf_counter()-began,
                'guidance_processing_seconds':0.,'anchor_preprocess_seconds':0.,'search_seconds':0.,
                'grid_preprocess_seconds':grid_seconds,'lower_bound_seconds':lower_bound_seconds,
                'candidate_seconds':0.,'query_parse_seconds':query_parse_seconds,'parsing_provider_calls':parse_calls,
                'rebuilds':0,'stale':0,'duplicates':0,'reopens':0,'macro_probes':0,'macro_accepted':0,
                'source':self.source,'selection':self.selection,'provider_error':None}
        tick=perf_counter()
        if self.source in ['goal_only','llm_only']:
            candidates={'candidates':[],'points':{},'geometry_best':[],
                        'heap_pops':0,'heap_pushes':0,'seconds':0.}
            gate=False
        else:
            candidates=portfolio(query,graph,budget=self.portfolio_budget,anchor=anchor)
            gate=bool(candidates['candidates']) and candidates['candidates'][0]['failed_links']==0
        candidate_seconds=perf_counter()-tick
        geometry_seconds=perf_counter()-began-query_parse_seconds
        gate_used=gate and self.source!='hybrid_always'
        if gate_used:
            proposed=[candidates['geometry_best']]
        elif self.source=='geometry_best':proposed=[candidates['geometry_best']]
        elif self.source=='geometry_consensus':proposed=[r['route'] for r in candidates['candidates'][:3]]
        elif self.source=='all_endpoints':proposed=[list(candidates['points'].values())]
        elif self.source=='goal_only':proposed=[]
        else:
            proposed=routes
            if proposed is None and self.provider is not None:
                tick=perf_counter();provider_calls=1
                try:proposed=self.provider.propose(query,candidates)
                except Exception as exc:provider_error=type(exc).__name__;proposed=None
                provider_seconds=perf_counter()-tick
            if proposed is None:proposed=[candidates['geometry_best']] if self.source in ['hybrid','hybrid_always'] else []
        tick=perf_counter();normalized=normalize_routes(proposed,graph)
        points=select_targets(normalized,self.selection)
        processing_seconds=perf_counter()-tick
        result=self.engine.search(query,points,graph,record_trace=record_trace,anchor=anchor)
        result.update(llm_output=[start]+result['processed_waypoints']+[goal],
            total_heap_pops=result['heap_pops']+candidates['heap_pops'],
            total_heap_pushes=result['heap_pushes']+candidates['heap_pushes'],
            route_plan_expansions=candidates['heap_pops'],
            provider_calls=provider_calls,provider_seconds=provider_seconds,provider_error=provider_error,
            geometry_gate=gate_used,geometry_route_available=gate,proof_unreachable=False,source=self.source,selection=self.selection,
            geometry_preprocess_seconds=geometry_seconds,guidance_processing_seconds=processing_seconds,
            grid_preprocess_seconds=grid_seconds,lower_bound_seconds=lower_bound_seconds,
            candidate_seconds=candidate_seconds,
            query_parse_seconds=query_parse_seconds,parsing_provider_calls=parse_calls,
            anchor_preprocess_seconds=result['preprocess_seconds'],total_seconds=perf_counter()-began)
        return result

    def searching(self,query,filepath='temp.png',**kwargs):
        """Baseline-compatible query/result interface; plotting is separate."""
        return self.search(query,**kwargs)
