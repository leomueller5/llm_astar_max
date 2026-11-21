"""Frozen held-out residual accuracy and effective trust; no fitting or model calls."""
import argparse,json,math,statistics,collections
from pathlib import Path
import numpy as np
from common import read_cases,dump,RESULTS
from native_benchmark import ALPHA,TEXT_ALPHA,load_costs
from prompts_spatial import decode
from llmastar.research.spatial_guidance import RegionField
from llmastar.research.strategic.cuts import CutPotential

def stats(rr):
 truth=np.array([r['truth'] for r in rr]);pred=np.array([r['predicted'] for r in rr]);err=pred-truth
 return {'samples':len(rr),'mae':float(np.mean(abs(err))),'rmse':float(np.sqrt(np.mean(err**2))),'bias':float(np.mean(err)),'overestimate_fraction':float(np.mean(err>1e-7)),'underestimate_fraction':float(np.mean(err < -1e-7)),'pearson':float(np.corrcoef(truth,pred)[0,1]) if np.std(truth)>0 and np.std(pred)>0 else None}

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--traces',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};refs=read_cases(RESULTS/'heldout_reference_samples.json.gz')['runs'];cost=load_costs(RESULTS/'heldout_cost/responses.json.gz');icl=load_costs(RESULTS/'heldout_icl/responses.json.gz');rows=[];fields={};unreachable=0
 for ref in refs:
  cid=ref['case_id'];q=cases[cid]['query'];fields[cid],_=decode(q,cost[cid,'image']['response']['choices'][0]['message']['content'],4,'cost')
  for kind,source,alpha in [('image',cost,ALPHA),('text',cost,TEXT_ALPHA),('icl',icl,ALPHA)]:
   f,_=decode(q,source[cid,'structured' if kind=='text' else 'image']['response']['choices'][0]['message']['content'],4,'cost')
   for r in ref['samples']:
    if r['remaining_cost'] is None or r['geometric_lower_bound'] is None:unreachable+=1;continue
    h=r['geometric_lower_bound'];delta,priority,confidence=f.values.get(r['region_id'],(0.,.5,0.));true=r['remaining_cost'];common={'case_id':cid,'family':ref['family'],'region_id':r['region_id'],'truth':true,'confidence':confidence,'geometric_lower_bound':h,'raw_delta':delta,'true_delta':true-h}
    for variant,pred in [('geometric',h),('uniform105',1.05*h),('raw',h+confidence*delta),('calibrated',h+alpha*confidence*delta),('clipped105',h+min(.05*h,alpha*confidence*delta))]:rows.append(dict(common,representation=kind,variant=variant,predicted=pred))
 summary={kind:{v:stats([r for r in rows if r['representation']==kind and r['variant']==v]) for v in ['geometric','uniform105','raw','calibrated','clipped105']} for kind in ['image','text','icl']};confusion={}
 for kind in ['image','text','icl']:
  rr=[r for r in rows if r['representation']==kind and r['variant']=='raw'];delta=np.array([r['raw_delta'] for r in rr]);lower=np.array([r['geometric_lower_bound'] for r in rr]);truth=np.array([r['true_delta'] for r in rr]);zero=[r for r in rr if abs(r['true_delta'])<1e-7]
  confusion[kind]={'delta_correlation_with_lower_bound':float(np.corrcoef(delta,lower)[0,1]) if np.std(delta)>0 else None,'delta_correlation_with_true_extra_cost':float(np.corrcoef(delta,truth)[0,1]) if np.std(delta)>0 and np.std(truth)>0 else None,'zero_true_residual_samples':len(zero),'false_positive_delta_fraction_when_true_zero':statistics.mean(r['raw_delta']>1e-7 for r in zero) if zero else None,'mean_confidence_when_wrong_by_more_than10':statistics.mean(r['confidence'] for r in rr if abs(r['raw_delta']-r['true_delta'])>10) if any(abs(r['raw_delta']-r['true_delta'])>10 for r in rr) else None}
 trace_rows=[]
 for record in read_cases(a.traces):
  if record['method']!='rh_image105':continue
  cid=record['case_id'];q=cases[cid]['query'];f=fields[cid];h=CutPotential(q,tuple(q['goal'])).value;effective=[];capped=zero=0;regions=[]
  for label in record['trace']:
   node=tuple(label['node']);d,priority,c=f.value(node);hh=h(node);base=ALPHA*c;cap=.05*hh
   a_eff=min(base,cap/d) if d>0 else 0.;effective.append(a_eff);capped+=d>0 and base*d>=cap-1e-12;zero+=d<=0 or c<=0;regions.append(f.identifier(node))
  runs=[]
  for region in regions:
   if runs and runs[-1][0]==region:runs[-1][1]+=1
   else:runs.append([region,1])
  trace_rows.append({'case_id':cid,'expansions':len(effective),'mean_effective_alpha':statistics.mean(effective) if effective else None,'capped_fraction':capped/len(effective) if effective else None,'zero_advice_fraction':zero/len(effective) if effective else None,'region_visits':runs,'guidance_rebuilds':0,'online_alpha_adjustments':0})
 dump(a.output,{'scope':'Offline exact held-out remaining costs are targets only. Raw delta is extra distance beyond the geometric lower bound; confidence-weighted. No coefficient is fitted on these data. Coarse representative accuracy does not imply admissibility at other cells. Unreachable samples excluded explicitly. Repeated region visits are not independently generated advice.','prediction_summary':summary,'residual_confusion':confusion,'unreachable_records_counted_per_representation':unreachable,'samples':rows,'trace_analysis':trace_rows})
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
