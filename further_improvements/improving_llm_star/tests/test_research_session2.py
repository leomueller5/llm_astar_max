import math,random
from llmastar.research.search import GridGraph,LazyGridGraph,MOTIONS
from llmastar.research.geometry import IndexedGridGraph
from llmastar.research.incumbent import IncumbentSearch


def maps():
 rng=random.Random(16112026)
 for _ in range(20):
  hs=[];vs=[]
  for j in range(12):
   lo=rng.randrange(0,11);hi=rng.randrange(lo,12)
   (hs if j%2 else vs).append([rng.randrange(0,12),lo,hi])
  yield dict(range_x=[0,13],range_y=[0,13],horizontal_barriers=hs,vertical_barriers=vs,start=[1,1],goal=[11,11])


def test_indexed_edges_occupancy_and_degenerate_semantics():
 for q in maps():
  old=LazyGridGraph(q);new=IndexedGridGraph(q)
  for x in range(0,13):
   for y in range(0,13):
    a=x,y
    assert old.valid_point(a)==new.valid_point(a)
    for dx,dy in MOTIONS:
     b=x+dx,y+dy
     assert old.collision(a,b)==new.collision(a,b)
     assert old.cost(a,b)==new.cost(a,b)
    assert old.adj.get(a,[])==new.adj.get(a,[])


def test_indexed_geometry_preserves_certificate_search():
 for q in maps():
  params=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True)
  a=IncumbentSearch(**params).search(q,[[5,5],[7,9]],LazyGridGraph(q))
  b=IncumbentSearch(**params).search(q,[[5,5],[7,9]],IndexedGridGraph(q))
  assert a['path']==b['path'] and a['operation']==b['operation'] and a['length']==b['length']


def test_noninteger_geometry_uses_legacy_fallback():
 q=dict(range_x=[0,9],range_y=[0,9],horizontal_barriers=[],vertical_barriers=[[3.5,1,6]],start=[1,1],goal=[7,7])
 old=LazyGridGraph(q);new=IndexedGridGraph(q)
 assert not new.indexed
 for x in range(1,8):
  for y in range(1,8):
   a=x,y
   assert old.adj.get(a,[])==new.adj.get(a,[])

from llmastar.research.efficient import EfficientCertificateSearch


def test_reachable_certificate_and_uncertified_variants_are_valid_and_bounded():
 for q in maps():
  old=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True).search(q,[],IndexedGridGraph(q))
  for options in [{},{'ordering':'goal_first'},{'gate':'detour'},{'repair_radius':0},{'uncertified':'prune'},{'uncertified':'accept_bound'}]:
   r=EfficientCertificateSearch(**options).search(q,[[2,5],[4,7],[8,8]],IndexedGridGraph(q))
   assert r['valid']==old['valid']
   if r['valid']:
    assert r['length']<=2*old['length']+1e-9
    assert r['length']==sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:]))
    assert all(math.isfinite(IndexedGridGraph(q).cost(a,b)) for a,b in zip(r['path'],r['path'][1:]))
    if r['certified_early_return']:assert math.isclose(r['length'],old['length'],abs_tol=1e-9)


def test_empty_budget_falls_back_identically_and_respects_visibility_limit():
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5])
 base=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True).search(q,[],IndexedGridGraph(q))
 for budget in [0,1,7,100,4096]:
  r=EfficientCertificateSearch(visibility_budget=budget).search(q,[[8,8],[8,9]],IndexedGridGraph(q))
  assert r['visibility_edge_checks']<=budget
  assert r['valid'] and r['length']<=base['length']+1e-9
  if budget==0:assert r['operation']==base['operation'] and r['path']==base['path']

from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route


def test_continuous_piece_verification_equals_emitted_unit_edges():
 for q in maps():
  graph=SegmentGridGraph(q);old=LazyGridGraph(q);rng=random.Random(32)
  for _ in range(50):
   a=(rng.randrange(1,12),rng.randrange(1,12));b=(rng.randrange(1,12),rng.randrange(1,12))
   if a==b:continue
   route=graph.lattice_segment(a,b);reference=old.shortcut(a,b)
   assert bool(route)==bool(reference)
   if route:assert expand_lattice_route(route)==reference


def test_analytic_certificate_matches_unit_certificate():
 for q in maps():
  pts=[[2,3],[4,6],[8,9]]
  a=EfficientCertificateSearch().search(q,pts,IndexedGridGraph(q))
  b=EfficientCertificateSearch(segment_mode='analytic').search(q,pts,SegmentGridGraph(q))
  assert a['valid']==b['valid'] and a['length']==b['length'] and a['unique']==b['unique']

from llmastar.research.efficient import compress_collinear


def test_collinear_filter_preserves_turns_and_backtracking():
 assert compress_collinear([(1,1),(2,2),(3,3),(3,3),(4,4),(4,5),(4,6)])==[(1,1),(4,4),(4,6)]
 assert compress_collinear([(1,1),(2,2),(1,1)])==[(1,1),(2,2),(1,1)]


