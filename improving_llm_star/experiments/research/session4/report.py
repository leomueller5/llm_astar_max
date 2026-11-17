"""Map-cluster paired estimates and plots from immutable evaluation artifacts."""
import json,gzip,math,statistics,argparse,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/llmastar-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME','/private/tmp/llmastar-cache')
from pathlib import Path
from collections import defaultdict
import numpy as np


def summarize(data):
 groups=defaultdict(list)
 for r in data['runs']:groups[r['mode']].append(r)
 case={};summary={}
 for mode,rows in groups.items():
  by=defaultdict(list)
  for r in rows:by[r['case_id']].append(r)
  case[mode]={}
  for cid,rr in by.items():
   entry=dict(rr[0])
   for key in rr[0]:
    if key.endswith('seconds') and isinstance(rr[0][key],(int,float)):
     entry[key]=statistics.median(x.get(key,0) for x in rr)
   case[mode][cid]=entry
  one=list(case[mode].values());reachable=[r for r in one if r.get('reachable',r['optimal_cost'] is not None)];valid=[r for r in reachable if r['valid']]
  times=[r['seconds']*1000 for r in one];ratios=[r['length']/r['optimal_cost'] for r in valid if r['optimal_cost']]
  summary[mode]={'mean_ms':statistics.mean(times),'median_ms':statistics.median(times),'p90_ms':float(np.percentile(times,90)),'max_ms':max(times),'valid_reachable':len(valid),'reachable':len(reachable),'correct_unreachable':sum(not r['valid'] and not r.get('error') for r in one if r['optimal_cost'] is None),'unreachable':sum(r['optimal_cost'] is None for r in one),'gm_cost_ratio':math.exp(statistics.mean(math.log(x) for x in ratios)) if ratios else None,'max_cost_ratio':max(ratios,default=None),'mean_unique_total':statistics.mean(r.get('unique_total',r.get('unique',0)) for r in one),'mean_grid_unique':statistics.mean(r.get('unique',0) for r in one),'mean_total_pops':statistics.mean(r.get('total_heap_pops',r.get('operation',0)) for r in one),'mean_provider_expanded':statistics.mean(r.get('provider_expanded',0) for r in one),'mean_requests':statistics.mean(r.get('provider_requests',0) for r in one),'mean_preprocess_ms':statistics.mean(r.get('preprocess_seconds',0)*1000 for r in one),'mean_search_ms':statistics.mean(r.get('search_seconds',0)*1000 for r in one),'mean_candidate_ms':statistics.mean(r.get('candidate_seconds',0)*1000 for r in one),'mean_cut_ms':statistics.mean(r.get('cut_preprocess_seconds',0)*1000 for r in one),'mean_lazy_ms':statistics.mean(r.get('lazy_heuristic_seconds',0)*1000 for r in one),'timeouts':sum(r.get('error')=='timeout' for r in rows),'errors':sum(bool(r.get('error')) for r in rows),'zero_grid_fraction':statistics.mean(r.get('unique',0)==0 for r in one),'max_model_latency_break_even_ms_vs_cut_none':None}
 # Missing timeout counters must not be reported as artificial zeros.
 for mode,rows in groups.items():
  if any(r.get('error') for r in rows):
   for key in ['mean_unique_total','mean_grid_unique','mean_total_pops','mean_provider_expanded']:summary[mode][key]=None
 if 'cut_none' in case:
  for mode in summary:
   ids=set(case[mode])&set(case['cut_none']);saved=sum(case['cut_none'][i]['seconds']-case[mode][i]['seconds'] for i in ids);requests=sum(case[mode][i].get('provider_requests',0) for i in ids)
   if requests:summary[mode]['max_model_latency_break_even_ms_vs_cut_none']=1000*saved/requests
 pairs={}
 controls=['weighted','witness','cut_none','local_none','local_raw','original_matched']
 for mode in summary:
  for control in controls:
   if control not in case or mode==control:continue
   bymap=defaultdict(list)
   for cid,r in case[mode].items():
    b=case[control].get(cid)
    if b:bymap[r['map_id']].append((r['seconds'],b['seconds']))
   arrays=np.array([[sum(x[0] for x in rr),sum(x[1] for x in rr)] for rr in bymap.values()])
   rng=np.random.default_rng(2026111740);indices=rng.integers(0,len(arrays),size=(4000,len(arrays)));resamples=arrays[indices].sum(axis=1);ratios=resamples[:,0]/resamples[:,1]
   key=mode+'/'+control;pairs[key]={'ratio_mean_times':float(arrays[:,0].sum()/arrays[:,1].sum()),'ci95_map_bootstrap':list(map(float,np.quantile(ratios,[.025,.975]))),'maps':len(arrays),'cases':sum(map(len,bymap.values())),'scope':'Exploratory unadjusted map-cluster percentile intervals; repeated trials reduced to query medians first. Ratios involving timeouts are censored, not complete runtime ratios.'}
 family={}
 for mode in case:
  by=defaultdict(list)
  for r in case[mode].values():by[r['family']].append(r)
  family[mode]={f:{'mean_ms':statistics.mean(r['seconds'] for r in rr)*1000,'mean_unique':statistics.mean(r.get('unique_total',r.get('unique',0)) for r in rr),'valid':sum(r['valid'] for r in rr),'cases':len(rr),'gm_cost_ratio':math.exp(statistics.mean(math.log(r['length']/r['optimal_cost']) for r in rr if r['valid'])) if any(r['valid'] for r in rr) else None} for f,rr in by.items()}
 return {'summary':summary,'pairs':pairs,'family':family},case


