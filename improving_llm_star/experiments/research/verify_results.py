"""Independent result audit; original Shapely semantics validate emitted paths."""
import gzip,json,math
import numpy as np
from shapely.geometry import LineString
from shapely import linestrings,intersects
from benchmark import cached_cases,ROOT,WORKSPACE,GridGraph
from datasets import generate
from llmastar.research.incumbent import IncumbentSearch


def main():
 base=ROOT/'experiments/results/research';counts={};details={}
 prior={r['id']:r for r in json.loads((WORKSPACE/'table1_reproduction/ergebnisse.json').read_text())}
 config=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True)
 for suite,cases in [('heldout_cached',cached_cases('test',['standard','cot','repe'])),('heldout_synthetic',generate('test',3))]:
  data=json.load(gzip.open(base/suite/'results.json.gz','rt'));runs=data['runs'];by={(r['case_id'],r['variant']):r for r in runs}
  valid=certificates=nopath=baseline_matches=0;graphs={}
  for case in cases:
   if case['map_id'] not in graphs:graphs[case['map_id']]=GridGraph(case['query'])
   graph=graphs[case['map_id']];r=IncumbentSearch(**config).search(case['query'],case['points'],graph)
   stored=by[case['id'],'sieved_cert']
   assert r['length']==stored['length'] and r['unique']==stored['unique']
   if stored['optimal_cost'] is None:
    assert not r['valid'];nopath+=1;continue
   assert r['valid'];q=case['query'];path=r['path']
   assert path[0]==tuple(q['start']) and path[-1]==tuple(q['goal'])
   assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 for a,b in zip(path,path[1:]))
   assert all(q['range_x'][0]<x<q['range_x'][1]-1 and q['range_y'][0]<y<q['range_y'][1]-1 for x,y in path)
   walls=[LineString([(a,y),(b,y)]) for y,a,b in q['horizontal_barriers']]
   walls += [LineString([(x,a),(x,b)]) for x,a,b in q['vertical_barriers']]
   if walls and len(path)>1:
    segments=linestrings(np.array(list(zip(path,path[1:])),dtype=float))
    assert not intersects(segments[:,None],np.array(walls,dtype=object)[None,:]).any()
   assert math.isclose(r['length'],sum(math.dist(a,b) for a,b in zip(path,path[1:])),abs_tol=1e-9)
   valid+=1
   if r['certified_early_return']:
    assert abs(r['length']-stored['optimal_cost'])<1e-8;certificates+=1
   assert r['length']<=2*stored['optimal_cost']+1e-8
   for control in ['wa2','direct_only']:
    other=by[case['id'],control]
    assert r['length']<=other['length']+1e-8 and r['unique']<=other['unique']
   if suite=='heldout_cached':
    _,m,j,prompt=case['id'].split('_');old=prior[f'{m}_{j}'];orig=by[case['id'],'original']
    assert old[prompt+'_op']==orig['operation']
    assert math.isclose(old[prompt+'_len'],orig['length'],abs_tol=1e-8)
    baseline_matches+=1
  counts[suite]={'independently_valid_paths':valid,'exact_optimal_certificates':certificates,
                 'correct_no_path':nopath,'frozen_Table1_matches':baseline_matches}
 out=base/'verification.json';out.write_text(json.dumps(counts,indent=2)+'\n');print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
