"""Offline structured-query adapter retaining the assignment result fields."""
from .cut_search import CutStrategySearch
from .local_routes import LocalRouteProvider
from .providers import StaticProvider


class StrategicLLMAStar:
    """No model client or network calls. Supply a cached response or a provider.

    `.searching(query)` returns operation/storage/length/llm_output as before;
    detailed counters are available as `.research_result`. Only structured query
    dictionaries are accepted, so natural-language parsing cannot trigger an API.
    """
    def __init__(self,waypoint_response=None,provider=None,bound=2.,local_refinement=True,**settings):
        if provider is not None and waypoint_response is not None:raise ValueError('Choose response or provider')
        self.response=waypoint_response;self.provider=provider;self.bound=bound;self.local_refinement=local_refinement;self.settings=settings
        self.path=[];self.research_result={}
    def searching(self,query,filepath=None):
        if not isinstance(query,dict):raise TypeError('Offline strategic search requires a structured query')
        from ..geometry import SegmentGridGraph
        graph=SegmentGridGraph(query)
        provider=self.provider or (StaticProvider(self.response) if self.response is not None else None)
        if self.local_refinement and provider is not None:provider=LocalRouteProvider(provider,graph)
        self.research_result=CutStrategySearch(bound=self.bound,**self.settings).search(query,provider,graph)
        self.path=self.research_result['path']
        return {'operation':self.research_result['operation'],'storage':self.research_result['storage'],'length':self.research_result['length'],'llm_output':[],'valid':self.research_result['valid']}
