"""Map-clustered paired analysis and standalone charts for Session 3."""
import json,gzip,math,statistics,sys,os,csv
from pathlib import Path
from collections import defaultdict
import numpy as np
BASE=Path(__file__).resolve().parents[2]/'results/research_session3'
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[4]/'.venv/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def analyze(data):
 group=defaultdict(list)
 for r in data['runs']:group[r['case_id'],r['variant']].append(r)
 cases={}
 for (cid,mode),rr in group.items():
  r=dict(rr[0]);r['time']=statistics.median(x['fresh_seconds'] for x in rr)
  r['prep']=statistics.median(x['preprocess_seconds']+x['geometry_init_seconds'] for x in rr)
  r['search']=statistics.median(x['search_seconds'] for x in rr)
  cases.setdefault(cid,{})[mode]=r
 maps=sorted({next(iter(c.values()))['map_id'] for c in cases.values()});index={m:i for i,m in enumerate(maps)}
 samples=np.random.default_rng(202611163).integers(0,len(maps),(2000,len(maps)));out={}
 for mode in data['variants']:
  rr=[c[mode] for c in cases.values()];ref=[c['guide_off'] for c in cases.values()]
  def paired(control,metric):
   a=np.zeros(len(maps));b=np.zeros(len(maps))
   for c in cases.values():
    i=index[c[mode]['map_id']];a[i]+=c[mode][metric];b[i]+=c[control][metric]
   boot=a[samples].sum(axis=1)/b[samples].sum(axis=1)
   return {'ratio':float(a.sum()/b.sum()),'ci95':np.quantile(boot,[.025,.975]).tolist()}
  def cost_pair(control):
   sums=np.zeros(len(maps));counts=np.zeros(len(maps))
   for c in cases.values():
    a,b=c[mode],c[control]
    if a['valid'] and b['valid'] and a['length']>0 and b['length']>0:
     i=index[a['map_id']];sums[i]+=math.log(a['length']/b['length']);counts[i]+=1
   denominator=counts[samples].sum(axis=1);valid=denominator>0
   boot=np.exp(sums[samples].sum(axis=1)[valid]/denominator[valid])
   return {'ratio':float(math.exp(sums.sum()/counts.sum())),'ci95':np.quantile(boot,[.025,.975]).tolist()}
  ratios=[r['length']/c['indexed_astar']['length'] for c in cases.values() if (r:=c[mode])['valid'] and c['indexed_astar']['length']>0]
  out[mode]={'cases':len(rr),'solvable':sum(c['indexed_astar']['valid'] for c in cases.values()),'valid':sum(r['valid'] for r in rr),
   'mean_ms':statistics.mean(r['time'] for r in rr)*1000,'median_ms':statistics.median(r['time'] for r in rr)*1000,
   'p95_ms':float(np.quantile([r['time'] for r in rr],.95)*1000),'mean_prep_ms':statistics.mean(r['prep'] for r in rr)*1000,
   'mean_search_ms':statistics.mean(r['search'] for r in rr)*1000,'unique':statistics.mean(r['unique'] for r in rr),
   'pops':statistics.mean(r['operation'] for r in rr),'gm_cost_ratio':math.exp(statistics.mean(math.log(x) for x in ratios)),
   'p95_cost_ratio':float(np.quantile(ratios,.95)),'max_cost_ratio':max(ratios),
   'accepted_queries':sum(r.get('guidance_accepted',0)>0 for r in rr),
   'examined_candidates':sum(r.get('guidance_candidates',0) for r in rr),
   'accepted_seeds_or_targets':sum(r.get('guidance_accepted',0) for r in rr),
   'fewer_states':sum(r['unique']<b['unique'] for r,b in zip(rr,ref)),
   'more_states':sum(r['unique']>b['unique'] for r,b in zip(rr,ref)),
   'shorter_paths':sum(r['valid'] and b['valid'] and r['length']<b['length']-1e-8 for r,b in zip(rr,ref)),
   'longer_paths':sum(r['valid'] and b['valid'] and r['length']>b['length']+1e-8 for r,b in zip(rr,ref)),
   'both_improve':sum(r['valid'] and b['valid'] and r['unique']<b['unique'] and r['length']<b['length']-1e-8 for r,b in zip(rr,ref)),
   'vs_off_time':paired('guide_off','time'),'vs_geometry_time':paired('geometry_lazy','time'),
   'vs_off_unique':paired('guide_off','unique'),'cost_vs_off':cost_pair('guide_off'),'cost_vs_geometry':cost_pair('geometry_lazy'),'cost_vs_uniform15':cost_pair('uniform15'),
   'families':{family:{'mean_ms':statistics.mean(r['time'] for r in rr if r['family']==family)*1000,'unique':statistics.mean(r['unique'] for r in rr if r['family']==family)} for family in sorted({r['family'] for r in rr})}}
  if mode=='seed_cut_shuffle':
   assert all(c[mode]['unique']==c['seed_cut']['unique'] and c[mode]['length']==c['seed_cut']['length'] for c in cases.values())
 return out


