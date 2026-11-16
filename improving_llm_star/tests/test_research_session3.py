import math,random
import pytest
from llmastar.research.guidance import WaypointGuidanceSearch
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch


def queries():
 rng=random.Random(202611163)
 for _ in range(16):
  yield dict(range_x=[0,19],range_y=[0,17],start=[2,2],goal=[16,14],horizontal_barriers=[[rng.randrange(4,13),4,11]],vertical_barriers=[[rng.randrange(5,14),3,10]])

@pytest.mark.parametrize('mode',['seed','chain','potential','tie','attract'])
def test_guidance_paths_are_valid_and_weight_two_bounded(mode):
 for q in queries():
  opt=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],SegmentGridGraph(q))
  r=WaypointGuidanceSearch(mode=mode).search(q,[[4,12],[12,12],[15,13]],SegmentGridGraph(q))
  assert r['valid']==opt['valid']
  if r['valid']:
   assert r['length']<=2*opt['length']+1e-8
   assert r['length']==sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:]))
   assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 for a,b in zip(r['path'],r['path'][1:]))


def test_disabled_guidance_is_independent_of_input_points():
 for q in queries():
  p=WaypointGuidanceSearch(use_waypoints=False)
  a=p.search(q,[],SegmentGridGraph(q));b=p.search(q,[[1000,1000],[5,6]],SegmentGridGraph(q))
  assert a['path']==b['path'] and a['operation']==b['operation']


def test_invalid_unreachable_and_trivial_endpoints():
 q=dict(range_x=[0,12],range_y=[0,12],start=[2,5],goal=[9,5],horizontal_barriers=[],vertical_barriers=[[6,0,12]])
 r=WaypointGuidanceSearch().search(q,[[6,5]],SegmentGridGraph(q));assert not r['valid']
 q['start']=q['goal']=[2,2];r=WaypointGuidanceSearch().search(q,[],SegmentGridGraph(q));assert r['valid'] and r['length']==0
 q['start']=[0,0];r=WaypointGuidanceSearch().search(q,[],SegmentGridGraph(q));assert not r['valid']

@pytest.mark.parametrize('mode',['seed','chain','potential','tie','attract'])
def test_guidance_execution_without_geometry_early_exit(mode):
 for q in queries():
  opt=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],SegmentGridGraph(q))
  r=WaypointGuidanceSearch(mode=mode,witness=False,max_seeds=3).search(q,[[3,3],[3,12],[14,13]],SegmentGridGraph(q))
  assert r['valid']==opt['valid']
  if r['valid']:
   assert r['length']<=2*opt['length']+1e-8
   assert all(math.isfinite(SegmentGridGraph(q).cost(a,b)) for a,b in zip(r['path'],r['path'][1:]))


def test_seeded_prefix_is_expanded_into_real_unit_edges():
 q=dict(range_x=[0,24],range_y=[0,24],start=[2,2],goal=[20,20],horizontal_barriers=[],vertical_barriers=[])
 p=WaypointGuidanceSearch(witness=False,filtering='rank')
 r=p.search(q,[[17,17]],SegmentGridGraph(q));off=WaypointGuidanceSearch(witness=False,use_waypoints=False).search(q,[],SegmentGridGraph(q))
 assert r['guidance_accepted']==1 and r['unique']<off['unique']
 assert r['length']==off['length'] and r['path'][0]==(2,2) and r['path'][-1]==(20,20)


def test_ranking_is_invariant_to_waypoint_order():
 q=dict(range_x=[0,24],range_y=[0,24],start=[2,2],goal=[20,20],horizontal_barriers=[],vertical_barriers=[])
 p=WaypointGuidanceSearch(witness=False,filtering='rank');pts=[[4,8],[17,17],[15,16]]
 a=p.search(q,pts,SegmentGridGraph(q));b=p.search(q,list(reversed(pts)),SegmentGridGraph(q))
 assert a['path']==b['path'] and a['operation']==b['operation']


def test_lazy_rank_has_identical_paths_and_counts_to_eager_rank():
 for q in queries():
  pts=[[4,12],[14,13],[3,4],[6,12]]
  a=WaypointGuidanceSearch(witness=False).search(q,pts,SegmentGridGraph(q))
  b=WaypointGuidanceSearch(witness=False,lazy=True).search(q,pts,SegmentGridGraph(q))
  assert a['path']==b['path'] and a['operation']==b['operation'] and a['guidance_accepted']==b['guidance_accepted']


def test_public_seed_interface_immutable_and_cache_only():
 import copy
 from llmastar.pather import SeededLLMAStar
 q=next(queries());saved=copy.deepcopy(q)
 for enabled in [False,True]:
  p=SeededLLMAStar(waypoint_response='Generated Path: [[2,2],[4,12],[16,14]]',guidance=enabled)
  r=p.searching(q)
  assert q==saved and set(r)=={'operation','storage','length','llm_output'}
  assert p.search_metrics['path_valid']
