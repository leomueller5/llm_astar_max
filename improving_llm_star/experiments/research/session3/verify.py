"""Independent path/cost/weight-bound checks on all frozen selected cases."""
import sys,json,gzip,math
from pathlib import Path
import numpy as np
from shapely import linestrings,intersects
from shapely.geometry import LineString
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import ROOT,execute,cached_cases,add_ablation_inputs


def main():
 base=ROOT/'experiments/results/research_session3';output={}
 for cohort in ['validation','fresh']:
  with gzip.open(base/cohort/'results.json.gz','rt') as f:data=json.load(f)
  by={(r['case_id'],r['variant']):r for r in data['runs'] if r['repeat']==0}
  if cohort=='validation':cases=add_ablation_inputs(cached_cases('validation',['standard','cot','repe']))
  else:
   with gzip.open(base/'fresh_cases.json.gz','rt') as f:cases=json.load(f)
  counts={};walls={}
  for mode in ['seed_cut','seed_lazy','potential_visible']:
   valid=failed=0
   for c in cases:
    r=execute(mode,c);stored=by[c['id'],mode];ref=by[c['id'],'indexed_astar']
    assert r['valid']==stored['valid']==ref['valid'] and r['operation']==stored['operation'] and r['unique']==stored['unique']
    if not r['valid']:failed+=1;continue
    p=r['path'];q=c['query'];assert p[0]==tuple(q['start']) and p[-1]==tuple(q['goal'])
    assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 for a,b in zip(p,p[1:]))
    assert all(q['range_x'][0]<x<q['range_x'][1]-1 and q['range_y'][0]<y<q['range_y'][1]-1 for x,y in p)
    if c['map_id'] not in walls:walls[c['map_id']]=np.array([LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']],dtype=object)
    if len(p)>1 and len(walls[c['map_id']]):assert not intersects(linestrings(np.array(list(zip(p,p[1:])),dtype=float))[:,None],walls[c['map_id']][None,:]).any()
    cost=sum(math.dist(a,b) for a,b in zip(p,p[1:]));assert abs(cost-stored['length'])<1e-8 and cost<=2*ref['length']+1e-8
    valid+=1
   counts[mode]={'independently_valid_paths':valid,'correct_no_path':failed};print(cohort,mode,counts[mode],flush=True)
  assert all(by[c['id'],m]['valid']==by[c['id'],'indexed_astar']['valid'] for c in cases for m in data['variants'])
  output[cohort]=counts
 (base/'verification.json').write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__':main()
