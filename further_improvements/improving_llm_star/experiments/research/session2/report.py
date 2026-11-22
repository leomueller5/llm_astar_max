"""Generate final tables, paired clustered intervals and exportable plots offline."""
import sys,os,json,gzip,csv,statistics,math
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze import aggregate
BASE=Path(__file__).resolve().parents[2]/'results/research_session2'
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[4]/'.venv/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(path):
 with gzip.open(path,'rt') as f:return json.load(f)


def main():
 lines=['# Research session 2 — measured results','',
 'Policies frozen in commit `87c3310` before new test generation. Primary runtime policy: `witness_only`. Its gains are geometric; it does not use LLM guidance. All runs offline. Fresh final timing stages ran sequentially.','']
 results={};csvrows=[];fig,axes=plt.subplots(1,2,figsize=(13,5))
 for ax,cohort in zip(axes,['fresh_core','opened_cached_confirmation']):
  data=load(BASE/cohort/'results.json.gz');solvable=sum(r['variant']=='indexed_astar' and r['repeat']==0 and r['valid'] for r in data['runs']);stats=aggregate(data);llm=aggregate(data,control='witness_only');results[cohort]={'vs_matched_wa2':stats,'vs_witness_only':llm}
  lines+=['## '+cohort,'',
   'Fresh: 80 new maps /640 deterministic fixture cases (helpful fixture is oracle-derived, not real LLM). Opened confirmation: 600 cached observations /20 maps already inspected in Session 1; not a new independent holdout. Mean times are arithmetic means of within-case repetition medians.','',
   '| Variant | Mean ms | Median ms | Distinct states | Heap pops | GM cost / optimum | Valid / solvable | Exact certs | LLM routes used |',
   '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for m,s in stats.items():
   fmt=lambda v:'NA' if v is None else f'{v:.5f}'
   lines.append(f"| {m} | {s['mean_case_median_ms']:.4f} | {s['median_case_median_ms']:.4f} | {s['unique']:.2f} | {s['operations']:.2f} | {fmt(s['gm_cost_ratio'])} | {s['successes']}/{solvable} | {s['exact_certificates']} | {s['llm_accepted']} |")
   csvrows.append([cohort,m,s['mean_case_median_ms'],s['median_case_median_ms'],s['unique'],s['operations'],s['gm_cost_ratio'],s['successes'],s['exact_certificates'],s['llm_accepted']])
  lines+=['','Mean-time ratio / matched WA2, 95% whole-map bootstrap intervals (2,000 resamples):','']
  for m in ['old_cf','lean_cf','witness_only','witness_cf','witness_chain','witness_frontier']:
   s=stats[m];ci=s['ratio_of_mean_times_ci95'];lines.append(f"- {m}: {s['ratio_of_mean_times']:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]; paired GM ratio {s['gm_paired_time_ratio']:.4f}.")
  lines+=['','LLM incremental runtime / identical witness-only geometry:','']
  for m in ['witness_cf','witness_chain','witness_frontier']:
   s=llm[m];ci=s['ratio_of_mean_times_ci95'];lines.append(f"- {m}: {s['ratio_of_mean_times']:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]; more-cost cases {s['longer_than_control']}; more-distinct cases {s['more_unique_than_control']}.")
  first={}
  for r in data['runs']:
   if r['repeat']==0:first[r['case_id'],r['variant']]=r
  details={}
  for m,s in stats.items():
   rr=[r for (c,v),r in first.items() if v==m]
   details[m]={'exception_cases':sum(bool(r.get('error')) for r in rr),'fallback_fraction':statistics.mean(r['operation']>0 for r in rr),
     'accepted_sources':{key:sum(r.get('accepted_source')==key for r in rr) for key in ['direct','wall_witness','waypoint_dag']},
     'mean_preprocessing_ms':data['summary'][m]['mean_preprocessing_ms'],'mean_search_ms':data['summary'][m]['mean_search_ms'],
     'max_cost_ratio':s['max_cost_ratio'],'p95_cost_ratio':s['p95_cost_ratio']}
  lines += ['', '| Variant | p95 cost ratio | Max cost ratio | Longer than original | More distinct than original |', '|---|---:|---:|---:|---:|']
  for m in stats:
   rr=[r for (c,v),r in first.items() if v==m]
   longer=sum(r['valid'] and first[r['case_id'],'original_indexed']['valid'] and r['length']>first[r['case_id'],'original_indexed']['length']+1e-8 for r in rr)
   more=sum(r['unique']>first[r['case_id'],'original_indexed']['unique'] for r in rr)
   details[m]['longer_than_original']=longer;details[m]['more_unique_than_original']=more
   lines.append(f"| {m} | {stats[m]['p95_cost_ratio']:.5f} | {stats[m]['max_cost_ratio']:.5f} | {longer} | {more} |")
  results[cohort]['details']=details
  lines+=['','Per-family mean case-median ms (equal case weighting within family):','',
   '| Family | WA2 | Witness only | Exact LLM | Frontier LLM |','|---|---:|---:|---:|---:|']
  for family in sorted(stats['witness_only']['family_mean_ms']):
   vals=[stats[m]['family_mean_ms'][family] for m in ['scheduled_wa2','witness_only','witness_cf','witness_frontier']]
   lines.append('| '+family+' | '+' | '.join(f'{v:.4f}' for v in vals)+' |')
  lines+=['', 'The frozen-original soft-guidance algorithm has no comparable route-acceptance counter; its zero in that column means not applicable. Frozen-original exceptions on unreachable cases are reported separately: '+str(details['original_indexed']['exception_cases'])+'. New methods must match A* reachability; see independent verification.',
   '', 'Tail cost ratios and fallback/source breakdowns are saved in `report_statistics.json`; no claim of per-case runtime dominance. `original_indexed` retains frozen algorithm logic with the new geometry; it is not native-original timing.','']
  modes=['original_indexed','old_cf','indexed_cf','lean_cf','scheduled_wa2','witness_only','witness_cf','witness_frontier']
  ax.barh(modes,[stats[m]['mean_case_median_ms'] for m in modes],color=['#718da8']*5+['#24845e','#b88a34','#a86471']);ax.invert_yaxis();ax.set_xscale('log');ax.set_xlabel('Mean case-median elapsed time (ms, log scale)');ax.set_title(cohort)
 fig.tight_layout();fig.savefig(BASE/'runtime.png',dpi=180);fig.savefig(BASE/'runtime.pdf');plt.close(fig)
 native=load(BASE/'fresh_native/results.json.gz');lines+=['## Native public interface on fresh map-balanced sample','',native['scope'],'',
  '| Variant | Mean observed/censored ms | Median observed/censored ms | Maximum observed/censored ms | Timeout trials |','|---|---:|---:|---:|---:|']
 for m,s in native['summary'].items():lines.append(f"| {m} | {s['mean_case_median_ms']:.4f} | {s['median_case_median_ms']:.4f} | {s['max_case_median_ms']:.4f} | {s.get('timeout_trials',0)} |")
 lines += ['', 'Uniform 2-second per-trial timeout for ALL native interface methods. If any trials are censored, the observed mean is only a runtime LOWER BOUND, not the complete mean. This native safeguard was added after an interrupted first attempt; the full core evaluation has no such cutoff and is unchanged.', '']
 # Plot genuine geometric/LLM ablation against quality, and memory separately.
 fig,axes=plt.subplots(1,2,figsize=(12,4.5));s=results['opened_cached_confirmation']['vs_matched_wa2']
 modes=['original_indexed','old_cf','scheduled_wa2','witness_only','witness_cf','witness_chain','witness_frontier']
 axes[0].barh(modes,[100*(s[m]['gm_cost_ratio']-1) for m in modes],color=['#718da8']*3+['#24845e','#b88a34','#a86471','#a86471'])
 axes[0].invert_yaxis();axes[0].set_xlabel('GM path-cost inflation (%)');axes[0].set_title('Opened cached confirmation: path quality')
 prof=json.loads((BASE/'final_profiles/profile.json').read_text())['modes'];mm=['old_cf','indexed_cf','lean_cf','witness_only','scheduled_wa2']
 axes[1].bar(mm,[prof[m]['mean_peak_python_bytes']/1024 for m in mm]);axes[1].tick_params(axis='x',rotation=20);axes[1].set_ylabel('Mean peak Python allocations (KiB)');axes[1].set_title('24 fixed development cases; not RSS')
 fig.tight_layout();fig.savefig(BASE/'quality_memory.png',dpi=180);fig.savefig(BASE/'quality_memory.pdf');plt.close(fig)
 lines+=['','## Profiling and allocation scope','',
  '120 fixed development cases. Profiling is separate from uninstrumented timing. 24 fixed tracemalloc cases, GC collected before each; imports/native-library allocations excluded. Python peak allocations are not process RAM.','',
  '| Mode | Mean peak Python KiB | Mean geometry init ms | Mean prep ms | Mean search ms |','|---|---:|---:|---:|---:|']
 for m,r in prof.items():lines.append(f"| {m} | {r['mean_peak_python_bytes']/1024:.2f} | {r['mean_geometry_init_ms']:.4f} | {r['mean_preprocess_ms']:.4f} | {r['mean_search_ms']:.4f} |")
 lines+=['', 'The original cProfile places most cumulative cost in adjacency and collision; heap primitives are under 1% of that instrumented profile. Cumulative times overlap and cannot be summed. Exact compare U<=L is a scalar operation too small to isolate reliably; it remains inside timed preprocessing. Phase dictionaries, source configurations, allocation data and full profile listings are preserved.',
  '', '## Correctness and interpretation','']
 verify=BASE/'verification.json'
 if verify.exists():lines+=['```json',verify.read_text().strip(),'```','']
 lines+=['Witness certificates are optimal, otherwise fallback is weight-2 bounded. Frontier variants remain weight-2 bounded and can regress against the control. All probe, failed-preparation and fallback costs are charged. Unit-edge tests, continuous-piece tests, wall tests and heap pops are distinct counters.',
  '', 'The primary speed improvement is geometric, not an established LLM advantage. Oracle corner fixtures show best-case guidance potential; cached model outputs determine real-response evidence. Opened confirmation is never relabelled fresh test data. See session2/README.md and EXPERIMENT_LOG.md for rejected approaches, exact commands, frozen policy and limitations.']
 (BASE/'REPORT.md').write_text('\n'.join(lines)+'\n');(BASE/'report_statistics.json').write_text(json.dumps(results,indent=2)+'\n')
 with (BASE/'aggregate.csv').open('w') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['cohort','variant','mean_case_median_ms','median_case_median_ms','mean_distinct','mean_pops','gm_cost_ratio','successes','optimal_certificates','llm_routes_used']);w.writerows(csvrows)
 print('Reports and figures saved to',BASE)
if __name__=='__main__':main()
