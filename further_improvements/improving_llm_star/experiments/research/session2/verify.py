"""Independent Shapely path audit for frozen final cohorts; run after timing finishes."""
import sys,json,gzip,math
from pathlib import Path
import numpy as np
from shapely.geometry import LineString
from shapely import linestrings,intersects
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import execute,cached_cases,ROOT


def main():
 base=ROOT/'experiments/results/research_session2';output={}
 for cohort in ['fresh_core','opened_cached_confirmation']:
  with gzip.open(base/cohort/'results.json.gz','rt') as f:data=json.load(f)
  stored={(r['case_id'],r['variant']):r for r in data['runs'] if r['repeat']==0}
  if cohort=='fresh_core':
   with gzip.open(base/'fresh_cases.json.gz','rt') as f:cases=json.load(f)
  else:cases=cached_cases('test',['standard','cot','repe'])
  counts={};walls={}
  for mode in ['witness_only','witness_cf','witness_chain','witness_frontier']:
   valid=certificates=failed=0
   for c in cases:
    r=execute(mode,c);expected=stored[c['id'],mode];optimal=stored[c['id'],'indexed_astar']
    assert r['valid']==expected['valid'] and r['unique']==expected['unique'] and r['operation']==expected['operation']
    if not optimal['valid']:
     assert not r['valid'];failed+=1;continue
    assert r['valid'];path=r['path'];q=c['query']
    assert path[0]==tuple(q['start']) and path[-1]==tuple(q['goal'])
    assert all(q['range_x'][0]<x<q['range_x'][1]-1 and q['range_y'][0]<y<q['range_y'][1]-1 for x,y in path)
    assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 for a,b in zip(path,path[1:]))
    if c['map_id'] not in walls:
     walls[c['map_id']]=np.array([LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']],dtype=object)
    if len(path)>1 and len(walls[c['map_id']]):
     segments=linestrings(np.array(list(zip(path,path[1:])),dtype=float))
     assert not intersects(segments[:,None],walls[c['map_id']][None,:]).any()
    cost=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    assert abs(cost-r['length'])<1e-8 and abs(cost-expected['length'])<1e-8
    assert cost<=2*optimal['length']+1e-8
    if r['certified_early_return']:
     assert abs(cost-optimal['length'])<1e-8;certificates+=1
    if mode in ['witness_only','witness_cf']:
     control=stored[c['id'],'scheduled_wa2' if mode=='witness_only' else 'witness_only']
     assert cost<=control['length']+1e-8 and r['unique']<=control['unique']
    valid+=1
   counts[mode]={'independent_valid_paths':valid,'optimal_certificates':certificates,'correctly_exhausted_unreachable':failed}
   print(cohort,mode,counts[mode],flush=True)
  # All saved algorithms agree on reachability; frozen failures kept as explicit errors.
  disagreements=[(c['id'],m) for c in cases for m in data['variants'] if stored[c['id'],m]['valid']!=stored[c['id'],'indexed_astar']['valid']]
  assert not disagreements
  counts['frozen_original_unreachable_exceptions']=sum(bool(stored[c['id'],'original_indexed'].get('error')) for c in cases)
  if cohort=='opened_cached_confirmation':
   previous=json.loads((ROOT.parent/'table1_reproduction/ergebnisse.json').read_text());lookup={v['id']:v for v in previous}
   matches=0
   for c in cases:
    _,m,j,prompt=c['id'].split('_');r=stored[c['id'],'original_indexed'];old=lookup[f'{m}_{j}']
    assert r['operation']==old[prompt+'_op'] and abs(r['length']-old[prompt+'_len'])<1e-8;matches+=1
   counts['frozen_Table1_matches']=matches
  output[cohort]=counts
 (base/'verification.json').write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__':main()
