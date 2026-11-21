"""Paired distributions, quality/work tradeoffs and transparent worst regressions."""
import argparse,math,statistics
from common import read_cases,dump

def main():
 p=argparse.ArgumentParser();p.add_argument('--case-level',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=read_cases(a.case_level);lookup={(r['case_id'],r['method']):r for r in rows};report={}
 for stratum in ['primary','large','all']:
  selected=[r for r in rows if r['method']=='rh_image105' and (stratum=='all' or r['stratum']==stratum)];block={}
  for control in sorted({r['method'] for r in rows}-{'rh_image105'}):
   pairs=[]
   for r in selected:
    other=lookup.get((r['case_id'],control))
    if not other or not(r['valid'] and other['valid']):continue
    x,y=r['queue_operations'],other['queue_operations']
    if x is None or y is None or y<=0:continue
    pairs.append({'case_id':r['case_id'],'family':r['family'],'queue_ratio':x/y,'queue_difference':x-y,'cost_ratio_primary_over_control':r['cost_ratio']/other['cost_ratio'],'primary_cost_over_optimum':r['cost_ratio'],'control_cost_over_optimum':other['cost_ratio'],'primary_native_ms':1000*r['seconds'] if r['seconds'] is not None else None,'control_native_ms':1000*other['seconds'] if other['seconds'] is not None else None})
   if not pairs:continue
   ratios=[r['queue_ratio'] for r in pairs];cost=[r['cost_ratio_primary_over_control'] for r in pairs]
   block[control]={'complete_paired_queries':len(pairs),'queue_wins':sum(v<1-1e-9 for v in ratios),'queue_ties':sum(abs(v-1)<=1e-9 for v in ratios),'queue_losses':sum(v>1+1e-9 for v in ratios),'cost_wins':sum(v<1-1e-9 for v in cost),'cost_ties':sum(abs(v-1)<=1e-9 for v in cost),'cost_losses':sum(v>1+1e-9 for v in cost),'queue_gain_without_worse_path':sum(r['queue_ratio']<1-1e-9 and r['cost_ratio_primary_over_control']<=1+1e-9 for r in pairs),'median_queue_ratio':statistics.median(ratios),'mean_case_queue_ratio':statistics.mean(ratios),'min_queue_ratio':min(ratios),'max_queue_ratio':max(ratios),'worst_ten_queue_regressions':sorted(pairs,key=lambda r:-r['queue_ratio'])[:10],'largest_ten_queue_benefits':sorted(pairs,key=lambda r:r['queue_ratio'])[:10]}
  report[stratum]=block
 dump(a.output,{'scope':'All families retained, complete paired audits only with coverage. Work distribution is physical total heap pushes+pops, not only CLOSED pops. Mean of per-case ratios differs from ratio of aggregate means. Extremes are illustrations, never benchmark selection or tuning.','strata':report})
 print('Saved paired distributions and worst regressions')
if __name__=='__main__':main()
