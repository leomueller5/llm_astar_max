"""Same public query/result interface for bounded verified waypoint seeding."""
from .witness import WitnessFirstLLMAStar
from llmastar.research.guidance import WaypointGuidanceSearch


class SeededLLMAStar(WitnessFirstLLMAStar):
    def __init__(self,*args,guidance=True,strategy='cut',**kwargs):
        if strategy not in ['cut','rank','quality']:raise ValueError('Unknown guidance strategy')
        super().__init__(*args,use_waypoints=guidance,**kwargs);self.strategy=strategy

    def _make_research_planner(self):
        if self.strategy=='quality':return WaypointGuidanceSearch(use_waypoints=self.use_waypoints,mode='potential',filtering='visible')
        return WaypointGuidanceSearch(use_waypoints=self.use_waypoints,lazy=True,cut_filter=self.strategy=='cut')

    def searching(self,*args,**kwargs):
        result=super().searching(*args,**kwargs)
        self.search_metrics.update({k:self.research_result.get(k,0) for k in ['guidance_candidates','guidance_accepted','guidance_rejected','guidance_seconds']})
        return result
