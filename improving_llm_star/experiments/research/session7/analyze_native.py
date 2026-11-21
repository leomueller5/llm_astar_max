"""Map-paired statistics, preserving censored cases and seed dependence."""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path
import numpy as np
from common import read_cases,dump
from data_audit import fingerprint

def average(values):
    v=[x for x in values if x is not None and math.isfinite(x)];return statistics.mean(v) if v else None

def collapse(rows,cases):
    groups=defaultdict(list)
    for r in rows:groups[r['case_id'],r['method'],r.get('seed',0)].append(r)
    seeds=defaultdict(list)
    for (cid,method,seed),rr in groups.items():
        audit=next((r for r in rr if r['rep']==-1),None);native=[r for r in rr if r['rep']>=0]
        if audit is None:continue
        count=audit.get('audit') or {};pop=count.get('pop');push=count.get('push');classification=audit.get('label_pop_classification') or {}
        seedrow={'case_id':cid,'method':method,'seed':seed,'valid':bool(audit.get('valid')),'seconds':statistics.median(r['seconds'] for r in native) if native else None,'native_timeouts':sum(r.get('error')=='timeout' for r in native),'native_trials':len(native),'native_valid_trials':sum(bool(r.get('valid')) for r in native),'audit_timeout':audit.get('error')=='timeout',
            'pops':pop,'pushes':push,'queue_operations':pop+push if pop is not None and push is not None else None,'heapify_calls':count.get('heapify'),'operation':audit.get('operation'),'storage':audit.get('storage'),'unique':audit.get('unique'),'expanded':audit.get('expanded'),'stale':audit.get('stale'),'reopens':audit.get('reopens'),'rebuilds':audit.get('rebuilds'),
            'already_closed_pops':classification.get('already_closed_label_pops') if classification.get('trace_fully_matched') else audit.get('duplicate_pops',audit.get('duplicates')),'cost_ratio':audit.get('cost_ratio'),'search_seconds':audit.get('search_seconds'),'heuristic_seconds':audit.get('heuristic_seconds'),'guidance_seconds':audit.get('guidance_seconds'),'coverage':audit.get('prediction_coverage')}
        for key in ['search_seconds','heuristic_seconds','guidance_seconds','grid_seconds','region_seconds','prediction_parse_seconds','provider_seconds','candidate_seconds','preprocess_seconds']:
            vv=[r[key] for r in native if r.get(key) is not None and r.get('valid')]
            seedrow[key]=statistics.median(vv) if vv else None
        seeds[cid,method].append(seedrow)
    result=[]
    for (cid,method),rr in seeds.items():
        c=cases[cid];group=fingerprint(c['query']);r={'case_id':cid,'map_id':c['map_id'],'geometry_group':group,'family':c['family'],'stratum':'large' if max(c['query']['range_x'][1],c['query']['range_y'][1])>220 else 'primary','method':method,'seeds':len(rr),'valid':all(s['valid'] for s in rr),'native_timeouts':sum(s['native_timeouts'] for s in rr),'native_trials':sum(s['native_trials'] for s in rr),'native_valid_trials':sum(s['native_valid_trials'] for s in rr),'audit_timeouts':sum(s['audit_timeout'] for s in rr)}
        for key in ['seconds','pops','pushes','queue_operations','heapify_calls','operation','storage','unique','expanded','stale','reopens','rebuilds','already_closed_pops','search_seconds','heuristic_seconds','guidance_seconds','grid_seconds','region_seconds','prediction_parse_seconds','provider_seconds','candidate_seconds','preprocess_seconds','coverage']:r[key]=average(s[key] for s in rr) if key=='seconds' or r['valid'] else None
        r['cost_ratio']=math.exp(statistics.mean(math.log(s['cost_ratio']) for s in rr)) if r['valid'] else None
        result.append(r)
    return result

def paired(rows,control,metric,primary='rh_image105',samples=4000,geometric=False):
    lookup={(r['case_id'],r['method']):r for r in rows};pairs=[]
    for r in rows:
        if r['method']!=primary or (r['case_id'],control) not in lookup:continue
        other=lookup[r['case_id'],control];x,y=r.get(metric),other.get(metric)
        if x is None or y is None or not math.isfinite(x+y):continue
        pairs.append((r['geometry_group'],x,y))
    if not pairs:return None
    grouped=defaultdict(list)
    for group,x,y in pairs:grouped[group].append((x,y))
    if geometric:
        grouped={g:[(math.log(x/y),1.) for x,y in v if x>0 and y>0] for g,v in grouped.items()}
    sums=np.array([[sum(x for x,y in v),sum(y for x,y in v)] for v in grouped.values()]);rng=np.random.default_rng(2026112007);idx=rng.integers(0,len(sums),(samples,len(sums)));boot=sums[idx].sum(1)
    with np.errstate(divide='ignore',invalid='ignore'):ratios=boot[:,0]/boot[:,1]
    if geometric:ratios=np.exp(ratios)
    finite=ratios[np.isfinite(ratios)];ratio=float(sums[:,0].sum()/sums[:,1].sum()) if sums[:,1].sum()>0 else None
    if geometric and ratio is not None:ratio=math.exp(ratio)
    return {'ratio':ratio,'ci95':np.quantile(finite,[.025,.975]).tolist() if len(finite) else None,'cases':len(pairs),'map_geometries':len(grouped),'undefined_bootstrap_fraction':float(1-len(finite)/samples),'resampling':'Whole canonical geometries, all paired queries retained; random guidance seeds averaged within query.'}

