"""Is reported confidence useful beyond changing overall heuristic amplitude?"""
import argparse,math,statistics
from common import read_cases,dump
from prompts_spatial import decode
from cost_controls import Scaled
from llmastar.research.spatial_guidance import RegionField,SpatialSearch

def constant_confidence(field):
 out=RegionField(field.query,field.side);den=sum(d for d,p,c in field.values.values());k=sum(d*c for d,p,c in field.values.values())/den if den else 0.
 out.update([{'region_id':rid,'detour':d,'priority':p,'confidence':k} for rid,(d,p,c) in field.values.items()]);assert math.isclose(sum(d*c for d,p,c in field.values.values()),sum(d*c for d,p,c in out.values.values()),abs_tol=1e-8);return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();responses={(r['case_id'],r['representation']):r for r in read_cases(a.responses)['runs']};rows=[]
 for c in read_cases(a.cases):
  f,_=decode(c['query'],responses[c['id'],'image']['response']['choices'][0]['message']['content'],4,'cost')
  for name,field in [('reported',f),('constant_equal_mean',constant_confidence(f))]:
   r=SpatialSearch(mode='heuristic_envelope',bound=1.05,base_weight=1.).search(c['query'],Scaled(field,.22640953779865894));assert r['valid'] and r['length']<=1.05*c['optimal_cost']+1e-7;rows.append({'case_id':c['id'],'family':c['family'],'method':name,'pops':r['heap_pops'],'queue_ops':r['heap_pops']+r['heap_pushes'],'unique':r['unique'],'cost_ratio':r['length']/c['optimal_cost']})
 summary={name:{k:statistics.mean(r[k] for r in rows if r['method']==name) for k in ['pops','queue_ops','unique']} for name in ['reported','constant_equal_mean']};dump(a.output,{'scope':'Development/validation-only explanatory ablation, no final tuning/API calls. Constant confidence per query preserves sum(delta*confidence), separating placement of confidence from overall inflation amplitude. No calibrated probability interpretation claimed.','summary':summary,'runs':rows});print(summary)
if __name__=='__main__':main()