def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);allstats={};cases={}
 for folder in a.inputs:
  with gzip.open(folder/'results.json.gz','rt') as f:d=json.load(f)
  allstats[folder.name],cases[folder.name]=summarize(d)
 (a.output/'statistics.json').write_text(json.dumps(allstats,indent=2)+'\n')
 lines=['# Frozen Session 4 evaluation tables','', 'Times are means of per-query medians; every query has randomized repeated trials and two fixed excluded warmups. All values include cold map setup and all method processing. Model generation and network latency are unavailable/excluded; actual API calls and costs are zero. Synthetic/oracle results are not real LLM performance.','']
 for dataset,stats in allstats.items():
  lines+=['## '+dataset,'','|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|','|---|---:|---:|---:|---:|---:|---:|---:|']
  for m,s in stats['summary'].items():lines.append(f"|{m}|{s['mean_ms']:.4f}|{s['median_ms']:.4f}|{s['mean_unique_total'] if s['mean_unique_total'] is not None else 'missing/censored'}|{s['mean_total_pops'] if s['mean_total_pops'] is not None else 'missing/censored'}|{s['gm_cost_ratio'] or 0:.5f}|{s['valid_reachable']}/{s['reachable']}|{s['timeouts']}|")
  lines+=['','Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.','', '|Paired time ratio|Estimate|95% map CI|','|---|---:|---|']
  for key,v in stats['pairs'].items():
   if key in ['cut_none/weighted','cut_none/witness','cut_raw/cut_none','local_raw/cut_none','local_raw/local_none','local_portfolio/local_none','local_portfolio/local_raw','cut_oracle/cut_none','cut_random/cut_none','cut_wrong/cut_none','cut_dynamic/cut_none','local_none/cut_none','local_random/local_raw','local_wrong/local_raw','local_shuffled/local_raw','local_norepair/local_raw','local_noshortcut/local_raw']:
    lines.append(f"|{key}|{v['ratio_mean_times']:.4f}|[{v['ci95_map_bootstrap'][0]:.4f}, {v['ci95_map_bootstrap'][1]:.4f}]|")
  lines+=['','Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.','']
 (a.output/'TABLES.md').write_text('\n'.join(lines)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 for dataset,stats in allstats.items():
  selected=[m for m in ['weighted','witness','cut_none','local_none','cut_raw','local_raw','local_portfolio','cut_oracle'] if m in stats['summary']]
  fig,axes=plt.subplots(1,2,figsize=(13,4.2));s=stats['summary'];x=np.arange(len(selected))
  axes[0].barh(x,[s[m]['mean_ms'] for m in selected],color=['#6a8caf' if m in ['weighted','witness','cut_none','local_none'] else '#d99a53' for m in selected]);axes[0].set_yticks(x,selected);axes[0].invert_yaxis();axes[0].set_xlabel('Mean of query-median end-to-end time [ms]');axes[0].set_title(dataset)
  for m in selected:axes[1].scatter(s[m]['mean_ms'],s[m]['gm_cost_ratio'],s=40,label=m)
  axes[1].legend(loc='upper left',bbox_to_anchor=(1.01,1),fontsize=7);axes[1].margins(x=.12,y=.15)
  axes[1].set_xlabel('End-to-end time [ms]');axes[1].set_ylabel('Geometric mean path cost / optimum');axes[1].axhline(1,color='gray',lw=.8);fig.suptitle('Synthetic/oracle guidance is explicitly unavailable information; no paid API calls',fontsize=10);fig.tight_layout()
  for ext in ['png','pdf']:fig.savefig(a.output/f'{dataset}_comparison.{ext}',dpi=180)
  plt.close(fig)
 print('Wrote tables, statistics and plots for:',', '.join(allstats))
if __name__=='__main__':main()
