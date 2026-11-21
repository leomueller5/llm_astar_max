"""Combine explicitly disjoint method blocks, preserving every original artifact."""
import argparse,hashlib
from pathlib import Path
from common import read_cases,dump

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',nargs='+',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=[];seen=set()
 if Path(a.output).exists():raise FileExistsError(a.output)
 for path in a.inputs:
  for row in read_cases(path)['runs']:
   key=(row['case_id'],row['method'],row.get('seed',0),row['rep'])
   if key in seen:raise ValueError('Overlapping method block; never silently choose a duplicate')
   seen.add(key);rows.append(row)
 dump(a.output,{'scope':'Disjoint frozen main/explicit control blocks; native trials are not fabricated for counts-only controls. Original raw files remain unchanged.','sources':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in a.inputs},'runs':rows});print('Combined',len(rows),'records')
if __name__=='__main__':main()
