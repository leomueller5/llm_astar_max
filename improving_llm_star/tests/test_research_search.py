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
