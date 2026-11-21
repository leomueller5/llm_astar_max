"""Independent dense-edge/path-cost audit of saved results; no search or API calls."""
import argparse,math,collections
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from common import read_cases,dump

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--paths',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};checked=collections.Counter();invalid=[];edges=0;trees={}
 for r in read_cases(a.paths):
  c=cases[r['case_id']];q=c['query'];path=r['path']
  if not r['valid']:invalid.append({'case_id':c['id'],'method':r['method']});continue
  if c['id'] not in trees:
   walls=[LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']];trees[c['id']]=(walls,STRtree(walls))
  walls,tree=trees[c['id']];assert tuple(path[0])==tuple(q['start']) and tuple(path[-1])==tuple(q['goal'])
  for v in path:
   assert all(float(x).is_integer() for x in v)
   assert q['range_x'][0]<v[0]<q['range_x'][1]-1 and q['range_y'][0]<v[1]<q['range_y'][1]-1
   point=Point(v);assert not any(point.intersects(walls[int(i)]) for i in tree.query(point))
  for v,w in zip(path,path[1:]):
   assert max(abs(v[0]-w[0]),abs(v[1]-w[1]))==1
   line=LineString([v,w]);assert not any(line.intersects(walls[int(i)]) for i in tree.query(line));edges+=1
  cost=sum(math.dist(v,w) for v,w in zip(path,path[1:]));assert abs(cost-r['length'])<1e-6
  assert cost>=c['optimal_cost']-1e-6,(c['id'],r['method'],'cost below independently checked optimum')
  bound=1.05 if (r['method'].startswith('rh_') and r['method']!='rh_image2') or r['method'] in ['matched_uniform105','optimized_uniform105','cut105','vm_geo105'] else 2.
  if r['method'] in ['astar_octile','astar_cut','paper_astar','matched_zero']:bound=1.
  if r['method'] not in ['original','original_bounds','robust_original','original_goal_only','robust_goal_only']:assert cost<=bound*c['optimal_cost']+1e-6
  checked[r['method']]+=1
 dump(a.output,{'checked_paths':sum(checked.values()),'checked_edges':edges,'by_method':checked,'declared_invalid':invalid,'all_returned_valid_paths_independently_pass':True,'checker':'Shapely closed-segment STRtree; integer grid, strict bounds, endpoints, unit neighbours, recomputed Euclidean cost and declared search bound.'});print(sum(checked.values()),'paths',edges,'edges passed')
if __name__=='__main__':main()
