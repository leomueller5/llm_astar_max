"""Paired map-clustered statistics, reducing repetitions within query first."""
import sys,json,gzip,math,statistics,random,argparse
from collections import defaultdict
from pathlib import Path


def aggregate(data,control='scheduled_wa2',bootstrap=2000):
 groups=defaultdict(list)
 for r in data['runs']:groups[r['case_id'],r['variant']].append(r)
 cases={}
 for (case,mode),rr in groups.items():
  v=dict(rr[0]);v['median_seconds']=statistics.median(r['fresh_seconds'] for r in rr)
  v['mean_seconds']=statistics.mean(r['fresh_seconds'] for r in rr)
  v['median_cpu_seconds']=statistics.median(r['cpu_seconds'] for r in rr)
  cases.setdefault(case,{})[mode]=v
 modes=sorted({m for c in cases.values() for m in c});out={}
 for mode in modes:
  pairs=[(c[mode],c[control]) for c in cases.values() if mode in c and control in c]
  if not pairs:continue
  rr=[a for a,b in pairs];clusters=defaultdict(list)
  for a,b in pairs:clusters[a['map_id']].append((a,b))
  def measures(ps):
   time=sum(a['median_seconds'] for a,b in ps)/sum(b['median_seconds'] for a,b in ps)
   gm=math.exp(statistics.mean(math.log(a['median_seconds']/b['median_seconds']) for a,b in ps))
   return time,gm
  ratio,gm=measures(pairs);rng=random.Random(20261116);cc=list(clusters.values());boot=[]
  for _ in range(bootstrap):boot.append(measures([p for _ in cc for p in rng.choice(cc)]))
  opt=[]
  for a,b in pairs:
   cost=a.get('optimal_cost')
   if cost is None:
    ref=cases[a['case_id']].get('indexed_astar')
    if ref and ref['valid']:cost=ref['length']
   if cost and a['valid']:opt.append(a['length']/cost)
  out[mode]={'cases':len(rr),'mean_case_median_ms':statistics.mean(r['median_seconds'] for r in rr)*1000,
    'median_case_median_ms':statistics.median(r['median_seconds'] for r in rr)*1000,
    'mean_raw_ms_including_outliers':statistics.mean(r['mean_seconds'] for r in rr)*1000,
    'ratio_of_mean_times':ratio,'gm_paired_time_ratio':gm,
    'ratio_of_mean_times_ci95':[sorted(v[0] for v in boot)[49],sorted(v[0] for v in boot)[1949]],
    'gm_paired_time_ratio_ci95':[sorted(v[1] for v in boot)[49],sorted(v[1] for v in boot)[1949]],
    'unique':statistics.mean(r['unique'] for r in rr),'operations':statistics.mean(r['operation'] for r in rr),
    'successes':sum(r['valid'] for r in rr),'exact_certificates':sum(r.get('certified_early_return',False) for r in rr),
    'llm_accepted':sum((r.get('accepted_source')=='waypoint_dag') or ('accepted_source' not in r and r.get('certified_early_return',False) and r.get('candidate_source')=='waypoint_dag') for r in rr),
    'incumbent_used':sum(r.get('incumbent_used',False) for r in rr),
    'gm_cost_ratio':math.exp(statistics.mean(math.log(v) for v in opt)) if opt else None,
    'p95_cost_ratio':sorted(opt)[min(len(opt)-1,int(.95*len(opt)))] if opt else None,
    'max_cost_ratio':max(opt) if opt else None,
    'longer_than_control':sum(a['valid'] and b['valid'] and a['length']>b['length']+1e-8 for a,b in pairs),
    'more_unique_than_control':sum(a['unique']>b['unique'] for a,b in pairs),
    'family_mean_ms':{family:statistics.mean(r['median_seconds'] for r in rr if r['family']==family)*1000 for family in sorted({r['family'] for r in rr})}}
 return out


def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--control',default='scheduled_wa2');a=p.parse_args()
 with gzip.open(a.directory/'results.json.gz','rt') as f:data=json.load(f)
 out=aggregate(data,a.control)
 (a.directory/('analysis_'+a.control+'.json')).write_text(json.dumps(out,indent=2)+'\n')
 for mode,r in out.items():print(mode,round(r['mean_case_median_ms'],4),round(r['ratio_of_mean_times'],4),r['ratio_of_mean_times_ci95'],'LLM',r['llm_accepted'])
if __name__=='__main__':main()
