"""Public offline-compatible interface for witness-first waypoint search."""
import copy,math
from time import perf_counter
from .certified import CertifiedLLMAStar
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch


class WitnessFirstLLMAStar(CertifiedLLMAStar):
    """Exact geometric certificates, optional cached-waypoint stage, robust fallback.

    `policy='exact'` preserves optimal early certificates. `policy='frontier'`
    optionally uses an uncertified valid waypoint route as a weight-2 incumbent.
    Neither variant introduces requests during search. Supply waypoint_response
    for an offline run; initial live generation otherwise follows the old adapter.
    """
    def __init__(self,*args,use_waypoints=True,policy='exact',**kwargs):
        super().__init__(*args,**kwargs)
        if policy not in ['exact','frontier']:raise ValueError('Unknown waypoint policy')
        self.use_waypoints=use_waypoints;self.policy=policy

    def searching(self,query,filepath='temp.png'):
        if self.waypoint_response is not None and not isinstance(query,dict):raise ValueError('Offline cached runs require a structured query')
        data=copy.deepcopy(self._parse_query(query));self._initialize_parameters(copy.deepcopy(data))
        original_model=self.model
        if self.waypoint_response is not None:
            response=self.waypoint_response
            class CachedResponse:
                def ask(self,**kwargs):return response
            self.model=CachedResponse()
        try:
            if self.s_start==self.s_goal or not self.use_waypoints:self.raw_waypoints=[];self.target_list=[self.s_start,self.s_goal]
            else:self._initialize_llm_paths()
        finally:self.model=original_model
        began=perf_counter();graph=SegmentGridGraph(data)
        planner=self._make_research_planner()
        r=planner.search(data,self.raw_waypoints,graph);self.path=r['path'];self.research_result=r
        self.search_metrics={'expanded_nodes':r['expanded'],'unique_expanded_nodes':r['unique'],
          'heap_pops':r['operation'],'duplicate_pops':r['duplicates'],'stale_pops':r['stale'],
          'path_valid':r['valid'],'path_cost':r['length'],'search_time_seconds':perf_counter()-began,
          'preprocess_seconds':r['preprocess_seconds']+graph.preprocess_seconds,
          'geometry_edge_checks':graph.edge_checks,'continuous_segment_checks':graph.segment_checks,
          'wall_interval_tests':graph.wall_tests,'certified_early_return':r['certified_early_return'],
          'accepted_source':r.get('accepted_source'),'alpha_adjustments':0,'open_queue_rebuilds':0}
        if self.render:self.plot.animation(self.path,[],True,'Witness-First LLM-A*',filepath)
        return {'operation':r['operation'],'storage':r['storage'],'length':r['length'] if r['valid'] else math.inf,'llm_output':self.target_list}

    def _make_research_planner(self):
        return EfficientCertificateSearch(segment_mode='analytic',compress=True,
          witness=True,use_waypoints=self.use_waypoints,fallback_engine='lean',reuse_validation=True,
          uncertified='frontier' if self.policy=='frontier' else 'discard')
