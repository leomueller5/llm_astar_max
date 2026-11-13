"""Regenerate aggregate tables, clustered intervals and standalone figures offline."""
import csv,gzip,json,math,random,statistics,os

from collections import defaultdict
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR",str(Path(__file__).resolve().parents[3]/".venv/matplotlib"))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parents[1]/'results/research'
MODES=['original','alpha05','current_adaptive','astar','wa2','direct_only','sieved_no_repair','sieved_no_cut','sieved_cert']

def interval(rows,control):
 by=defaultdict(dict)
 for r in rows:by[r['case_id']][r['variant']]=r
 clusters=defaultdict(list)
 for v in by.values():
  if control in v and 'sieved_cert' in v and v[control]['optimal_cost'] is not None:
   r=v['sieved_cert'];clusters[r['map_id']].append((r['unique'],v[control]['unique']))
 groups=list(clusters.values());rng=random.Random(20261113);ratios=[]
 for _ in range(2000):
  sample=[pair for _ in groups for pair in rng.choice(groups)]
  ratios.append(sum(x for x,y in sample)/sum(y for x,y in sample))
 ratios.sort();return [ratios[49],ratios[1949]]

def main():
 details={};lines=['# Held-out research results — 13 November 2026','',
 'Policy frozen before test; no paid API calls. Distinct expansions and raw heap pops have different definitions. Timings below use shared collision graphs; fresh-query timings follow separately.','']
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for ax,suite in zip(axes,['heldout_cached','heldout_synthetic']):
  with gzip.open(BASE/suite/'results.json.gz','rt') as f:data=json.load(f)
  rows=data['runs'];summ=data['summary'];details[suite]={'clustered_mean_unique_ratio_ci95':{c:interval(rows,c) for c in ['original','wa2','direct_only']}}
  lines += ['## '+suite,'','All-case expansion means include correctly exhausted disconnected maps. Path ratios use solvable cases only.','',
   '| Variant | Mean distinct | Mean heap pops | GM cost / optimal | p95 cost ratio | Shared median ms | Mean preprocessing ms |',
   '|---|---:|---:|---:|---:|---:|---:|']
  for m in MODES:
   s=summ[m];lines.append(f"| {m} | {s['mean_unique']:.2f} | {s['mean_operations']:.2f} | {s['gm_path_ratio']:.5f} | {s['p95_path_ratio']:.5f} | {s['median_ms']:.3f} | {s['mean_preprocess_ms']:.3f} |")
  lines += ['', '95% bootstrap intervals for selected/control mean distinct-expansion ratios (2,000 whole-map resamples):', '']
  for c,ci in details[suite]['clustered_mean_unique_ratio_ci95'].items():lines.append(f'- {c}: [{ci[0]:.4f}, {ci[1]:.4f}] (solvable cases).')
  lines += ['', '| Variant | Mean stale pops | Mean duplicate pops | Mean rebuilds | Mean storage counter | Mean alpha events | Mean switches |', '|---|---:|---:|---:|---:|---:|---:|']
  for m in MODES:
   rr=[r for r in rows if r['variant']==m]
   vals=[statistics.mean(v) if (v:=[r[k] for r in rr if r.get(k) is not None]) else None for k in ['stale','duplicates','rebuilds','storage']]
   vals += [statistics.mean(len(r.get(k,[])) for r in rr) for k in ['alpha_events','switches']]
   lines.append('| '+m+' | '+' | '.join((f'{v:.2f}' if v is not None else 'NA') for v in vals)+' |')
  lines += ['', 'Alpha events include initial/reset events where recorded, not just value changes. Storage counters are historical algorithm outputs, not comparable byte-level peak memory; candidate DAG and geometry caches add memory outside these counters. Stale/duplicate labels may overlap; the original does not classify stale snapshots separately and its recorded zero is not proof of their absence. No claim of reduced RAM usage is supported.', '']
  pairs=defaultdict(dict)
  for r in rows:pairs[r['case_id']][r['variant']]=r
  regress={}
  for c in ['original','wa2','direct_only']:
   p=[v for v in pairs.values() if v[c]['optimal_cost'] is not None]
   regress[c]={'more_distinct':sum(v['sieved_cert']['unique']>v[c]['unique'] for v in p),
    'longer_path':sum(v['sieved_cert']['length']>v[c]['length']+1e-8 for v in p),'solvable':len(p)}
  details[suite]['regressions']=regress
  lines+=['',f'Regressions, selected versus controls: `{json.dumps(regress)}`.','']
  # Per-family or prompt grouping, preserving map-clustered main inference.
  groups=defaultdict(list)
  for r in rows:
   label=r['family'] if suite.endswith('synthetic') else r['case_id'].split('_')[-1]
   groups[(label,r['variant'])].append(r)
  lines+=['| Condition | Original distinct | WA2 distinct | Selected distinct |','|---|---:|---:|---:|']
  for label in sorted({k[0] for k in groups}):
   vals=[statistics.mean(r['unique'] for r in groups[label,m]) for m in ['original','wa2','sieved_cert']]
   lines.append('| '+label+' | '+' | '.join((f'{v:.2f}' if v is not None else 'NA') for v in vals)+' |')
  modes=['original','current_adaptive','astar','wa2','direct_only','sieved_no_repair','sieved_no_cut','sieved_cert']
  ax.barh(range(len(modes)),[summ[m]['mean_unique'] for m in modes],color=['#6688aa']*7+['#26855b'])
  ax.set_yticks(range(len(modes)),modes);ax.invert_yaxis();ax.set_xlabel('Mean distinct expansions (all cases)');ax.set_title(suite.replace('heldout_',''))
  details[suite]['graph_preprocessing_seconds']=sum(g['seconds'] for g in data['graph_preprocessing'])
 fig.tight_layout();fig.savefig(BASE/'expansions.png',dpi=180);fig.savefig(BASE/'expansions.pdf');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.5))
 summary=json.loads((BASE/'heldout_cached/summary.json').read_text())
 modes=['original','alpha05','current_adaptive','astar','wa2','direct_only','sieved_cert']
 for m in modes:
  q=summary[m];axes[0].scatter(q['mean_unique'],100*(q['gm_path_ratio']-1),s=55)
  axes[0].annotate(m,(q['mean_unique'],100*(q['gm_path_ratio']-1)),xytext=(4,5),textcoords='offset points',fontsize=8)
 axes[0].set_xlim(150,440);axes[0].set_xlabel('Mean distinct expansions');axes[0].set_ylabel('GM path-cost inflation (%)');axes[0].set_title('Cached held-out efficiency / quality')
 timing=json.loads((BASE/'native_timing.json').read_text())['summary']
 axes[1].bar(list(timing),[v['median_ms'] for v in timing.values()],color=['#6688aa']*3+['#26855b'])
 axes[1].set_yscale('log');axes[1].set_ylabel('Fresh-query median CPU ms (log scale)');axes[1].set_title('Includes geometry / preprocessing')
 fig.tight_layout();fig.savefig(BASE/'quality_runtime.png',dpi=180);fig.savefig(BASE/'quality_runtime.pdf');plt.close(fig)
 native=json.loads((BASE/'native_timing.json').read_text())
 lines += ['','## Fresh-query CPU timing','',native['scope'],'','| Variant | Median ms | Mean ms |','|---|---:|---:|']
 for m,s in native['summary'].items():lines.append(f"| {m} | {s['median_ms']:.3f} | {s['mean_ms']:.3f} |")
 lines+=['','Selected is slower than matched WA2 and direct-only controls. The larger speedup over native original combines search changes with geometry/engine engineering and cannot be attributed to waypoint selection alone.',
  '', 'Independent verification:', '', '```json', (BASE/'verification.json').read_text().strip(),'```',
  '', 'Additional graph preparation CPU totals and clustered comparisons are in `report_statistics.json`. No confidence interval treats three prompt styles as independent map samples.']
 (BASE/'REPORT.md').write_text('\n'.join(lines)+'\n');(BASE/'report_statistics.json').write_text(json.dumps(details,indent=2)+'\n')
 with (BASE/'aggregate.csv').open('w') as f:
  writer=csv.writer(f);writer.writerow(['suite','variant','mean_distinct','mean_heap_pops','gm_cost_ratio','median_ms'])
  for suite in ['heldout_cached','heldout_synthetic']:
   for m,s in json.loads((BASE/suite/'summary.json').read_text()).items():writer.writerow([suite,m,s['mean_unique'],s['mean_operations'],s['gm_path_ratio'],s['median_ms']])
 print(json.dumps(details,indent=2))
if __name__=='__main__':main()
