import math
from llmastar.research.strategic.schema import parse_guidance
from llmastar.research.strategic.providers import StaticProvider,ScriptedProvider,GuidanceContext


def test_schema_legacy_and_strategic_advice():
 a=parse_guidance('Generated Path: [[1,2],[3,4]]','cached_real')
 assert a.strategies[0].waypoints==((1,2),(3,4))
 b=parse_guidance('```json\n{"version":1,"strategies":[{"id":"north","confidence":0.6,"regions":["r1","r2"],"bypasses":[{"obstacle_id":"h0","side":"above"}]}]}\n```')
 assert b.strategies[0].regions==('r1','r2') and b.strategies[0].bypasses[0].side=='above'


def test_malformed_advice_does_not_become_constraints():
 for raw in ['not json',{'version':9}, {'strategies':'bad'}, {'strategies':[{'id':'x','waypoints':[[True,1],[math.nan,2],[1.5,2]]}]}]:
  assert parse_guidance(raw).abstain
 r=parse_guidance({'strategies':[{'id':'x','confidence':9,'regions':['r1']},{'id':'x','regions':['r2']}]})
 assert len(r.strategies)==1 and r.strategies[0].confidence is None
 assert parse_guidance('x'*100001).abstain


def test_provider_accounts_simulated_latency_without_network():
 p=ScriptedProvider([{'strategies':[{'id':'a','regions':['r1']}]}],charged_latency=.2)
 a=p.propose(GuidanceContext({},'effort_budget',40));b=p.propose(GuidanceContext({},'corridor_failed',80))
 assert len(a.strategies)==1 and b.abstain and p.calls==2 and p.actual_api_calls==0
 assert p.simulated_latency_seconds==.4 and p.actual_tokens is None

import random,heapq
from llmastar.research.strategic.abstraction import RasterGridGraph,TileHierarchy,point_portal_distance,portal_distance


def _distances(graph,goal):
 d={goal:0.};queue=[(0.,goal)]
 while queue:
  cost,n=heapq.heappop(queue)
  if cost!=d[n]:continue
  for other,e in graph.adj.get(n,[]):
   new=cost+e
   if new<d.get(other,math.inf)-1e-12:d[other]=new;heapq.heappush(queue,(new,other))
 return d


def test_hierarchy_bounds_against_exact_grid_costs_and_reachability():
 rng=random.Random(17112026)
 for size in [3,4,6]:
  for i in range(8):
   q=dict(range_x=[0,16],range_y=[0,14],horizontal_barriers=[[rng.randrange(3,11),rng.randrange(1,5),rng.randrange(7,14)]],vertical_barriers=[[rng.randrange(4,13),0,rng.randrange(7,12)]])
   graph=RasterGridGraph(q);h=TileHierarchy(graph,size);goal=(13,11);exact=_distances(graph,goal)
   pq=h.query((2,2),goal)
   for point in [(x,y) for x in range(1,15) for y in range(1,13) if graph.valid_point((x,y))]:
    optimum=exact.get(point,math.inf)
    assert pq.point_bound(point)<=optimum+1e-8
    assert pq.fast_bound(point)<=optimum+1e-8
    assert math.isfinite(pq.point_bound(point))==math.isfinite(optimum)
   route=pq.geometric_route()
   assert bool(route)==((2,2) in exact and graph.valid_point((2,2)))

from llmastar.research.strategic.planner import StrategicSearch
from llmastar.research.strategic.compiler import region_trace,compile_strategy
from llmastar.research.strategic.schema import Strategy


def test_strategic_corridor_validity_bounds_and_wrong_plan_fallback():
 rng=random.Random(41017)
 for i in range(12):
  q=dict(range_x=[0,24],range_y=[0,21],start=[2,2],goal=[21,18],horizontal_barriers=[[9,0,15]],vertical_barriers=[[12,11,19]])
  q['vertical_barriers'][0][0]=rng.randrange(10,18)
  graph=RasterGridGraph(q);hierarchy=TileHierarchy(graph,5);d=_distances(graph,tuple(q['goal']));opt=d.get(tuple(q['start']),math.inf)
  source=StaticProvider({'version':1,'strategies':[{'id':'bad','regions':['not-a-region']}]},'synthetic')
  for bound in [1.,1.1,2.]:
   for corridor in [False,True]:
    r=StrategicSearch(bound=bound,corridor=corridor,budget_scale=.1).search(q,source,hierarchy)
    assert r['valid']==math.isfinite(opt)
    if r['valid']:assert r['length']<=bound*opt+1e-8


def test_disconnected_hierarchy_and_dynamic_provider_events():
 q=dict(range_x=[0,24],range_y=[0,21],start=[2,2],goal=[21,18],horizontal_barriers=[],vertical_barriers=[[12,0,21]])
 r=StrategicSearch().search(q)
 assert not r['valid'] and r['operation']==0
 q['vertical_barriers']=[[12,0,15]]
 p=ScriptedProvider([{'strategies':[{'id':'x','waypoints':[[2,18]]}]},{'abstain':True}])
 r=StrategicSearch(budget_scale=.1).search(q,p)
 assert r['valid'] and p.actual_api_calls==0
 assert r['operation']>=r['expanded'] and r['unique']<=r['expanded']


