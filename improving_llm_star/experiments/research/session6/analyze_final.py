"""Map-clustered paired analysis of the frozen held-out benchmark."""
import argparse
import csv
import gzip
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


def gm(values):
    return math.exp(statistics.mean(math.log(v) for v in values)) if values else None


def quantile(values,p):
    if not values:return None
    v=sorted(values);return v[min(len(v)-1,int(p*(len(v)-1)))]


def clustered_ratio(pairs,bootstrap=4000,geometric=False):
    groups=defaultdict(list)
    for map_id,a,b in pairs:
        if a is None or b is None or a<0 or b<0:continue
        if geometric and (a<=0 or b<=0):continue
        groups[map_id].append((a,b))
    if not groups:return None
    def estimate(rows):
        if geometric:return gm([a/b for a,b in rows])
        denominator=sum(b for a,b in rows)
        return sum(a for a,b in rows)/denominator if denominator>0 else None
    keys=list(groups);rng=random.Random(202611196);samples=[]
    for _ in range(bootstrap):
        samples.append(estimate([p for k in rng.choices(keys,k=len(keys)) for p in groups[k]]))
    undefined=sum(x is None for x in samples);samples=sorted(x for x in samples if x is not None)
    all_pairs=[p for rows in groups.values() for p in rows]
    ci=[quantile(samples,.025),quantile(samples,.975)] if samples else None
    if ci is not None and undefined/bootstrap>.025:ci[1]=None
    return {'ratio':estimate(all_pairs),'ci95':ci,
            'zero_denominator_bootstrap_fraction':undefined/bootstrap,
            'cases':len(all_pairs),'maps':len(groups),'resampling':'Whole maps, all paired queries retained'}


