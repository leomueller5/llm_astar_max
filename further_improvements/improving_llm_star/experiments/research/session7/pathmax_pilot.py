"""Pathmax integration: same-engine off/on and no-LLM/uniform controls."""
import argparse,statistics
from common import read_cases,dump
from prompts_spatial import decode
from evaluate import permuted
from llmastar.research.pathmax_guidance import PathmaxResidualSearch

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();cache={(r['case_id'],r['representation']):r for r in read_cases(a.responses)['runs']};rows=[]
 for c in read_cases(a.cases):
  f,_=decode(c['query'],cache[c['id'],'image']['response']['choices'][0]['message']['content'],4,'cost')
  for method in ['none','real','shuffled','uniform105']:
   for pathmax in [False,True]:
    field=None if method in ['none','uniform105'] else f if method=='real' else permuted(f,c['id']);r=PathmaxResidualSearch(pathmax=pathmax,base_weight=1.05 if method=='uniform105' else 1.).search(c['query'],field);assert r['valid'] and r['length']<=1.05*c['optimal_cost']+1e-7
    rows.append({'case_id':c['id'],'family':c['family'],'method':method,'pathmax':pathmax,'pops':r['heap_pops'],'pushes':r['heap_pushes'],'unique':r['unique'],'reopens':r['reopens'],'raises':r['pathmax_raises'],'clips':r['pathmax_clipped'],'cost_ratio':r['length']/c['optimal_cost'],'diagnostic_seconds':r['total_seconds'],'path':r['path']})
 dump(a.output,{'scope':'Independent late hypothesis, development/validation only, no API calls. Established pathmax adapted with pointwise w*anchor cap. Cap can prevent global consistency; only existing bounded-suboptimal argument claimed. Single diagnostic timing is not native result.','runs':rows})
 for method in ['none','real','shuffled','uniform105']:
  for active in [False,True]:
   rr=[r for r in rows if r['method']==method and r['pathmax']==active];print(method,active,'pops',statistics.mean(r['pops'] for r in rr),'queue',statistics.mean(r['pops']+r['pushes'] for r in rr),'unique',statistics.mean(r['unique'] for r in rr),'raises',sum(r['raises'] for r in rr))
if __name__=='__main__':main()
