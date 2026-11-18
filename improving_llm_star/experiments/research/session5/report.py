"""Read-only research summaries/paired map intervals; never invokes the API."""
import os,json,gzip,math,statistics,argparse
from pathlib import Path
import numpy as np
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/llmastar-matplotlib');os.environ.setdefault('XDG_CACHE_HOME','/private/tmp/llmastar-cache')


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;output=root/'analysis';output.mkdir(exist_ok=True)
 data=json.load(gzip.open(root/'repair_replay_controls_v2/results.json.gz','rt'));rows=[r for r in data['runs'] if r['rep']==0];by={}
 for r in rows:by.setdefault(r['mode'],{})[r['case_id']]=r
 pairs={}
 for method in by:
  for control in ['original','no_guidance','egor_ungated','restart_gated','shuffle_gated','random_gated']:
   if method==control:continue
   ids=sorted(set(by[method])&set(by[control]));xy=np.array([[by[method][i]['operation'],by[control][i]['operation']] for i in ids]);rng=np.random.default_rng(20261118);sample=xy[rng.integers(0,len(ids),size=(4000,len(ids)))].sum(axis=1);ratios=sample[:,0]/sample[:,1]
   pairs[method+'/'+control]={'ratio_mean_pops':float(xy[:,0].sum()/xy[:,1].sum()),'ci95_development_map_bootstrap':list(map(float,np.quantile(ratios,[.025,.975]))),'maps':len(ids),'scope':'Exploratory development only; no multiplicity adjustment; no held-out confirmation.'}
 ledger=json.loads((root/'api_export.json').read_text());requests={r['id']:r for r in ledger['requests']};live=json.load(gzip.open(root/'dynamic_pilot/results.json.gz','rt'))['runs'];timing=[]
 for r in live:
  initial=requests[r['initial_request_id']];successful=[x for x in r['requests'] if x.get('request_id')];additional=[requests[x['request_id']] for x in successful]
  timing.append({'case_id':r['case_id'],'initial_api_seconds':initial['latency_seconds'],'correction_api_seconds':sum(x['latency_seconds'] for x in additional),'measured_online_loop_seconds':r['seconds'],'derived_initial_plus_online_seconds':initial['latency_seconds']+r['seconds'],'known_cost_usd':initial['estimated_cost_usd']+sum(x['estimated_cost_usd'] or 0 for x in additional),'initial_plus_correction_calls':1+len(additional)})
 prompt_comparison={}
 for folder in ['pilot_search','validation_search']:
  summary=json.loads((root/folder/'summary.json').read_text())
  prompt_comparison[folder]={k:v for k,v in summary.items() if k.endswith('/original') or k.endswith('/none') or k.endswith('/lineage_full')}
 result={'budget':ledger['summary'],'model':ledger['pricing']['model'],'repair_summary':data['summary'],'pairs':pairs,'prompt_comparison':prompt_comparison,'api_timing':timing,'latency_summary':{'mean_initial_api_seconds':statistics.mean(r['initial_api_seconds'] for r in timing),'mean_correction_api_seconds_per_query':statistics.mean(r['correction_api_seconds'] for r in timing),'mean_actual_online_loop_seconds':statistics.mean(r['measured_online_loop_seconds'] for r in timing),'mean_derived_initial_plus_online_seconds':statistics.mean(r['derived_initial_plus_online_seconds'] for r in timing)},'failed_online_self_review':'8 transport failures; NOT a completed LLM control. No efficacy comparison uses those unchanged outputs.'}
 (output/'statistics.json').write_text(json.dumps(result,indent=2)+'\n')
 lines=['# Session5 measured tables','','Exact model: `'+result['model']+'`. All algorithm comparisons reuse the same real response; repeated timing runs are not independent maps. These are development/validation results, not fresh held-out LLM evidence.','','|Direct original variant|Mean heap pops|Mean distinct states|Cost/opt GM|Offline compute ms|','|---|---:|---:|---:|---:|']
 for method,s in data['summary'].items():lines.append(f"|{method}|{s['mean_pops']:.1f}|{s['mean_unique']:.1f}|{s['gm_cost_ratio']:.5f}|{s['mean_ms']:.3f}|")
 lines+=['','|Paired development pop ratio|Estimate|95% map-bootstrap interval|','|---|---:|---|']
 for key in ['egor_gated/original','egor_gated/no_guidance','egor_gated/egor_ungated','egor_gated/restart_gated','egor_gated/shuffle_gated','egor_gated/random_gated']:
  s=pairs[key];lines.append(f"|{key}|{s['ratio_mean_pops']:.4f}|{s['ci95_development_map_bootstrap']}|")
 lines+=['','All intervals exploratory/unadjusted. API latency excluded from offline compute times.','', 'API usage: '+json.dumps(result['budget']), '', 'Latency summary seconds: '+json.dumps(result['latency_summary'])]
 (output/'TABLES.md').write_text('\n'.join(lines)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 methods=['original','no_guidance','egor_gated','egor_ungated','restart_gated','shuffle_gated','random_gated'];s=data['summary'];fig,axes=plt.subplots(1,2,figsize=(12,4.5));x=np.arange(len(methods))
 axes[0].barh(x,[s[m]['mean_pops'] for m in methods]);axes[0].set_yticks(x,methods);axes[0].invert_yaxis();axes[0].set_xlabel('Mean actual heap pops (development,10 maps)')
 for m in methods:axes[1].scatter(s[m]['mean_pops'],s[m]['gm_cost_ratio'],label=m)
 axes[1].legend(loc='upper left',bbox_to_anchor=(1.01,1),fontsize=7);axes[1].set_xlabel('Mean heap pops');axes[1].set_ylabel('Geometric mean cost / optimal');axes[1].axhline(1,color='gray',lw=.7);axes[1].margins(.15)
 fig.suptitle('Real model corrections, exploratory only: no held-out or no-guidance win established',fontsize=10);fig.tight_layout()
 for ext in ['png','pdf']:fig.savefig(output/f'repair_tradeoffs.{ext}',dpi=180)
 plt.close(fig)
 print(json.dumps({'budget':result['budget'],'pairs':{k:pairs[k] for k in ['egor_gated/original','egor_gated/no_guidance']},'latency':result['latency_summary']},indent=2))
if __name__=='__main__':main()