def test_refining_portals_remains_admissible_and_strengthens_start_bound():
 q=dict(range_x=[0,26],range_y=[0,23],horizontal_barriers=[[10,0,17]],vertical_barriers=[[14,12,22]])
 goal=(23,19);start=(2,2);bounds=[]
 for span in [None,2,1]:
  graph=RasterGridGraph(q);h=TileHierarchy(graph,6,span);pq=h.query(start,goal);exact=_distances(graph,goal)
  for p,d in exact.items():assert pq.point_bound(p)<=d+1e-8
  bounds.append(pq.lower_bound)
 assert bounds[0]<=bounds[1]+1e-8 and bounds[1]<=bounds[2]+1e-8

import numpy as np
from llmastar.research.strategic.cuts import octile_transform,CutPotential


def test_octile_minplus_transform_against_exhaustive_reference():
 rng=np.random.default_rng(171104)
 for n in [1,2,5,16,31]:
  for dx in [0,1,3,n,n+3]:
   values=rng.random(n)*20;values[rng.random(n)<.25]=np.inf
   dy=np.abs(np.arange(n)[:,None]-np.arange(n)[None,:]);cost=np.maximum(dx,dy)+(math.sqrt(2)-1)*np.minimum(dx,dy)
   expected=np.min(cost+values[None,:],axis=1)
   assert np.allclose(octile_transform(values,dx),expected)


def test_cut_bounds_admissible_for_all_free_starts_and_selected_cuts():
 rng=random.Random(1711404)
 for i in range(20):
  hs=[];vs=[]
  for j in range(5):
   lo=rng.randrange(0,7);hi=rng.randrange(max(lo+1,8),15)
   (hs if j%2 else vs).append([rng.randrange(2,14),lo,hi])
  q=dict(range_x=[0,17],range_y=[0,17],horizontal_barriers=hs,vertical_barriers=vs)
  graph=RasterGridGraph(q);free=[(x,y) for x in range(1,16) for y in range(1,16) if graph.valid_point((x,y))]
  goal=rng.choice(free);exact=_distances(graph,goal)
  for selection in ['all','longest','waypoints']:
   h=CutPotential(q,goal,selection,2,[(3,3),(12,12)])
   for p in free:assert h.value(p)<=exact.get(p,math.inf)+1e-7


def test_fractional_hierarchy_fallback_preserves_requested_bound():
 from llmastar.research.incumbent import IncumbentSearch
 from llmastar.research.geometry import SegmentGridGraph
 q=dict(range_x=[0,24],range_y=[0,21],start=[2,2],goal=[21,18],horizontal_barriers=[[9.5,0,15]],vertical_barriers=[])
 optimum=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],SegmentGridGraph(q))
 r=StrategicSearch(bound=1.).search(q)
 assert r['unsupported_hierarchy'] and abs(r['length']-optimum['length'])<1e-8


def test_prompt_has_explicit_orientation_and_omitted_context():
 from llmastar.research.strategic.prompts import build_prompt
 q=dict(range_x=[0,24],range_y=[0,21],start=[2,2],goal=[21,18],horizontal_barriers=[[9,0,15]],vertical_barriers=[[12,0,4]])
 p=build_prompt(q,obstacle_budget=1);import json
 assert json.loads(p['user'])['obstacles_omitted']==1 and 'y UP' in p['system']
 assert parse_guidance({'version':True,'strategies':[]}).abstain

from llmastar.research.strategic.cut_search import CutStrategySearch,digital_walk,legacy_bypasses
from llmastar.research.geometry import SegmentGridGraph


def test_cut_strategy_bounds_under_adversarial_and_oracle_proposals():
 rng=random.Random(1711504)
 for i in range(14):
  q=dict(range_x=[0,29],range_y=[0,25],start=[2,2],goal=[25,21],horizontal_barriers=[[10,0,18],[17,12,27]],vertical_barriers=[[14,12,23]])
  q['vertical_barriers'][0][0]=rng.randrange(10,20)
  graph=RasterGridGraph(q);exact=_distances(graph,tuple(q['goal']));opt=exact.get(tuple(q['start']),math.inf)
  for bound in [1.,1.1,2.]:
   p=ScriptedProvider([{'strategies':[{'id':'bad','waypoints':[[2,20],[27,3]],'bypasses':[{'obstacle_id':'h0','side':'left'}]}]}, {'abstain':True}])
   r=CutStrategySearch(bound=bound,intervention='blocked',witness=False,budget_scale=.1).search(q,p)
   assert r['valid']==math.isfinite(opt)
   if r['valid']:
    assert r['length']<=bound*opt+1e-7
    assert r['length']==sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:]))


def test_cut_proof_is_independent_of_bad_bypass_direction():
 q=dict(range_x=[0,25],range_y=[0,22],start=[2,2],goal=[21,19],horizontal_barriers=[[10,0,16]],vertical_barriers=[])
 provider=StaticProvider({'strategies':[{'id':'wrong','bypasses':[{'obstacle_id':'h0','side':'left'}]}]},'synthetic')
 r=CutStrategySearch(bound=1.,intervention='initial',witness=False).search(q,provider)
 exact=_distances(RasterGridGraph(q),tuple(q['goal']))[tuple(q['start'])]
 assert r['valid'] and abs(r['length']-exact)<1e-8
 p=CutPotential(q,tuple(q['goal']));assert p.value(tuple(q['start']))<=exact+1e-8