def summarize(rows,paper=None,primary='hybrid'):
    by=defaultdict(list)
    for r in rows:by[r['method']].append(r)
    summaries={};case_data={}
    for method,rr in by.items():
        groups=defaultdict(list)
        for r in rr:groups[r['case_id']].append(r)
        one=[]
        for cid,group in groups.items():
            audit=next((r for r in group if r['rep']==-1),None)
            timed=[r for r in group if r['rep']>=0]
            complete=[r for r in timed if r['valid']]
            if audit is None:continue
            value=dict(audit,median_seconds=statistics.median(r['seconds'] for r in timed) if timed else None,
                timed_successes=len(complete),timed_trials=len(timed),
                native_timeouts=sum(r.get('error')=='timeout' for r in timed))
            one.append(value);case_data[cid,method]=value
        valid=[r for r in one if r['valid']];times=[r['median_seconds'] for r in one if r['median_seconds'] is not None]
        cost=[r['cost_ratio'] for r in valid]
        operations=[r['operation'] for r in valid if r.get('operation') is not None]
        pop=[r['audit']['pop'] for r in valid];push=[r['audit']['push'] for r in valid]
        operation_ratio=[];storage_ratio=[]
        if paper:
            for r in valid:
                reference=paper.get(r['case_id'])
                if reference and reference['valid'] and reference.get('operation'):
                    operation_ratio.append(r['operation']/reference['operation'])
                    storage_ratio.append(r.get('storage',0)/reference['storage'])
        summaries[method]={'cases':len(one),'valid_audits':len(valid),
            'audit_timeouts':sum(r.get('error')=='timeout' for r in one),
            'native_timeouts':sum(r['native_timeouts'] for r in one),
            'native_trials':sum(r['timed_trials'] for r in one),
            'mean_ms':1000*statistics.mean(times) if times else None,
            'median_ms':1000*statistics.median(times) if times else None,
            'p95_ms':1000*quantile(times,.95) if times else None,
            'mean_unique':statistics.mean(r.get('unique_total',r.get('unique',0)) for r in valid) if valid else None,
            'mean_search_operations':statistics.mean(operations) if operations else None,
            'mean_total_heap_pops':statistics.mean(pop) if pop else None,
            'mean_total_heap_pushes':statistics.mean(push) if push else None,
            'mean_queue_operations':statistics.mean(a+b for a,b in zip(pop,push)) if pop else None,
            'mean_heapify_calls':statistics.mean(r['audit']['heapify'] for r in valid) if valid else None,
            'mean_all_heap_api_calls':statistics.mean(r['audit']['pop']+r['audit']['push']+r['audit']['heapify'] for r in valid) if valid else None,
            'mean_open_rebuilds':statistics.mean(r.get('rebuilds',0) or 0 for r in valid) if valid else None,
            'mean_storage_states':statistics.mean(r.get('storage',0) for r in valid) if valid else None,
            'gm_cost_ratio':gm(cost),'mean_cost_ratio':statistics.mean(cost) if cost else None,
            'p95_cost_ratio':quantile(cost,.95),'max_cost_ratio':max(cost) if cost else None,
            'paper_operation_ratio_percent':100*statistics.mean(operation_ratio) if operation_ratio else None,
            'paper_storage_ratio_percent':100*statistics.mean(storage_ratio) if storage_ratio else None,
            'paper_ratio_cases':len(operation_ratio),
            'mean_macro_probes':statistics.mean(r.get('macro_probes',0) for r in valid) if valid else None,
            'mean_geometry_ms':1000*statistics.mean(r.get('geometry_preprocess_seconds',0) for r in valid) if valid else None,
            'mean_provider_cpu_ms':1000*statistics.mean(r.get('provider_seconds',0) for r in valid) if valid else None,
            'mean_search_ms':1000*statistics.mean(r['search_seconds'] for r in valid if r.get('search_seconds') is not None) if any(r.get('search_seconds') is not None for r in valid) else None,
            'scope':'Work and path means on completed audits. Native times include capped timed trials; timeouts are censored lower bounds, not complete solution times.'}
    comparisons={}
    if primary in summaries:
        for method in summaries:
            if method==primary:continue
            if method not in summaries:continue
            common=[]
            for cid,m in case_data:
                if m!=primary or (cid,method) not in case_data:continue
                a,b=case_data[cid,primary],case_data[cid,method]
                if a['valid'] and b['valid']:common.append((a,b))
            if not common:continue
            comparisons[method]={
                'total_heap_pops':clustered_ratio([(a['map_id'],a['audit']['pop'],b['audit']['pop']) for a,b in common]),
                'queue_operations':clustered_ratio([(a['map_id'],a['audit']['pop']+a['audit']['push'],b['audit']['pop']+b['audit']['push']) for a,b in common]),
                'unique':clustered_ratio([(a['map_id'],a.get('unique_total',a.get('unique')),b.get('unique_total',b.get('unique'))) for a,b in common]),
                'path_cost':clustered_ratio([(a['map_id'],a['length'],b['length']) for a,b in common],geometric=True),
                'native_seconds':clustered_ratio([(a['map_id'],a['median_seconds'],b['median_seconds']) for a,b in common if a['median_seconds'] is not None and b['median_seconds'] is not None]),
                'worst_runtime_ratio':max(a['median_seconds']/b['median_seconds'] for a,b in common if a['median_seconds'] is not None and b['median_seconds'] is not None),
                'worst_absolute_runtime_regression_ms':max((a['median_seconds']-b['median_seconds'])*1000 for a,b in common if a['median_seconds'] is not None and b['median_seconds'] is not None),
                'win_rate_heap_pops':sum(a['audit']['pop']<b['audit']['pop'] for a,b in common)/len(common),
                'tie_rate_heap_pops':sum(a['audit']['pop']==b['audit']['pop'] for a,b in common)/len(common)}
    return {'summary':summaries,'comparisons':comparisons}


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True)
    p.add_argument('--paper',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--primary',default='hybrid');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);rows=json.load(gzip.open(a.results,'rt'))['runs']
    paper={r['case_id']:r for r in json.load(gzip.open(a.paper,'rt'))['runs'] if r['rep']==-1} if a.paper else None
    strata={'all':rows,'team_maps':[r for r in rows if r['family']=='team_random_walls'],
            'challenging':[r for r in rows if r['family']!='team_random_walls']}
    strata.update({'family_'+family:[r for r in rows if r['family']==family] for family in sorted({r['family'] for r in rows})})
    report={name:summarize(rr,paper,a.primary) for name,rr in strata.items() if rr}
    (a.output/'analysis.json').write_text(json.dumps(report,indent=2))
    with (a.output/'summary.csv').open('w',newline='') as f:
        records=[dict(stratum=s,method=m,**v) for s,data in report.items() for m,v in data['summary'].items()]
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    text=['# Frozen held-out benchmark','',
          'All methods reuse the same raw model outputs. Native timing excludes API latency. Whole-map paired bootstrap, 4,000 resamples. Work/path means exclude incomplete audits; capped timings and timeout counts are disclosed.','']
    for stratum in ['team_maps','challenging']:
        if stratum not in report:continue
        text+=['## '+stratum,'','| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |',
               '|---|---:|---:|---:|---:|---:|---:|---:|']
        for method,v in report[stratum]['summary'].items():
            fmt=lambda x,n=2:'—' if x is None else f'{x:.{n}f}'
            text.append(f'| {method} | {v["valid_audits"]}/{v["cases"]} | {fmt(v["mean_ms"])} | {fmt(v["mean_unique"],1)} | {fmt(v["mean_total_heap_pops"],1)} | {fmt(v["mean_queue_operations"],1)} | {fmt(v["gm_cost_ratio"],5)} | {v["audit_timeouts"]} |')
        text.append('')
    (a.output/'RESULTS.md').write_text('\n'.join(text)+'\n')
    print(a.output/'RESULTS.md')


if __name__=='__main__':main()