def summarize(rows,paper):
    summary={}
    for method in sorted({r['method'] for r in rows}):
        rr=[r for r in rows if r['method']==method];valid=[r for r in rr if r['valid']];times=[r['seconds'] for r in rr if r['seconds'] is not None];costs=[r['cost_ratio'] for r in valid]
        s={'cases':len(rr),'valid_audits':len(valid),'audit_timeouts':sum(r['audit_timeouts'] for r in rr),'native_timeouts':sum(r['native_timeouts'] for r in rr),'native_trials':sum(r['native_trials'] for r in rr),'native_valid_trials':sum(r['native_valid_trials'] for r in rr),'mean_ms':1000*statistics.mean(times) if times else None,'median_ms':1000*statistics.median(times) if times else None,'p95_ms':1000*float(np.quantile(times,.95)) if times else None,'gm_cost_ratio':math.exp(statistics.mean(math.log(v) for v in costs)) if costs else None,'max_cost_ratio':max(costs) if costs else None}
        for key in ['pops','pushes','queue_operations','heapify_calls','operation','storage','unique','expanded','stale','already_closed_pops','reopens','rebuilds','search_seconds','heuristic_seconds','guidance_seconds','grid_seconds','region_seconds','prediction_parse_seconds','provider_seconds','candidate_seconds','preprocess_seconds','coverage']:s['mean_'+key]=average(r.get(key) for r in valid)
        op=[];storage=[]
        for r in valid:
            ref=paper.get(r['case_id']) if paper else None
            if ref and ref.get('valid') and ref.get('operation') and r.get('operation') is not None:
                op.append(100*r['operation']/ref['operation']);storage.append(100*r['storage']/ref['storage'])
        s.update(paper_operation_ratio_percent=average(op),paper_storage_ratio_percent=average(storage),paper_ratio_cases=len(op));summary[method]=s
    comparisons={}
    for method in summary:
        if method=='rh_image105':continue
        comparisons[method]={key:paired(rows,method,key,geometric=key=='cost_ratio') for key in ['pops','queue_operations','unique','seconds','cost_ratio']}
    return {'summary':summary,'paired_primary_over_control':comparisons}

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--cases',required=True);p.add_argument('--paper');p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);cases={c['id']:c for c in read_cases(a.cases)};rows=collapse(read_cases(a.results)['runs'],cases);paper={r['case_id']:r for r in read_cases(a.paper)['runs'] if r['rep']==-1} if a.paper else {}
    strata={'primary':[r for r in rows if r['stratum']=='primary'],'large':[r for r in rows if r['stratum']=='large'],'all':rows}
    strata.update({'family_'+f:[r for r in rows if r['family']==f] for f in sorted({r['family'] for r in rows})});report={k:summarize(v,paper) for k,v in strata.items() if v};dump(out/'analysis.json',report);dump(out/'case_level.json.gz',rows)
    records=[dict(stratum=k,method=m,**s) for k,v in report.items() for m,s in v['summary'].items()]
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
    text=['# Frozen Session7 results','','Planning CPU uses cached advice, fresh preprocessing, five native trials. First-use prompt/image and actual API latency reported separately. Native timeouts are right-censored; their measured cap contributes to the mean, never treated as zero. Work/path means use completed audits with coverage shown. Whole-geometry paired bootstrap4000, nominal intervals without multiplicity correction.','']
    for stratum in ['primary','large']:
        if stratum not in report:continue
        text+=['## '+stratum,'','| Method | Valid | Mean ms | Pops | Push+pop | Unique | GM cost/opt | Timeouts |','|---|---:|---:|---:|---:|---:|---:|---:|']
        def fmt(v,n=2):return '—' if v is None else f'{v:.{n}f}'
        for method,s in report[stratum]['summary'].items():text.append(f'| {method} | {s["valid_audits"]}/{s["cases"]} | {fmt(s["mean_ms"])} | {fmt(s["mean_pops"],1)} | {fmt(s["mean_queue_operations"],1)} | {fmt(s["mean_unique"],1)} | {fmt(s["gm_cost_ratio"],5)} | {s["audit_timeouts"]} |')
        text.append('')
    (out/'RESULTS.md').write_text('\n'.join(text).rstrip()+'\n');print(out/'RESULTS.md')
if __name__=='__main__':main()
