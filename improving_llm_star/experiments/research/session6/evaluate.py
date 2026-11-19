"""Offline replay: matched fresh geometry, native timing and separate heap audit."""
import argparse
import contextlib
import gzip
import hashlib
import heapq
import io
import json
import math
import random
import statistics
import signal
import shutil
import sys
from pathlib import Path
from time import perf_counter

from hybrid import ROOT,portfolio,clean,assess
sys.path.insert(0,str(ROOT/'experiments/research'))
from benchmark import replay,WORKSPACE,finite_json,legacy_run
from direct import macro_class
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.strategic.local_routes import LocalRouteProvider
from llmastar.research.macro_guidance import MacroGuidedSearch


class TrialTimeout(Exception):
    pass


def timeout_handler(signum,frame):
    raise TrialTimeout()


@contextlib.contextmanager
def heap_audit(enabled):
    counts={'push':0,'pop':0,'heapify':0}
    original=heapq.heappush,heapq.heappop,heapq.heapify
    if enabled:
        def push(q,v):counts['push']+=1;return original[0](q,v)
        def pop(q):counts['pop']+=1;return original[1](q)
        def heapify(q):counts['heapify']+=1;return original[2](q)
        heapq.heappush,heapq.heappop,heapq.heapify=push,pop,heapify
    try:
        yield counts
    finally:
        heapq.heappush,heapq.heappop,heapq.heapify=original


