import math
import pytest
from llmastar.research.search import GridGraph, WaypointSearch, SearchConfig, MOTIONS
from llmastar.utils import is_lines_collision


def query():
 return {'start':[3,5],'goal':[13,5],'range_x':[0,17],'range_y':[0,13],
         'horizontal_barriers':[],'vertical_barriers':[[8,0,8]]}


def test_exact_grid_collision_matches_shapely_all_unit_edges():
 q=query();g=GridGraph(q)
 for x in range(1,16):
  for y in range(1,12):
   for dx,dy in MOTIONS:
    a=(x,y);b=(x+dx,y+dy)
    if not g.inside(b):continue
    expected=is_lines_collision([a,b],[(8,0),(8,8)])
    assert g.collision(a,b)==expected


@pytest.mark.parametrize('method',['weighted','focal'])
@pytest.mark.parametrize('switch',['neighbor','pop','budget'])
def test_guided_search_validity_and_focal_bound(method,switch):
 q=query();g=GridGraph(q)
 opt=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(q,[q['start'],q['goal']],g)
 r=WaypointSearch(SearchConfig(method=method,switch=switch,filter_points=True)).search(q,[q['start'],[7,3],q['goal']],g)
 assert r['valid']
 assert r['length']==pytest.approx(sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:])))
 if method=='focal':assert r['length']<=1.1*opt['length']+1e-9


def test_disconnected_no_path():
 q=query();q['vertical_barriers']=[[8,0,12]]
 for method in ['weighted','focal']:
  r=WaypointSearch(SearchConfig(method=method)).search(q,[q['start'],q['goal']])
  assert not r['valid'] and r['length'] is None

from llmastar.research.incumbent import IncumbentSearch


def test_incumbent_certifies_real_path_not_llm_segments():
 q=query();g=GridGraph(q)
 # Incorrect target on barrier must not create an invalid incumbent.
 for pts in [[q['start'],[8,8],q['goal']],[q['start'],[7,9],[9,9],q['goal']]]:
  r=IncumbentSearch().search(q,pts,g)
  assert r['valid']
  assert r['length']==pytest.approx(sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:])))


def test_early_certificate_and_budget():
 q=query();q['vertical_barriers']=[]
 r=IncumbentSearch().search(q,[q['start'],q['goal']])
 assert r['certified_early_return'] and r['operation']==0
 assert r['length']==10
 for budget in [0,1,10]:
  r=IncumbentSearch(visibility_budget=budget).search(q,[q['start'],[7,3],q['goal']])
  assert r['valid'] and r['visibility_edge_checks']<=budget

from llmastar.research.incumbent import obstacle_lower_bound


def test_obstacle_cut_bound_is_exact_for_single_wall():
 q=query();g=GridGraph(q)
 oracle=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(q,[q['start'],q['goal']],g)
 assert obstacle_lower_bound(g,tuple(q['start']),tuple(q['goal']))==pytest.approx(oracle['length'])


def test_cut_bound_never_overestimates_on_random_small_maps():
 import random
 for seed in range(25):
  rng=random.Random(seed);q=query()
  q['vertical_barriers']=[[rng.randrange(4,12),rng.randrange(0,4),rng.randrange(6,11)] for _ in range(3)]
  g=GridGraph(q);free=[n for n,e in g.adj.items() if e]
  for _ in range(8):
   a,b=rng.sample(free,2);q['start'],q['goal']=a,b
   oracle=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(q,[a,b],g)
   if oracle['valid']:assert obstacle_lower_bound(g,a,b)<=oracle['length']+1e-9


def test_repaired_incumbent_and_certificate_bound():
 q=query();g=GridGraph(q)
 oracle=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(q,[q['start'],q['goal']],g)
 r=IncumbentSearch(repair_radius=1,obstacle_certificate=True).search(q,[q['start'],[8,8],q['goal']],g)
 assert r['valid']
 if r['certified_early_return']:assert r['length']<=1.02*oracle['length']+1e-9