def test_quality_gate_never_mislabels_loose_certificate_as_optimal():
 for q in maps():
  optimum=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True).search(q,[],IndexedGridGraph(q))
  r=EfficientCertificateSearch(segment_mode='analytic',certificate_ratio=1.1,compress=True).search(q,[[3,5],[6,8],[9,9]],SegmentGridGraph(q))
  if r['valid']:
   assert r['length']<=2*optimum['length']+1e-9
   if r['certified_early_return']:assert math.isclose(r['length'],optimum['length'],abs_tol=1e-9)
   if r['bounded_early_return']:assert r['length']<=1.1*optimum['length']+1e-9

from llmastar.research.scheduled import ScheduledCertificateSearch


def test_scheduled_and_frontier_variants_preserve_validity_and_bound():
 for q in maps():
  optimum=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True).search(q,[],IndexedGridGraph(q))
  planners=[ScheduledCertificateSearch(threshold=1),ScheduledCertificateSearch(threshold=16),EfficientCertificateSearch(segment_mode='analytic',compress=True,uncertified='frontier',chain_only=True,repair_radius=0)]
  for planner in planners:
   r=planner.search(q,[[3,5],[6,8],[9,9]],SegmentGridGraph(q))
   assert r['valid']==optimum['valid']
   if r['valid']:assert r['length']<=2*optimum['length']+1e-9


def test_scheduled_no_guidance_control_has_identical_search_order():
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5])
 a=ScheduledCertificateSearch(use_waypoints=False,direct=False).search(q,[],SegmentGridGraph(q))
 b=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True).search(q,[],SegmentGridGraph(q))
 assert a['path']==b['path'] and a['operation']==b['operation'] and a['unique']==b['unique']


def test_lean_fallback_matches_legacy_and_noninteger_cut_bound_disabled():
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5])
 a=EfficientCertificateSearch(segment_mode='analytic',compress=True).search(q,[[8,8]],SegmentGridGraph(q))
 b=EfficientCertificateSearch(segment_mode='analytic',compress=True,fallback_engine='lean',reuse_validation=True).search(q,[[8,8]],SegmentGridGraph(q))
 assert a['path']==b['path'] and a['length']==b['length'] and a['operation']==b['operation']
 q['vertical_barriers']=[[8.5,0,8.1]]
 r=EfficientCertificateSearch(segment_mode='analytic').search(q,[[8,9]],SegmentGridGraph(q))
 from llmastar.research.search import octile
 assert r['start_lower_bound']==octile(tuple(q['start']),tuple(q['goal']))


def test_wall_witnesses_are_verified_optimal_and_not_credited_to_llm():
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5])
 optimum=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],IndexedGridGraph(q))
 for hints in [[],[[8,8]],[[1,11]]]:
  r=EfficientCertificateSearch(segment_mode='analytic',witness=True,fallback_engine='lean',reuse_validation=True).search(q,hints,SegmentGridGraph(q))
  assert r['valid'] and r['length']==optimum['length']
  assert r['candidate_source']=='wall_witness' and r['certified_early_return'] and r['unique']==0

from llmastar.research.corridor import CorridorSearch


def test_corridor_fallback_validity_cost_and_operation_accounting():
 for q in maps():
  optimum=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],IndexedGridGraph(q))
  for hints in [[],[[5,6],[7,8]],[[0,0]]]:
   r=CorridorSearch(expansion_cap=8,max_cells=256).search(q,hints,SegmentGridGraph(q))
   assert r['valid']==optimum['valid']
   assert r['operation']>=r['unique']
   if r['valid']:assert r['length']<=2*optimum['length']+1e-9


def test_public_witness_interface_is_offline_immutable_and_baseline_compatible():
 import copy
 from llmastar.pather import WitnessFirstLLMAStar
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5]);saved=copy.deepcopy(q)
 for policy in ['exact','frontier']:
  p=WitnessFirstLLMAStar(waypoint_response='Generated Path: [[3,5],[8,8],[13,5]]',policy=policy)
  result=p.searching(q)
  assert q==saved and set(result)=={'operation','storage','length','llm_output'}
  assert p.search_metrics['path_valid'] and p.search_metrics['accepted_source']=='wall_witness'


def test_no_guidance_public_mode_skips_initial_model_request():
 from llmastar.pather import WitnessFirstLLMAStar
 q=dict(range_x=[0,17],range_y=[0,13],horizontal_barriers=[],vertical_barriers=[[8,0,8]],start=[3,5],goal=[13,5])
 p=WitnessFirstLLMAStar(use_waypoints=False)
 class ForbiddenModel:
  def ask(self,**kwargs):raise AssertionError('No guidance mode must not call a model')
 p.model=ForbiddenModel();r=p.searching(q)
 assert p.search_metrics['path_valid'] and r['llm_output']==[(3,5),(13,5)]


def test_fractional_and_degenerate_segment_fallback_emits_exact_unit_walk():
 q=dict(range_x=[0,13],range_y=[0,13],horizontal_barriers=[[6,3,3],[8.5,1,5.5]],vertical_barriers=[[4.5,0,3]],start=[1,1],goal=[11,11])
 g=SegmentGridGraph(q);old=LazyGridGraph(q)
 for a,b in [((1,1),(11,11)),((2,7),(9,10)),((1,5),(11,5)),((3,6),(10,10))]:
  route=g.lattice_segment(a,b);reference=old.shortcut(a,b)
  assert bool(route)==bool(reference)
  if route:assert expand_lattice_route(route)==reference
