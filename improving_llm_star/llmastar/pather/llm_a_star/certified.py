"""Same query/result interface, certified waypoint use with no in-search LLM calls."""
import copy
import math
from time import perf_counter
from .llm_a_star import LLMAStar
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.search import LazyGridGraph


class CertifiedLLMAStar(LLMAStar):
    """Certificate-first search; initial waypoint generation is inherited unchanged.

    `waypoint_response` permits a fully offline run with an existing raw response.
    Without it, the inherited adapter performs its normal initial request only.
    """
    def __init__(self,llm='gpt',prompt='standard',waypoint_response=None,plot=False,
                 visibility_budget=4096):
        super().__init__(llm=llm,prompt=prompt)
        self.waypoint_response=waypoint_response;self.render=plot
        self.visibility_budget=visibility_budget
        self.raw_waypoints=[]

    def _filter_valid_nodes(self,nodes):
        self.raw_waypoints=nodes if isinstance(nodes,list) else []
        try:return super()._filter_valid_nodes(nodes)
        except (TypeError,IndexError):return []

    def searching(self,query,filepath='temp.png'):
        if self.waypoint_response is not None and not isinstance(query,dict):
            raise ValueError('Offline cached runs require a structured query')
        data=copy.deepcopy(self._parse_query(query))
        self._initialize_parameters(copy.deepcopy(data))
        original_model=self.model
        if self.waypoint_response is not None:
            response=self.waypoint_response
            class CachedResponse:
                def ask(self,**kwargs):return response
            self.model=CachedResponse()
        try:
            if self.s_start==self.s_goal:
                self.raw_waypoints=[];self.target_list=[self.s_start,self.s_goal]
            else:self._initialize_llm_paths()
        finally:self.model=original_model
        started=perf_counter();graph=LazyGridGraph(data)
        planner=IncumbentSearch(certificate=1.0,repair_radius=1,
            obstacle_certificate=True,certificate_only=True,certificate_pruning=True,
            visibility_budget=self.visibility_budget)
        r=planner.search(data,self.raw_waypoints,graph)
        self.path=r['path'];self.research_result=r
        self.search_metrics={
            'expanded_nodes':r['expanded'],'unique_expanded_nodes':r['unique'],
            'heap_pops':r['operation'],'duplicate_pops':r['duplicates'],
            'path_valid':r['valid'],'path_cost':r['length'],
            'search_time_seconds':perf_counter()-started,
            'preprocess_seconds':r['preprocess_seconds']+graph.preprocess_seconds,
            'geometry_edge_checks':graph.edge_checks,
            'visibility_edge_checks':r['visibility_edge_checks'],
            'certified_early_return':r['certified_early_return'],
            'alpha_adjustments':0,'open_queue_rebuilds':0,
        }
        if self.render:self.plot.animation(self.path,[],True,'Certified LLM-A*',filepath)
        return {'operation':r['operation'],'storage':r['storage'],
                'length':r['length'] if r['valid'] else math.inf,'llm_output':self.target_list}