def execute(case,points,method,Original,meta=None,prompt=None):
    tick=perf_counter();q=case['query'];graph=SegmentGridGraph(q)
    prep=0.;geo_pops=geo_pushes=0
    if prompt in ['rank','repair','rank_strict','repair_strict','multi_strict','fork'] and not method.endswith(('_geometry','_none')) and method not in ['astar','wa2','witness','macro_all','macro_cut_all','cut_portfolio']:
        proposal=portfolio(q,graph);prep=proposal['seconds']
        geo_pops=proposal['heap_pops'];geo_pushes=proposal['heap_pushes']
    if method.endswith('_geometry'):
        proposal=portfolio(q,graph);points=proposal['geometry_best'];prep=proposal['seconds']
        geo_pops=proposal['heap_pops'];geo_pushes=proposal['heap_pushes']
        meta={'routes':[r['route'] for r in proposal['candidates'][:3]]}
    elif method.endswith('_none'):
        points=[];meta={}
    name=method.removesuffix('_geometry').removesuffix('_none')
    raw='Generated Path: '+json.dumps(points)
    if name=='original':
        r=legacy_run(Original,dict(case,response=raw),graph)
    elif name in ['direct_macro','direct_confidence']:
        planner=macro_class(Original)();planner.model=replay.OfflineModel(raw)
        planner.set_macro(graph,confidence=(meta or {}).get('confidence',1.) if name=='direct_confidence' else None)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                result=planner.searching(json.loads(json.dumps(q)))
                path=planner.plot.path
                r={'path':path,'valid':bool(path),'length':result['length'],
                    'operation':result['operation'],'expanded':len(planner.CLOSED),
                    'unique':len(set(planner.CLOSED)),'duplicates':len(planner.CLOSED)-len(set(planner.CLOSED)),
                    'storage':result['storage'],'rebuilds':None,'preprocess_seconds':0.,
                    'macro_probes':planner.macro_probes,'macro_accepted':planner.macro_accepted}
            except (KeyError,IndexError):
                r={'valid':False,'length':None,'path':[],'operation':len(planner.CLOSED),
                   'unique':len(set(planner.CLOSED)),'expanded':len(planner.CLOSED)}
    elif name in ['astar','wa2']:
        r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1 if name=='astar' else 2).search(q,[],graph)
    elif name=='witness':
        r=EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,
            fallback_engine='lean',reuse_validation=True).search(q,[],graph)
    elif name in ['cut','cut_raw','cut105','cut105_raw','cut_multi','cut_portfolio']:
        routes=(meta or {}).get('routes') or [points]
        if name=='cut_portfolio':
            proposal=portfolio(q,graph);prep=proposal['seconds'];routes=[r['route'] for r in proposal['candidates'][:4]]
        provider=StaticProvider({'strategies':[{'id':'proposal'+str(i),'waypoints':route} for i,route in enumerate(routes[:4] if name in ['cut_multi','cut_portfolio'] else [points])]},'hybrid') if points or name in ['cut_multi','cut_portfolio'] else None
        if provider is not None and name in ['cut','cut105']:
            provider=LocalRouteProvider(provider,graph)
        r=CutStrategySearch(bound=1.05 if name.startswith('cut105') else 2).search(q,provider,graph)
    elif name in ['macro','seed_macro','seed_only','macro_all','macro_cut','seed_cut','macro_cut_all','macro_portfolio','macro_regret','macro_regret_all']:
        if name in ['macro_all','macro_cut_all','macro_regret_all']:
            from hybrid import endpoints
            candidates=list(endpoints(q).values());s,t=tuple(q['start']),tuple(q['goal'])
            points=sorted(candidates,key=lambda p:(math.dist(s,p)+math.dist(p,t),p))
        if name=='macro_portfolio':
            routes=(meta or {}).get('routes') or [points]
            points=[route[i] for i in range(max(map(len,routes),default=0)) for route in routes if i<len(route)]
        r=MacroGuidedSearch(initial_chain=name in ['seed_macro','seed_only','seed_cut'],
            dynamic=name!='seed_only',heuristic='cut' if name in ['macro_cut','seed_cut','macro_cut_all','macro_portfolio','macro_regret','macro_regret_all'] else 'euclidean',
            target_order='regret' if name in ['macro_regret','macro_regret_all'] else 'given').search(q,points,graph)
    else:
        raise ValueError(method)
    elapsed=perf_counter()-tick
    path=r.pop('path',[])
    if r['valid']:
        assert path and tuple(path[0])==tuple(q['start']) and tuple(path[-1])==tuple(q['goal'])
        assert all(math.isfinite(graph.cost(tuple(a),tuple(b))) for a,b in zip(path,path[1:]))
        cost=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
        assert abs(cost-r['length'])<1e-7
        if name in ['macro','seed_macro','seed_only','macro_all','macro_cut','seed_cut','cut','cut_raw','cut105','cut105_raw','cut_multi','wa2','astar']:
            assert cost<=(1 if name=='astar' else 1.05 if name.startswith('cut105') else 2)*case['optimal_cost']+1e-7
    r.pop('trace',None);r.pop('events',None)
    r.update(seconds=elapsed,geometry_seconds=prep,geometry_heap_pops=geo_pops,geometry_heap_pushes=geo_pushes)
    return r


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,nargs='+',required=True)
    p.add_argument('--exclude-short-original',action='store_true')
    p.add_argument('--methods',nargs='+',default=['original','original_none','original_geometry',
        'astar','wa2','witness','cut_none','cut','macro_none','macro_geometry','macro','macro_all',
        'seed_only','seed_macro','direct_macro','direct_macro_none','direct_confidence'])
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=float,default=3.)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    a.output.mkdir(parents=True)
    sources=list(Path(__file__).parent.glob('*.py'))+[ROOT/'llmastar/research/macro_guidance.py']
    manifest={}
    for source in sources:
        dest=a.output/'sources'/source.relative_to(WORKSPACE)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        manifest[str(source.relative_to(WORKSPACE))]=hashlib.sha256(source.read_bytes()).hexdigest()
    (a.output/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    responses=[]
    for f in a.responses:
        for row in json.load(gzip.open(f,'rt'))['runs']:
            if a.exclude_short_original and row['prompt']=='original' and 'prompt_pilot' in str(f):
                continue
            responses.append(row)
    replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='')
    rng=random.Random(202611186);runs=[];qualities=[]
    signal.signal(signal.SIGALRM,timeout_handler)
    def trial(case,points,method,meta,prompt):
        began=perf_counter();signal.setitimer(signal.ITIMER_REAL,a.timeout)
        try:
            return execute(case,points,method,Original,meta,prompt)
        except TrialTimeout:
            return {'valid':False,'length':None,'operation':None,'unique':None,
                    'seconds':perf_counter()-began,'error':'equal_trial_timeout'}
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
    for response in responses:
        case=cases[response['case_id']];points=response['points'];meta=response['meta']
        graph=SegmentGridGraph(case['query']);route=clean(case['query'],points,graph)
        quality=assess(case['query'],route,graph)
        qualities.append({'case_id':case['id'],'prompt':response['prompt'],
            'failed_links':quality['failed_links'],'targets':len(route)-2,
            'finish_reason':response['response']['choices'][0].get('finish_reason'),**meta})
        # Warmups and exact heap auditing are excluded from native timings.
        for method in a.methods:
            trial(case,points,method,meta,response['prompt'])
        for rep in [-1]+list(range(a.repeats)):
            methods=list(a.methods);rng.shuffle(methods)
            for method in methods:
                with heap_audit(rep==-1) as counts:
                    r=trial(case,points,method,meta,response['prompt'])
                runs.append(dict(r,case_id=case['id'],map_id=case['map_id'],family=case['family'],
                    prompt=response['prompt'],method=method,rep=rep,optimal_cost=case['optimal_cost'],
                    audit=counts if rep==-1 else None))
        print(case['id'],response['prompt'],'completed',flush=True)
        with gzip.open(a.output/'checkpoint.json.gz','wt') as f:
            json.dump(finite_json({'runs':runs,'quality':qualities}),f)
    summary={}
    for prompt,method in sorted({(r['prompt'],r['method']) for r in runs}):
        rr=[r for r in runs if r['prompt']==prompt and r['method']==method]
        one=[r for r in rr if r['rep']==-1];valid=[r for r in one if r['valid']]
        times=[statistics.median(r['seconds'] for r in rr if r['case_id']==c['case_id'] and r['rep']>=0) for c in one]
        summary[prompt+'/'+method]={'cases':len(one),'valid':len(valid),
            'mean_ms':1000*statistics.mean(times),'median_ms':1000*statistics.median(times),
            'mean_unique':statistics.mean(r.get('unique_total',r.get('unique',0)) or 0 for r in one),
            'timeouts':sum(r.get('error')=='equal_trial_timeout' for r in one),
            'expansion_scope':'Timeout expansions unknown and excluded from success-only mean',
            'mean_unique_success':statistics.mean(r.get('unique_total',r.get('unique',0)) or 0 for r in valid) if valid else None,
            'mean_pops':statistics.mean(r['audit']['pop'] for r in one),
            'mean_pushes':statistics.mean(r['audit']['push'] for r in one),
            'mean_queue_operations':statistics.mean(r['audit']['pop']+r['audit']['push'] for r in one),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['length']/r['optimal_cost']) for r in valid)) if valid else None,
            'max_cost_ratio':max((r['length']/r['optimal_cost'] for r in valid),default=None),
            'mean_macro_probes':statistics.mean(r.get('macro_probes',0) for r in one),
            'mean_geometry_ms':statistics.mean(r.get('geometry_seconds',0)*1000 for r in one)}
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with gzip.open(a.output/'results.json.gz','wt') as f:
        json.dump(finite_json({'runs':runs,'quality':qualities,'summary':summary,
            'timing':'Warmups excluded. Fresh geometry each run. Offline replay; API latency excluded. Heap counts in separate untimed audit.'}),f)
    # Snapshots remain reproducible even if another independent prototype is
    # developed while this loaded process runs. Flag source drift explicitly.
    drift=[name for name,h in manifest.items() if hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()!=h]
    (a.output/'source_drift.json').write_text(json.dumps({'modified_during_execution':drift},indent=2))


if __name__=='__main__':
    main()
