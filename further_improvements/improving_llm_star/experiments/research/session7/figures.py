"""Standalone scientific figures from completed artifacts, no model calls."""
import argparse,os,tempfile,json,statistics,math
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'llm-astar-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from common import read_cases,RESULTS
LABELS={'original':'Original LLM-A*','robust_original':'Original + engine fixes','matched_zero':'Matched A*','matched_uniform105':'Matched WA*1.05','optimized_uniform105':'Optimized WA*1.05','vm_geo105':'Geometric VM1.05','vm_hybrid2':'Frozen hybrid VM2 (compatible)','rh_image105':'LLM-RH* image1.05','rh_text105':'LLM-RH* text1.05','rh_icl105':'LLM-RH* few-shot1.05','rh_shuffled105':'RH shuffled regions','rh_scalar105':'RH scalar prediction','rh_geometry105':'Geometry-only residual'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--analysis',required=True);p.add_argument('--predictions',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);data=json.loads(Path(a.analysis).read_text());pred=read_cases(a.predictions);plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 def save(fig,name):
  fig.savefig(out/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
 methods=['original','robust_original','matched_zero','matched_uniform105','vm_geo105','vm_hybrid2','rh_image105','rh_text105','rh_icl105']
 for stratum in ['primary','large']:
  s=data[stratum]['summary'];fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
  for ax,key,title,scale in [(axes[0],'mean_ms','Cached-guidance local elapsed (ms)','log'),(axes[1],'mean_queue_operations','Actual heap pushes + pops','log'),(axes[2],'gm_cost_ratio','Geometric mean path cost / optimum','linear')]:
   vals=[np.nan if m=='original' and key!='mean_ms' else s[m][key] for m in methods];ax.barh(range(len(methods)),vals,color=['#d78543' if m=='rh_image105' else '#607d9a' for m in methods]);ax.set(yticks=range(len(methods)),yticklabels=[LABELS[m] for m in methods],title=title,xscale=scale);ax.grid(axis='x',alpha=.2);ax.invert_yaxis() if ax is axes[0] else None
   if key!='mean_ms':ax.text(.02,0,'censored original: completed-only mean omitted',transform=ax.get_yaxis_transform(),va='center',fontsize=7,color='#666666')
   if key=='gm_cost_ratio':ax.set_xlim(.995,max(v for v in vals if np.isfinite(v))*1.01)
  fig.suptitle(f'{stratum}: frozen comparison; completed-work coverage in RESULTS.md; capped timing if any timeouts',y=1.02);fig.tight_layout();save(fig,'comparison_'+stratum)
 controls=['matched_zero','matched_uniform105','optimized_uniform105','vm_geo105','rh_shuffled105','rh_scalar105','rh_geometry105','rh_text105','rh_icl105']
 fig,axes=plt.subplots(1,2,figsize=(12,5.2),sharey=True)
 for ax,metric,title in [(axes[0],'queue_operations','Primary LLM-RH* / control: total queue work'),(axes[1],'seconds','Primary LLM-RH* / control: local elapsed')]:
  rr=data['primary']['paired_primary_over_control'];mid=[];lo=[];hi=[]
  for m in controls:
   v=rr[m][metric];mid.append(v['ratio']);lo.append(v['ratio']-v['ci95'][0]);hi.append(v['ci95'][1]-v['ratio'])
  ax.errorbar(mid,range(len(controls)),xerr=[lo,hi],fmt='o',color='#315b7b',capsize=3);ax.axvline(1,color='#b24b42',ls='--');ax.set(yticks=range(len(controls)),yticklabels=[LABELS.get(m,m) for m in controls],title=title);ax.grid(axis='x',alpha=.2)
 axes[0].invert_yaxis();fig.suptitle('Map-cluster paired bootstrap95% nominal intervals; <1 favors LLM-RH*',y=1.01);fig.tight_layout();save(fig,'paired_intervals')
 families=sorted(k[7:] for k in data if k.startswith('family_'));fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(len(families));width=.27
 for offset,control,color in [(-1,'matched_uniform105','#607d9a'),(0,'vm_geo105','#73a08a'),(1,'rh_shuffled105','#c98a62')]:
  ratios=[data['family_'+f]['paired_primary_over_control'][control]['queue_operations']['ratio'] for f in families];ax.bar(x+offset*width,ratios,width,label=LABELS.get(control,control),color=color)
 ax.axhline(1,color='black',lw=.8);ax.set(xticks=x,xticklabels=[f.replace('_','\n') for f in families],ylabel='LLM-RH* / control queue work',title='Per-family tradeoffs, all fresh sizes (no favorable-family selection)');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2);fig.tight_layout();save(fig,'families')
 fig,ax=plt.subplots(figsize=(8,4));variants=['geometric','uniform105','raw','calibrated','clipped105'];x=np.arange(len(variants));width=.25
 for i,(kind,label,color) in enumerate([('text','Text','#607d9a'),('image','Image','#c98a62'),('icl','Image + fixed examples','#73a08a')]):ax.bar(x+(i-1)*width,[pred['prediction_summary'][kind][v]['mae'] for v in variants],width,label=label,color=color)
 ax.set(xticks=x,xticklabels=['Geometric h','Uniform1.05 h','Raw model','Calibrated model','Clipped1.05 model'],ylabel='Remaining-cost MAE at free region samples',title='Actual prediction accuracy; exact references are offline targets only');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();save(fig,'prediction_accuracy')
 oracle=read_cases(RESULTS/'oracle_pilot.json.gz')['summary'];resolution=read_cases(RESULTS/'oracle_resolution.json.gz')['summary'];fig,axes=plt.subplots(1,2,figsize=(11,4.4))
 labels=['No residual','4x4 exact samples','8x8 exact samples','16x16 exact samples','Exact every node'];vals=[oracle['cut_envelope_detour_none']['mean_pops']]+[resolution[f'detour{k}_envelope']['pops'] for k in [4,8,16]]+[oracle['cut_envelope_detour_oracle_fine']['mean_pops']]
 axes[0].bar(range(len(vals)),vals,color=['#607d9a']+['#73a08a']*4);axes[0].set(xticks=range(len(vals)),xticklabels=[x.replace(' ','\n') for x in labels],ylabel='Mean heap pops',title='Remaining-cost ceiling (base weight1)' )
 labels=['No corridor','Oracle8x8','Oracle16x16','Oracle cell priorities'];vals=[oracle['cut_envelope_priority_none']['mean_pops'],resolution['corridor8_envelope']['pops'],resolution['corridor16_envelope']['pops'],oracle['cut_envelope_priority_oracle_fine']['mean_pops']];axes[1].bar(range(len(vals)),vals,color=['#607d9a']+['#73a08a']*3);axes[1].set(xticks=range(len(vals)),xticklabels=[x.replace(' ','\n') for x in labels],title='Route-priority ceiling (base weight1.5)');fig.suptitle('Development-only oracle diagnostics; bound2 full-key envelope, not final primary; exact-reference generation excluded and not available online',fontsize=9,y=1.02);fig.tight_layout();save(fig,'oracle_resolution')
 print(out)
if __name__=='__main__':main()
