"""Work, latency, family regressions and memory supplements; no search reruns."""
import json,gzip,statistics,math,argparse,os
from pathlib import Path
from collections import defaultdict
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/llmastar-matplotlib');os.environ.setdefault('XDG_CACHE_HOME','/private/tmp/llmastar-cache')


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;stats=json.loads((root/'final_analysis/statistics.json').read_text());out={};lines=['# Additional diagnostics','']
 for dataset in ['final_fresh','final_cached_validation']:
  with gzip.open(root/dataset/'results.json.gz','rt') as f:data=json.load(f)
  one={};time_groups=defaultdict(list)
  for r in data['runs']:
   time_groups[(r['mode'],r['case_id'])].append(r['seconds'])
   if r['repeat']==0:one.setdefault(r['mode'],{})[r['case_id']]=r
  medians={key:statistics.median(values) for key,values in time_groups.items()}
  s=stats[dataset]['summary'];latency={};paper={};worst={};usage={}
  for mode,ss in s.items():
   req=ss['mean_requests']
   latency[mode]={'hypothetical_ms_with_per_request_delay':{str(delay):ss['mean_ms']+req*delay for delay in [0,1,10,100,1000]},'break_even_delay_ms_vs_cut_none':ss['max_model_latency_break_even_ms_vs_cut_none'],'requests_per_observation':req,'scope':'Fixed-output what-if arithmetic only, NOT measured model inference; classical local_none requests are interface calls and should receive zero model delay.'}
   if mode in one and 'astar' in one:
    pairs=[(r,one['astar'][cid]) for cid,r in one[mode].items() if r['optimal_cost'] is not None and r['valid']]
    paper[mode]={'arithmetic_mean_heap_pop_ratio_to_astar':statistics.mean(r.get('total_heap_pops',r['operation'])/b['operation'] for r,b in pairs),'arithmetic_mean_global_g_entry_ratio_to_astar':statistics.mean(r.get('storage',0)/b['storage'] for r,b in pairs),'mean_cost_ratio_to_opt':statistics.mean(r['length']/r['optimal_cost'] for r,b in pairs),'scope':'Reachable valid cases only. Heap pops include local search. Global g-entry ratio is a state-count proxy, NOT full memory storage; consult tracemalloc.'}
   rr=list(one[mode].values());usage[mode]={'provider_invocations':sum(r.get('provider_requests',0) for r in rr),'with_any_seed':sum(r.get('seed_count',0)>0 for r in rr),'accepted_sources':dict(__import__('collections').Counter(str(r.get('accepted_source',r.get('candidate_source'))) for r in rr)),'warning_observations':sum(bool(r.get('warnings')) for r in rr),'scope':'A seed being inserted does not prove the returned path used it. Source labels refer to accepted incumbents only.'}
   if mode!='cut_none' and mode in one:
    pairs=[]
    for cid,r in one[mode].items():
     base=one['cut_none'][cid]
     # Main statistics use query medians; use these here too.
     t=medians[(mode,cid)]
     bt=medians[('cut_none',cid)]
     pairs.append({'case_id':cid,'family':r['family'],'extra_ms':1000*(t-bt),'time_ratio':t/bt,'cost':r['length'],'control_cost':base['length']})
    worst[mode]=sorted(pairs,key=lambda r:r['extra_ms'],reverse=True)[:3]
  out[dataset]={'latency':latency,'paper_style_metrics':paper,'usage':usage,'worst_absolute_regressions_vs_cut_none':worst}
  lines+=['## '+dataset,'','|Method|Mean pop ratio / A*|Mean global g-entry ratio / A*|Mean cost / optimal|','|---|---:|---:|---:|']
  for m in ['weighted','witness','cut_none','local_none','local_raw','local_portfolio','cut_oracle']:
   if m in paper:
    v=paper[m];lines.append(f"|{m}|{v['arithmetic_mean_heap_pop_ratio_to_astar']:.4f}|{v['arithmetic_mean_global_g_entry_ratio_to_astar']:.4f}|{v['mean_cost_ratio_to_opt']:.5f}|")
  lines+=['','The g-entry ratio excludes local transient structures and DP/cache bytes; it is not a claim of byte-memory reduction.','']
 audit=json.loads((root/'final_audit/audit.json').read_text());memory={}
 for mode in sorted({r['mode'] for r in audit['instrumented_runs']}):
  rr=[r for r in audit['instrumented_runs'] if r['mode']==mode];memory[mode]={'mean_peak_traced_MiB':statistics.mean(r['peak_python_bytes'] for r in rr)/2**20,'max_peak_traced_MiB':max(r['peak_python_bytes'] for r in rr)/2**20,'mean_heap_push_calls':statistics.mean(r['push_calls'] for r in rr),'mean_heap_pop_calls':statistics.mean(r['pop_calls'] for r in rr),'mean_heapify_calls':statistics.mean(r['heapify_calls'] for r in rr),'mean_heapify_items':statistics.mean(r['heapify_items'] for r in rr)}
 out['instrumented_memory_heap']=memory;lines+=['## Separate instrumented memory/heap pass','','Ten predetermined fresh query0 cases: open, random walls, rooms, tree mazes and bottlenecks at both sizes. Traced allocations include Python objects and any native buffers exposed to tracemalloc; this is not total native memory or process RSS. No instrumented times enter native runtime tables.','','|Method|Mean peak MiB|Max peak MiB|Heap pushes|Heap pops|Heapify items|','|---|---:|---:|---:|---:|---:|']
 for mode,s in memory.items():lines.append(f"|{mode}|{s['mean_peak_traced_MiB']:.3f}|{s['max_peak_traced_MiB']:.3f}|{s['mean_heap_push_calls']:.1f}|{s['mean_heap_pop_calls']:.1f}|{s['mean_heapify_items']:.1f}|")
 (root/'final_analysis/diagnostics.json').write_text(json.dumps(out,indent=2)+'\n');(root/'final_analysis/SUPPLEMENT.md').write_text('\n'.join(lines)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fam=stats['final_fresh']['family'];names=list(fam['cut_none']);fig,ax=plt.subplots(figsize=(11,4.5));x=range(len(names));width=.36
 ax.bar([i-width/2 for i in x],[fam['cut_none'][n]['mean_ms']/fam['weighted'][n]['mean_ms'] for n in names],width,label='Cut / Weighted A* (geometry contribution)')
 ax.bar([i+width/2 for i in x],[fam['local_raw'][n]['mean_ms']/fam['cut_none'][n]['mean_ms'] for n in names],width,label='Local imperfect-oracle / Cut (guidance contribution)')
 ax.set_xticks(list(x),names,rotation=35,ha='right');ax.set_yscale('log');ax.axhline(1,color='black',lw=.8);ax.set_ylabel('Mean time ratio (below 1 is faster)');ax.set_title('Fresh maps: benefits AND regressions by family; synthetic advice, not live LLM');ax.legend(fontsize=8);fig.tight_layout()
 for ext in ['png','pdf']:fig.savefig(root/'final_analysis'/f'families.{ext}',dpi=180)
 print(json.dumps(memory,indent=2))
if __name__=='__main__':main()
