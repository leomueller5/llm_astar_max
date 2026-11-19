"""Offline paired search and prediction quality. Never sends requests."""
import argparse,math,random,statistics
from collections import Counter
from pathlib import Path
from time import perf_counter
from common import read_cases,dump
from prompts_spatial import decode
from oracle import remaining_costs,oracle_path,anchor,regional_reference
from llmastar.research.spatial_guidance import RegionField,SpatialSearch
from llmastar.research.geometric_advice import portfolio
from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route

def geometric_field(q,side,kind='best'):
    g=SegmentGridGraph(q);f=RegionField(q,side,g);p=portfolio(q,g,budget=12)
    routes=[p['geometry_best']] if kind=='best' else [r['route'] for r in p['candidates'][:3]]
    votes=Counter()
    for route in routes:
        dense=expand_lattice_route(route) if route else []
        votes.update(set(f.identifier(n) for n in dense))
    f.update([{'region_id':r['id'],'priority':1. if votes[r['id']]>=len(routes)//2+1 else .5,'confidence':1.,'detour':0.} for r in f.regions]);return f

def permuted(field,seed):
    rng=random.Random(seed);f=RegionField(field.query,field.side);keys=list(field.values);values=list(field.values.values());rng.shuffle(values)
    f.update([{'region_id':k,'detour':v[0],'priority':v[1],'confidence':v[2]} for k,v in zip(keys,values)]);return f

def quality(c,field,costs,task):
    q=c['query'];path=oracle_path(q,costs);truth={field.identifier(p) for p in path};preferred={k for k,v in field.values.items() if v[1]>.5};avoid={k for k,v in field.values.items() if v[1]<.5};h=anchor(q,'cut');errors=[];baseline=[];over=under=0
    for region in field.regions:
        p=tuple(region['sample']) if region['sample'] else None
        if p not in costs:continue
        d,pr,conf=field.value(p);prediction=h(p)+d;errors.append(abs(prediction-costs[p]));baseline.append(abs(h(p)-costs[p]));over+=prediction>costs[p]+1e-8;under+=prediction<costs[p]-1e-8
    return {'canonical_path_region_precision':len(preferred&truth)/len(preferred) if preferred else None,'canonical_path_region_recall':len(preferred&truth)/len(truth),'avoided_canonical_path_fraction':len(avoid&truth)/len(truth),'start_region_preferred':field.identifier(q['start']) in preferred,'goal_region_preferred':field.identifier(q['goal']) in preferred,'mean_abs_remaining_cost_error':statistics.mean(errors) if errors else None,'geometric_mean_abs_remaining_cost_error':statistics.mean(baseline) if baseline else None,'overestimation_fraction':over/len(errors) if errors else None,'underestimation_fraction':under/len(errors) if errors else None,'preferred_count':len(preferred),'avoid_count':len(avoid)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=1);p.add_argument('--limit',type=int);a=p.parse_args()
    out=Path(a.output)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);cases={c['id']:c for c in read_cases(a.cases)};responses=read_cases(a.responses)['runs'];rows=[];qualities=[];refs={};fieldcache={}
    for response in responses[:a.limit]:
        c=cases[response['case_id']];q=c['query'];task=response['task'];side=response['side'];representation=response['representation'];raw=response['response']['choices'][0]['message'].get('content') or ''
        if c['id'] not in refs:refs[c['id']]=remaining_costs(q)
        costs,refwork=refs[c['id']];real,_=decode(q,raw,side,task);qualities.append(dict(case_id=c['id'],family=c['family'],representation=representation,task=task,**quality(c,real,costs,task)))
        if (c['id'],side) not in fieldcache:fieldcache[c['id'],side]=(geometric_field(q,side),geometric_field(q,side,'consensus'),regional_reference(q,side,costs))
        geo,consensus,oracle=fieldcache[c['id'],side]
        for signal,weight in [('priority',1.5)] if task=='corridor' else [('detour',1.),('combined',1.5)]:
            for control,field in [('real',real),('none',None),('geometry',geo),('geometry_consensus',consensus),('shuffled',permuted(real,c['id'])),('oracle',oracle)]:
                modes=['envelope','focal','dual'] if signal=='priority' else ['envelope']
                for mode in modes:
                    times=[]
                    for rep in range(a.repeats):
                        start=perf_counter();r=SpatialSearch(mode=mode,base_weight=weight,signal=signal).search(q,field);times.append(perf_counter()-start)
                    assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
                    rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=representation,task=task,signal=signal,mode=mode,control=control,pops=r['heap_pops'],pushes=r['heap_pushes'],expanded=r['expanded'],unique=r['unique'],reopens=r['reopens'],seconds=statistics.median(times),guidance_seconds=r['guidance_seconds'],cost_ratio=r['length']/c['optimal_cost'],valid=r['valid']))
        print(c['id'],representation,'offline comparison done',flush=True)
        dump(out/'checkpoint.json.gz',{'runs':rows,'qualities':qualities})
    summary={}
    for key in sorted({(r['representation'],r['signal'],r['mode'],r['control']) for r in rows}):
        rr=[r for r in rows if (r['representation'],r['signal'],r['mode'],r['control'])==key];summary['/'.join(key)]={'cases':len(rr),'mean_pops':statistics.mean(r['pops'] for r in rr),'mean_unique':statistics.mean(r['unique'] for r in rr),'mean_ms':1000*statistics.mean(r['seconds'] for r in rr),'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr))}
    dump(out/'results.json.gz',{'scope':'Offline cached response replay. Pilot timing: compare work/quality primarily; field/oracle construction work excluded here and separately acknowledged. Final end-to-end harness must reconstruct preprocessing for every trial. Canonical-path region labels are one optimal route, not all valid alternatives.','summary':summary,'runs':rows,'qualities':qualities,'reference_work':{k:v[1] for k,v in refs.items()}});dump(out/'summary.json',summary)
if __name__=='__main__':main()
