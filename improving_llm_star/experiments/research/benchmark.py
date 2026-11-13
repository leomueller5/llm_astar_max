"""Reproducible offline, map-disjoint research benchmark; never calls an API."""
import argparse
from collections import defaultdict
import contextlib
from dataclasses import asdict
import hashlib
import heapq
import io
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[2]; WORKSPACE=ROOT.parent
sys.path.insert(0,str(ROOT/'experiments'))
os.environ.setdefault('MPLBACKEND','Agg');os.environ.setdefault('MPLCONFIGDIR',str(WORKSPACE/'.venv/matplotlib'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import measure_waypoint_progress as replay
from llmastar.research.search import GridGraph, SearchConfig, WaypointSearch, MOTIONS
from llmastar.utils import list_parse

SEED=20261113

def splits():
    ids=list(range(100));random.Random(SEED).shuffle(ids)
    return {i:('development' if k<60 else 'validation' if k<80 else 'test') for k,i in enumerate(ids)}

def cached_cases(split,prompts=('standard',),limit=None):
    maps=json.loads((WORKSPACE/'llm-astar/dataset/environment_50_30.json').read_text())
    caches={p:json.loads((WORKSPACE/f'table1_reproduction/antworten_{p}.json').read_text()) for p in prompts}
    out=[];assignment=splits()
    for m in maps:
        if split!='all' and assignment[m['id']]!=split:continue
        for j,sg in enumerate(m['start_goal']):
            q={k:m[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
            q=dict(q,start=sg[0],goal=sg[1])
            for prompt in prompts:
                key=f"{m['id']}_{j}";response=caches[prompt][key];parsed=list_parse(response)
                malformed=not(isinstance(parsed,list) and all(isinstance(p,(tuple,list)) and len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in parsed))
                # Same explicit malformed-answer fallback used in the Table 1 notebook.
                if malformed:response='';parsed=list_parse('')
                out.append({'id':f'cached_{key}_{prompt}','map_id':f'cached_{m["id"]}',
                            'split':assignment[m['id']],'family':'cached_public','source':'repository_cached_'+prompt,
                            'query':q,'response':response,'points':parsed,'parse_fallback':malformed})
    return out[:limit] if limit else out

VARIANTS={
 'original':None,
 'alpha05':SearchConfig(alpha=.5,goal_weight=1.5),
 'robust_original':SearchConfig(),
 'astar':SearchConfig(alpha=0,goal_weight=1),
 'wa11':SearchConfig(alpha=0,goal_weight=1.1),
 'wa15':SearchConfig(alpha=0,goal_weight=1.5),
 'wa2':SearchConfig(alpha=0,goal_weight=2),
 'pop_switch':SearchConfig(switch='pop'),
 'budget_skip':SearchConfig(switch='budget'),
 'confidence':SearchConfig(switch='budget',confidence=True,filter_points=True),
 'sparsify':SearchConfig(switch='budget',confidence=True,filter_points=True,simplify=True),
 'focal11':SearchConfig(method='focal',switch='budget',filter_points=True),
 'focal11_goal':SearchConfig(method='focal',focal_guide='goal',filter_points=True),
 'focal11_route':SearchConfig(method='focal',focal_guide='route',switch='budget',filter_points=True),
 'focal105':SearchConfig(method='focal',focal_weight=1.05,switch='budget',filter_points=True),
 'focal12':SearchConfig(method='focal',focal_weight=1.2,switch='budget',filter_points=True),
 'focal11_octile':SearchConfig(method='focal',switch='budget',filter_points=True,heuristic='octile'),
 'astar_octile':SearchConfig(alpha=0,goal_weight=1,heuristic='octile'),
 'current_adaptive':'current',
}
GOAL_ONLY={'astar','wa11','wa15','wa2','astar_octile','focal11_goal'}


def dijkstra(graph,start):
    costs={start:0.};queue=[(0.,start)]
    while queue:
        cost,node=heapq.heappop(queue)
        if cost!=costs[node]:continue
        for n,e in graph.adj.get(node,[]):
            v=cost+e
            if v<costs.get(n,math.inf)-1e-12:costs[n]=v;heapq.heappush(queue,(v,n))
    return costs


def legacy_run(Planner,case,graph,current=False,native=False):
    p=Planner(adaptive_alpha=True) if current else Planner()
    p.model=replay.OfflineModel(case['response'])
    switches=[];started_target=0;old_update=p._update_target
    def update():
        nonlocal started_target
        old=p.s_target;n=len(p.CLOSED);anchor=p.CLOSED[-1]
        switches.append({'expansion':n,'target':old,'active_expansions':n-started_target,
                         'reason':'neighbor','blocked_trigger':not math.isfinite(graph.cost(anchor,old))})
        started_target=n;old_update()
    p._update_target=update
    if not native:
        p.cost=graph.cost
        p.is_collision=lambda a,b:not math.isfinite(graph.cost(a,b))
    started=perf_counter()
    try:
        with contextlib.redirect_stdout(io.StringIO()):r=p.searching(json.loads(json.dumps(case['query'])))
        path=p.plot.path;valid=bool(path) and path[0]==tuple(case['query']['start']) and path[-1]==tuple(case['query']['goal']) and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        assert p.model.calls==1
    except (KeyError,IndexError,TypeError,ValueError) as exc:
        return {'valid':False,'length':None,'error':type(exc).__name__,'operation':len(p.CLOSED),
                'expanded':len(p.CLOSED),'unique':len(set(p.CLOSED)),'duplicates':len(p.CLOSED)-len(set(p.CLOSED)),
                'switches':switches,'total_seconds':perf_counter()-started,'rebuilds':None,'preprocess_seconds':0}
    metrics=getattr(p,'search_metrics',{})
    return {'valid':valid,'length':r['length'] if valid else None,'path':path,
            'operation':r['operation'],'expanded':metrics.get('expanded_nodes',len(p.CLOSED)),
            'unique':len(set(p.CLOSED)),'duplicates':metrics.get('duplicate_pops',len(p.CLOSED)-len(set(p.CLOSED))),
            'reopens':metrics.get('reopened_expansions',0),'stale':metrics.get('stale_pops',0),
            'storage':r['storage'],'switches':switches,'alpha_events':getattr(p,'alpha_history',[]),
            'total_seconds':perf_counter()-started,'rebuilds':metrics.get('open_queue_rebuilds',len(switches)),
            'preprocess_seconds':0,'processed_waypoints':r['llm_output']}


def summarize(records,bootstrap=500):
    by=defaultdict(list)
    for r in records:by[r['variant']].append(r)
    baseline={r['case_id']:r for r in by.get('original',[])}
    out={}
    def gm(values):return math.exp(statistics.mean(math.log(max(v,1e-12)) for v in values)) if values else None
    for name,rows in by.items():
        solved=[r for r in rows if r['optimal_cost'] is not None]
        valid=[r for r in solved if r['valid']]
        pairs=[(r,baseline[r['case_id']]) for r in valid if r['case_id'] in baseline and baseline[r['case_id']]['valid']]
        ratio=[r['length']/r['optimal_cost'] for r in valid if r['optimal_cost']>0]
        value={'cases':len(rows),'solvable':len(solved),'valid_rate':len(valid)/len(solved) if solved else None,
               'mean_unique':statistics.mean(r['unique'] for r in rows),'mean_operations':statistics.mean(r['operation'] for r in rows),
               'gm_path_ratio':gm(ratio),'p95_path_ratio':sorted(ratio)[min(len(ratio)-1,int(.95*len(ratio)))] if ratio else None,
               'gm_unique_vs_original':gm([r['unique']/max(1,b['unique']) for r,b in pairs]),
               'gm_operations_vs_original':gm([r['operation']/max(1,b['operation']) for r,b in pairs]),
               'gm_time_vs_original':gm([r['total_seconds']/b['total_seconds'] for r,b in pairs]),
               'median_ms':statistics.median(r['total_seconds'] for r in rows)*1000,
               'mean_preprocess_ms':statistics.mean(r.get('preprocess_seconds',0) for r in rows)*1000,
               'mean_rebuilds':statistics.mean(r['rebuilds'] or 0 for r in rows),
               'correct_no_path':sum(not r['valid'] for r in rows if r['optimal_cost'] is None),
               'pair_count':len(pairs)}
        # Whole-map bootstrap of paired log expansion ratios, not individual queries.
        groups=defaultdict(list)
        for r,b in pairs:groups[r['map_id']].append(math.log(r['unique']/max(1,b['unique'])))
        if groups:
            rng=random.Random(SEED);keys=list(groups);values=[]
            for _ in range(bootstrap):
                sample=[x for k in rng.choices(keys,k=len(keys)) for x in groups[k]]
                values.append(math.exp(statistics.mean(sample)))
            values.sort();value['unique_ratio_ci95']=[values[int(.025*bootstrap)],values[min(bootstrap-1,int(.975*bootstrap))]]
        out[name]=value
    return out


def finite_json(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {k:finite_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [finite_json(v) for v in value]
    return value


def run(cases,variants,output,record_trace=False):
    source_hashes={str(p.relative_to(WORKSPACE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'llmastar/research/search.py',WORKSPACE/'llm-astar'/replay.PLANNER_PATH]}
    replay.BACKEND='installed'
    Original=replay.load_planner(WORKSPACE/'llm-astar',response='')
    Current=replay.load_planner(ROOT,response='')
    records=[];graph_metadata=[];by_map=defaultdict(list)
    for case in cases:by_map[case['map_id']].append(case)
    for mi,(map_id,group) in enumerate(by_map.items()):
        graph=GridGraph(group[0]['query']); graph_metadata.append({'map_id':map_id,'seconds':graph.preprocess_seconds,'edge_checks':graph.edge_checks})
        for case in group:
            optimal=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(case['query'],[case['query']['start'],case['query']['goal']],graph)
            order=list(variants);random.Random(SEED+sum(map(ord,case['id']))).shuffle(order)
            for name in order:
                spec=VARIANTS[name]
                if name=='original':r=legacy_run(Original,case,graph)
                elif name=='current_adaptive':r=legacy_run(Current,case,graph,True)
                else:
                    pts=[case['query']['start'],case['query']['goal']] if name in GOAL_ONLY else case['points']
                    r=WaypointSearch(spec).search(case['query'],pts,graph)
                r.pop('trace',None) if not record_trace else None
                r.pop('path',None)
                records.append(dict(r,case_id=case['id'],map_id=map_id,source=case['source'],family=case['family'],variant=name,
                                    split=case['split'],optimal_cost=optimal['length'],parse_fallback=case.get('parse_fallback',False)))
        if mi%10==0:print(f'{mi+1}/{len(by_map)} maps; {len(records)} runs',flush=True)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    summary=summarize(records)
    payload={'source_hashes':source_hashes,'seed':SEED,'actual_api_calls':0,'case_count':len(cases),'variants':{n:asdict(VARIANTS[n]) if isinstance(VARIANTS[n],SearchConfig) else VARIANTS[n] for n in variants},
             'scope':'Shared precomputed exact collision graph; graph preprocessing separately reported. Frozen planner code is replayed, not rewritten.',
             'graph_preprocessing':graph_metadata,'summary':summary,'runs':records}
    (output/'results.json').write_text(json.dumps(finite_json(payload),indent=2,allow_nan=False)+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name,s in summary.items():print(name,json.dumps(s),flush=True)
    return payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',choices=['development','validation','test','all'],default='development')
    p.add_argument('--prompts',nargs='+',default=['standard'])
    p.add_argument('--variants',nargs='+',default=['original','wa2','pop_switch','budget_skip','confidence','focal11','focal11_goal'])
    p.add_argument('--limit',type=int)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(cached_cases(args.split,args.prompts,args.limit),args.variants,args.output)

if __name__=='__main__':main()
