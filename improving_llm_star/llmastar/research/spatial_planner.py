"""LLM-RH*: bounded A* with persistent regional residual predictions.

Default use is offline: provide predictions or an explicit provider. No model
calls are made by this module itself. Original baseline and Session6 VM untouched.
"""
import json,math
from time import perf_counter
from .geometry import SegmentGridGraph
from .spatial_guidance import RegionField,SpatialSearch
from .spatial_calibration import sample_intervals,VerifiedResidualField

class ResidualField:
    def __init__(self,field,alpha):self.field=field;self.alpha=alpha
    def value(self,n):
        d,p,c=self.field.value(n);return self.alpha*d,p,c
    def identifier(self,n):return self.field.identifier(n)

class SpatialResidualAStar:
    """H=h+min((w-1)h, alpha*confidence*predicted regional extra cost).

The model is unchanged. A global alpha can be fitted on development residual
labels; it is not silently optimized per hidden map. The effective trust also
shrinks near the goal through the pointwise envelope. Cost fields need not be
admissible or consistent; the anchor and reopenings supply the w bound.
"""
    def __init__(self,provider=None,bound=2.,alpha=1.,side=4,base_weight=1.,source='model',
                 macros=False,target_order='given',interval=8,probe_budget=256):
        if not math.isfinite(alpha) or alpha<0:raise ValueError('Nonnegative finite alpha required')
        if source not in ['model','none','verified_model','geometry_midpoint','geometry_upper']:raise ValueError('Unknown spatial source')
        self.provider=provider;self.bound=bound;self.alpha=alpha;self.side=side;self.base_weight=base_weight;self.source=source;self.macros=macros;self.target_order=target_order
        self.engine=SpatialSearch(mode='heuristic_envelope',bound=bound,base_weight=base_weight,macro=macros,target_order=target_order,interval=interval,probe_budget=probe_budget)
    def search(self,query,predictions=None,record_trace=False):
        began=perf_counter()
        if isinstance(query,str):
            try:query=json.loads(query)
            except ValueError:raise ValueError('Use the original structured query or its JSON representation') from None
        if not isinstance(query,dict):raise ValueError('Expected original structured query')
        graph=SegmentGridGraph(query);grid_seconds=perf_counter()-began;tick=perf_counter();regions=RegionField(query,self.side,graph);region_seconds=perf_counter()-tick
        provider_calls=0;provider_seconds=0.;provider_error=None;raw=predictions
        valid_endpoints=graph.valid_point(tuple(query['start'])) and graph.valid_point(tuple(query['goal']))
        if self.source in ['model','verified_model'] and raw is None and self.provider is not None and valid_endpoints:
            tick=perf_counter();provider_calls=1
            try:raw=self.provider.predict(query,regions.regions)
            except Exception as exc:provider_error=type(exc).__name__;raw=None
            provider_seconds=perf_counter()-tick
        tick=perf_counter();parse_error=None
        if self.source in ['model','verified_model'] and raw is not None:
            try:
                if isinstance(raw,str):raw=json.loads(raw)
                regions.update(raw)
            except (ValueError,TypeError,KeyError) as exc:parse_error=type(exc).__name__;regions.values={}
        parse_seconds=perf_counter()-tick;interval_work={};alpha_by_region={r['id']:self.alpha*regions.values.get(r['id'],(0.,.5,0.))[2] for r in regions.regions}
        field=ResidualField(regions,self.alpha) if self.source=='model' else None
        if self.source in ['verified_model','geometry_midpoint','geometry_upper']:
            intervals,interval_work=sample_intervals(query,self.side)
            field=VerifiedResidualField(regions,intervals,source='model' if self.source=='verified_model' else 'midpoint' if self.source=='geometry_midpoint' else 'upper',alpha=self.alpha)
            alpha_by_region=field.alpha_values
        targets=[];candidate_pops=candidate_pushes=0;candidate_seconds=0.
        if self.macros:
            from .geometric_advice import portfolio
            tick=perf_counter();p=portfolio(query,graph,budget=12);candidate_seconds=perf_counter()-tick
            gate=bool(p['candidates']) and p['candidates'][0]['failed_links']==0
            targets=p['geometry_best'] if gate else list(p['points'].values());candidate_pops=p['heap_pops'];candidate_pushes=p['heap_pushes']
        r=self.engine.search(query,field,graph,targets,record_trace=record_trace)
        r.update(llm_output=[tuple(query['start']),tuple(query['goal'])],guidance_type='regional_remaining_cost_residual',source=self.source,
            provider_calls=provider_calls,provider_seconds=provider_seconds,provider_error=provider_error,prediction_parse_error=parse_error,
            rejected_predictions=regions.rejections,prediction_coverage=len(regions.values)/len(regions.regions),global_alpha=self.alpha,alpha_by_region=alpha_by_region,
            field_predictions=regions.values,grid_seconds=grid_seconds,region_seconds=region_seconds,prediction_parse_seconds=parse_seconds,
            interval_work=interval_work,candidate_seconds=candidate_seconds,
            total_heap_pops=r['heap_pops']+candidate_pops,total_heap_pushes=r['heap_pushes']+candidate_pushes,
            total_seconds=perf_counter()-began,compute_excluding_provider_seconds=perf_counter()-began-provider_seconds)
        return r
    def searching(self,query,filepath='temp.png',**kwargs):return self.search(query,**kwargs)
