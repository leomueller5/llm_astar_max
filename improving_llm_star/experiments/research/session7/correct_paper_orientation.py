"""Normalize the frozen A*'s goal-to-start output; never rerun/change its search."""
import argparse,json
from pathlib import Path
from common import RESULTS,read_cases,dump

def normalize(result,query):
 r=dict(result);path=r.get('path',[])
 if path and tuple(path[0])==tuple(query['goal']) and tuple(path[-1])==tuple(query['start']):
  r['path']=list(reversed(path));r['valid']=True;r['original_path_orientation']='goal_to_start';return r
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cases={c['id']:c for c in read_cases(RESULTS/'heldout_all.json.gz')};raw=read_cases(RESULTS/'paper_denominator/results.json.gz');paths=read_cases(RESULTS/'paper_denominator/paths.json.gz');fixed=[];by={}
 for r in paths:
  n=normalize(r,cases[r['case_id']]['query']);fixed.append(n);by[r['case_id']]=n
 for r in raw['runs']:
  path=by.get(r['case_id'])
  if path and path.get('valid') and r.get('error') is None:
   r['valid']=True;r['cost_ratio']=r['length']/cases[r['case_id']]['optimal_cost'];r['original_path_orientation']='goal_to_start'
 dump(out/'paths.json.gz',fixed);dump(out/'results.json.gz',raw);dump(out/'CORRECTION.json',{'reason':'Frozen PaperAStar.extract_path returns goal->start. The shared original-LLMA evaluator expected start->goal and incorrectly labelled all completed paper paths invalid. Only reverse saved paths and normalize validity/cost ratio; algorithm, scores, times, operations and storage unchanged. Original raw artifacts preserved.','completed_normalized':sum(r['valid'] for r in raw['runs']),'capped':sum(r.get('error')=='timeout' for r in raw['runs'])});print('Corrected orientation of',sum(r['valid'] for r in raw['runs']),'completed paper paths')
if __name__=='__main__':main()