def main():
 allstats={};lines=['# Session 3: real waypoint contribution','',
 'Algorithms frozen in commit79b96f3 before Session3 validation. No old held-out test reuse. Real validation is the established20-map split used by prior sessions; fresh30-map/240-case fixtures are new geometry, but helpful points are oracle fixtures, not actual model responses. No paid calls. CIs:2000 whole-map bootstrap resamples, secondary comparisons exploratory/unadjusted.','']
 fig,axes=plt.subplots(1,2,figsize=(13,5));csvrows=[]
 for ax,cohort in zip(axes,['validation','fresh']):
  with gzip.open(BASE/cohort/'results.json.gz','rt') as f:data=json.load(f)
  stats=analyze(data);allstats[cohort]=stats
  lines+=['## '+cohort,'','All times include fresh graph construction, guidance preprocessing and search. Cached response parsing excluded equally from core variants; see separate public-API timings. Medians within query first; arithmetic mean across queries.','',
   '| Method | Mean ms | Median ms | Distinct | Pops | GM cost / optimal | Valid / solvable | Hint queries accepted |','|---|---:|---:|---:|---:|---:|---:|---:|']
  for mode,s in stats.items():
   lines.append(f"| {mode} | {s['mean_ms']:.4f} | {s['median_ms']:.4f} | {s['unique']:.2f} | {s['pops']:.2f} | {s['gm_cost_ratio']:.5f} | {s['valid']}/{s['solvable']} | {s['accepted_queries']} |")
   csvrows.append([cohort,mode,s['mean_ms'],s['unique'],s['pops'],s['gm_cost_ratio'],s['accepted_queries']])
  lines+=['','| Candidate | Time / matched off (95% CI) | Time / geometric seeding (95% CI) | Fewer / more states | Shorter / longer paths |','|---|---:|---:|---:|---:|']
  for mode in ['seed_cut','seed_lazy','potential_visible','potential_geometry','potential_random','seed_cut_wrong','seed_cut_random']:
   s=stats[mode];a=s['vs_off_time'];b=s['vs_geometry_time']
   lines.append(f"| {mode} | {a['ratio']:.4f} [{a['ci95'][0]:.4f},{a['ci95'][1]:.4f}] | {b['ratio']:.4f} [{b['ci95'][0]:.4f},{b['ci95'][1]:.4f}] | {s['fewer_states']}/{s['more_states']} | {s['shorter_paths']}/{s['longer_paths']} |")
  lines+=['','Worst-case cost ratios, candidate acceptance counts, search-only/preparation times and per-family numbers are in report_statistics.json. A lower heuristic can improve quality without demonstrating informative LLM content; compare uniform15 and randomized/geometric potentials. Ranking deliberately ignores input order; shuffle must match counts/costs exactly.','']
  modes=['guide_off','witness_only','seed_cut','seed_lazy','geometry_lazy','seed_cut_wrong','seed_cut_random','potential_visible','potential_geometry','uniform15']
  ax.barh(modes,[stats[m]['mean_ms'] for m in modes],color=['#718ca6']*2+['#24845f','#24845f','#b08a43','#af6470','#af6470','#528f83','#b08a43','#718ca6']);ax.invert_yaxis();ax.set_xlabel('Mean within-case median elapsed ms');ax.set_title(cohort)
 fig.tight_layout();fig.savefig(BASE/'comparison.png',dpi=180);fig.savefig(BASE/'comparison.pdf');plt.close(fig)
 public=BASE/'public_timing.json'
 if public.exists():
  p=json.loads(public.read_text());lines+=['## Cached public interface','',p['scope'],'','```json',json.dumps(p['summary'],indent=2),'```','']
 verification=BASE/'verification.json'
 if verification.exists():lines+=['## Independent verification','','```json',verification.read_text().strip(),'```','']
 lines+=['The global bound of new methods is2, not optimality. Exact geometry certificates remain optimal. Verified seeds only add real grid paths; start remains OPEN, stale snapshots are skipped, improved paths reopen, and macro parents are replaced on improvements. Original source/scoring preserved. No claim of LLM-specific efficiency is allowed if matched no-guidance/geometric/random controls are competitive.']
 (BASE/'REPORT.md').write_text('\n'.join(lines)+'\n');(BASE/'report_statistics.json').write_text(json.dumps(allstats,indent=2)+'\n')
 with (BASE/'aggregate.csv').open('w') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['cohort','variant','mean_case_median_ms','mean_distinct','mean_heap_pops','gm_cost_ratio','accepted_queries']);w.writerows(csvrows)
 for cohort,ss in allstats.items():
  for mode in ['guide_off','seed_cut','seed_lazy','geometry_lazy','potential_visible','uniform15']:print(cohort,mode,ss[mode]['mean_ms'],ss[mode]['gm_cost_ratio'],ss[mode]['vs_off_time'],flush=True)
if __name__=='__main__':main()