def test_mixed_wall_cut_bound_and_certificates_on_independent_random_maps():
 import random
 for seed in range(30,60):
  rng=random.Random(seed);q=query();q['range_x']=[0,13];q['range_y']=[0,11]
  q['vertical_barriers']=[[rng.randrange(2,10),rng.randrange(0,3),rng.randrange(5,10)] for _ in range(2)]
  q['horizontal_barriers']=[[rng.randrange(2,8),rng.randrange(0,3),rng.randrange(6,12)] for _ in range(2)]
  g=GridGraph(q);free=[p for p,e in g.adj.items() if e]
  for _ in range(5):
   a,b=rng.sample(free,2);q['start'],q['goal']=a,b
   oracle=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(q,[a,b],g)
   baseline=WaypointSearch(SearchConfig(alpha=0,goal_weight=2)).search(q,[a,b],g)
   pts=[a]+rng.sample(free,min(4,len(free)))+[b]
   r=IncumbentSearch(certificate=1,repair_radius=1,obstacle_certificate=True,
                     certificate_only=True,lazy_certificate=True).search(q,pts,g)
   assert r['valid']==oracle['valid']
   if oracle['valid']:
    assert obstacle_lower_bound(g,a,b)<=oracle['length']+1e-9
    assert r['length']<=baseline['length']+1e-9
    assert r['unique']<=baseline['unique']
    if r['certified_early_return']:assert r['length']==pytest.approx(oracle['length'])


def test_shortcut_is_a_real_octile_shortest_walk():
 q=query();q['vertical_barriers']=[];g=GridGraph(q)
 from llmastar.research.search import octile
 for a,b in [((2,2),(12,8)),((12,8),(2,2)),((3,9),(3,2))]:
  path=g.shortcut(a,b)
  assert sum(math.dist(x,y) for x,y in zip(path,path[1:]))==pytest.approx(octile(a,b))

from llmastar.research.search import LazyGridGraph


def test_lazy_graph_matches_precomputed_results():
 q=query();pts=[q['start'],[8,8],q['goal']]
 config=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True)
 a=IncumbentSearch(**config).search(q,pts,GridGraph(q))
 b=IncumbentSearch(**config).search(q,pts,LazyGridGraph(q))
 assert a['path']==b['path'] and a['operation']==b['operation']


def test_certified_planner_cached_interface_and_input_immutability():
 import copy
 from llmastar.pather import CertifiedLLMAStar
 q=query();original=copy.deepcopy(q)
 planner=CertifiedLLMAStar(waypoint_response='Generated Path: [[3,5],[8,8],[13,5]]')
 r=planner.searching(q)
 assert q==original
 assert set(r)=={'operation','storage','length','llm_output'}
 assert planner.search_metrics['path_valid']
 assert r['length']==pytest.approx(sum(math.dist(a,b) for a,b in zip(planner.path,planner.path[1:])))


def test_invalid_endpoint_and_trivial_case():
 q=query();q['start']=q['goal']=[0,0]
 r=IncumbentSearch().search(q,[])
 assert not r['valid'] and r['path']==[] and r['length'] is None
 q['start']=q['goal']=[2,2]
 r=IncumbentSearch().search(q,[])
 assert r['valid'] and r['length']==0


def test_certificate_sieve_does_not_lose_a_certifiable_route():
 q=query();g=GridGraph(q);pts=[q['start'],[8,8],[7,3],[2,7],q['goal']]
 kw=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True)
 a=IncumbentSearch(**kw).search(q,pts,g)
 b=IncumbentSearch(**kw,certificate_pruning=True).search(q,pts,g)
 assert a['length']==b['length'] and a['unique']==b['unique']
 assert b['visibility_edge_checks']<=a['visibility_edge_checks']


def test_wall_cut_bound_exhaustive_small_integer_wall_maps():
 """All free start/goal pairs, both orientations, every nondegenerate wall interval."""
 import heapq
 from llmastar.research.incumbent import obstacle_lower_bound
 for horizontal in [False,True]:
  for coordinate in range(1,6):
   for lo in range(1,5):
    for hi in range(lo+1,6):
     q={'start':[1,1],'goal':[5,5],'range_x':[0,7],'range_y':[0,7],
        'horizontal_barriers':[[coordinate,lo,hi]] if horizontal else [],
        'vertical_barriers':[] if horizontal else [[coordinate,lo,hi]]}
     graph=GridGraph(q)
     states=[(x,y) for x in range(1,6) for y in range(1,6) if graph.valid_point((x,y))]
     for start in states:
      distances={start:0.};queue=[(0.,start)]
      while queue:
       cost,node=heapq.heappop(queue)
       if cost!=distances[node]:continue
       for other,edge in graph.adj.get(node,[]):
        candidate=cost+edge
        if candidate<distances.get(other,math.inf):
         distances[other]=candidate;heapq.heappush(queue,(candidate,other))
      for goal in states:
       assert obstacle_lower_bound(graph,start,goal)<=distances.get(goal,math.inf)+1e-9
