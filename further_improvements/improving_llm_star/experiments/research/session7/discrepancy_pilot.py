"""Development/validation-only policy-discrepancy experiment; no API calls."""
import argparse,statistics
from time import perf_counter
from common import read_cases,dump
from prompts_spatial import decode
from evaluate import permuted
from llmastar.research.discrepancy_guidance import DiscrepancyGuidedSearch
from llmastar.research.spatial_guidance import SpatialSearch

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();cache={(r['case_id'],r['representation']):r for r in read_cases(a.responses)['runs']};rows=[]
 for c in read_cases(a.cases):
  row=cache[c['id'],'image'];raw=row['response']['choices'][0]['message']['content'];field,_=decode(c['query'],raw,4,'cost')
  for mode in ['none','real','shuffled','uniform105']:
   tick=perf_counter()
   if mode=='uniform105':r=SpatialSearch(mode='weighted',bound=1.05,base_weight=1.05).search(c['query'])
   else:r=DiscrepancyGuidedSearch().search(c['query'],None if mode=='none' else field if mode=='real' else permuted(field,c['id']))
   seconds=perf_counter()-tick;assert r['valid'] and r['length']<=1.05*c['optimal_cost']+1e-7
   rows.append({'case_id':c['id'],'family':c['family'],'method':mode,'seconds_diagnostic_only':seconds,'pops':r['heap_pops'],'pushes':r['heap_pushes'],'unique':r['unique'],'cost_ratio':r['length']/c['optimal_cost'],'path':r['path']})
 dump(a.output,{'scope':'New local-policy discrepancy representation motivated by focal/discrepancy literature; dev/validation only. All legal edges retained, anchor determines eligibility, stale entries skipped and better paths reopen. No paid requests. Diagnostic single timings, not native runtime claims.','runs':rows})
 for mode in ['none','real','shuffled','uniform105']:
  rr=[r for r in rows if r['method']==mode];print(mode,'pops',statistics.mean(r['pops'] for r in rr),'queue_ops',statistics.mean(r['pops']+r['pushes'] for r in rr),'unique',statistics.mean(r['unique'] for r in rr))
if __name__=='__main__':main()
