"""Frozen matched benchmark: native repeated timing and separate work audit.

No API calls. Every method replays identical stored responses. Original code is
loaded unchanged; the matched run substitutes an equivalent indexed collision
primitive and disables plotting. A native-geometry baseline is also selectable.
"""
import argparse
import ast
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import math
import random
import re
import signal
import statistics
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from hybrid import ROOT,clean,portfolio
from strategic import strict_messages,decode_strict
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.hybrid_guidance import HybridWaypointPlanner,select_targets
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.utils import list_parse

spec=importlib.util.spec_from_file_location('session6_final_heap',Path(__file__).with_name('evaluate.py'))
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)
WORKSPACE=ROOT.parent


class TrialTimeout(Exception):pass
def alarm(signum,frame):raise TrialTimeout()


class Engines:
    def __init__(self):
        evaluation.replay.BACKEND='installed'
        self.Original=evaluation.replay.load_planner(WORKSPACE/'llm-astar',response='')
        self.Current=evaluation.replay.load_planner(ROOT,response='')
        path=WORKSPACE/'llm-astar/llmastar/pather/a_star/a_star.py'
        spec=importlib.util.spec_from_file_location('llmastar.pather.a_star._session6_original',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.plotting=SimpleNamespace(Plotting=evaluation.replay.OfflinePlot)
        self.PaperAStar=module.AStar
        path=ROOT/'llm_astar_ww/llmastar/pather/llm_a_star_ww/llm_a_star_ww.py'
        cls=next(x for x in ast.parse(path.read_text()).body if isinstance(x,ast.ClassDef))
        ns={'LLMAStar':self.Original,'math':math,'json':json,'heapq':__import__('heapq'),'re':re,'list_parse':list_parse}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(path),'exec'),ns)
        self.WW=ns['LLMAStarWW']


class CachedProvider:
    def __init__(self,row,coordinate=False):self.row=row;self.coordinate=coordinate
    def propose(self,query,candidates):
        row=self.row
        raw=row['response']['choices'][0]['message'].get('content') or ''
        if self.coordinate:
            from prompts import messages
            messages(query,'original')
            return {'routes':[list_parse(raw)]}
        if row.get('meta',{}).get('api_skipped'):
            raise RuntimeError('Geometry-only cached record must not be used as model advice')
        strict_messages(query,candidates,'multi_strict')
        points,meta=decode_strict(raw,candidates,'multi_strict')
        return {'routes':meta.get('routes') or [points]}


def load_responses(paths):
    rows={}
    for path in paths:
        for r in json.load(gzip.open(path,'rt'))['runs']:
            if r['case_id'] in rows:raise ValueError('Duplicate response IDs in benchmark input')
            rows[r['case_id']]=r
    return rows


def legacy(case,row,method,engines,audit=False):
    began=perf_counter();q=case['query'];graph=SegmentGridGraph(q)
    if method=='paper_astar':p=engines.PaperAStar()
    elif method=='ww':p=engines.WW()
    elif method=='robust_original':p=engines.Current(robust_search=True,track_progress=audit)
    elif method=='constant05_goal2':p=engines.Current(alpha=.5,robust_search=True,final_goal_weight=1.,track_progress=audit)
    elif method=='adaptive':p=engines.Current(adaptive_alpha=True,track_progress=audit)
    elif method=='adaptive_goal2':p=engines.Current(adaptive_alpha=True,final_goal_weight=1.,track_progress=audit)
    else:p=engines.Original()
    raw=row['response']['choices'][0]['message'].get('content') or '' if row else ''
    if method in ['original_hybrid_prompt','original_hybrid_consensus']:
        proposal=portfolio(q,graph);strict_messages(q,proposal,'multi_strict')
        points,meta=decode_strict(raw,proposal,'multi_strict')
        routes=meta.get('routes') or [points]
        selected=select_targets(routes,'consensus' if method=='original_hybrid_consensus' else 'first')
        raw='Generated Path: '+json.dumps(selected)
    if method=='original_bounds_prompt':
        from hybrid import messages
        messages(q,'bounds_original')
    p.model=evaluation.replay.OfflineModel(raw)
    if method!='original_native':
        p.cost=graph.cost;p.is_collision=graph.collision
    rebuilds=0;switches=[];previous_pop=0
    prepared=None
    if hasattr(p,'_initialize_llm_paths'):
        old_init=p._initialize_llm_paths
        def initialize():
            nonlocal prepared
            old_init();prepared=perf_counter()
        p._initialize_llm_paths=initialize
    if audit and hasattr(p,'_update_queue'):
        old=p._update_queue
        def update():
            nonlocal rebuilds,previous_pop
            rebuilds+=1
            switches.append({'pop':len(p.CLOSED),'active_pops':len(p.CLOSED)-previous_pop,'target':p.s_target})
            previous_pop=len(p.CLOSED);return old()
        p._update_queue=update
    try:
        with contextlib.redirect_stdout(io.StringIO()):r=p.searching(json.loads(json.dumps(q)))
        path=getattr(p.plot,'path',[])
        valid=bool(path) and path[0]==tuple(q['start']) and path[-1]==tuple(q['goal'])
        metrics=getattr(p,'search_metrics',{})
        finished=perf_counter()
        return dict(r,path=path,valid=valid,unique=len(set(p.CLOSED)),expanded=len(p.CLOSED),
            duplicate_pops=metrics.get('duplicate_pops',len(p.CLOSED)-len(set(p.CLOSED))),
            stale=metrics.get('stale_pops'),reopens=metrics.get('reopened_expansions',0),
            rebuilds=rebuilds if audit else None,alpha_adjustments=getattr(p,'alpha_adjustments',0),
            switches=switches,alpha_history=getattr(p,'alpha_history',[]) if audit else [],
            preprocess_seconds=prepared-began if prepared is not None else None,
            search_seconds=finished-prepared if prepared is not None else None,
            _measured_seconds=finished-began)
    except (KeyError,IndexError,ValueError,TypeError) as exc:
        return {'valid':False,'length':None,'path':[],'operation':len(getattr(p,'CLOSED',[])),
                'unique':len(set(getattr(p,'CLOSED',[]))),'storage':len(getattr(p,'g',{})),
                'error':type(exc).__name__}


def execute(case,original,hybrid,method,engines,audit=False,forced=None):
    q=case['query'];began=perf_counter()
    legacy_names=['original','original_native','paper_astar','ww','robust_original',
                  'constant05_goal2','adaptive','adaptive_goal2','original_hybrid_prompt','original_hybrid_consensus','original_bounds_prompt']
    if method in legacy_names:
        row=forced if method in ['original_hybrid_prompt','original_hybrid_consensus','original_bounds_prompt'] else original
        r=legacy(case,row,method,engines,audit)
    elif method in ['astar','wa2']:
        graph=SegmentGridGraph(q)
        r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1 if method=='astar' else 2).search(q,[],graph)
    elif method=='witness':
        graph=SegmentGridGraph(q)
        r=EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,
            fallback_engine='lean',reuse_validation=True).search(q,[],graph)
    elif method in ['cut2','cut105']:
        graph=SegmentGridGraph(q);r=CutStrategySearch(bound=2 if method=='cut2' else 1.05).search(q,None,graph)
    else:
        kwargs={};provider=CachedProvider(hybrid)
        if method=='hybrid_first':kwargs['selection']='first'
        elif method=='hybrid_quality':kwargs['weight']=1.05
        elif method=='geometry_best_quality':kwargs.update(source='geometry_best',weight=1.05);provider=None
        elif method=='geometry_consensus_quality':kwargs.update(source='geometry_consensus',weight=1.05);provider=None
        elif method=='all_endpoints_quality':kwargs.update(source='all_endpoints',weight=1.05);provider=None
        elif method=='geometry_best':kwargs['source']='geometry_best';provider=None
        elif method=='geometry_consensus':kwargs['source']='geometry_consensus';provider=None
        elif method=='all_endpoints':kwargs['source']='all_endpoints';provider=None
        elif method=='goal_only':kwargs['source']='goal_only';provider=None
        elif method=='llm_only':kwargs.update(source='llm_only',selection='first');provider=CachedProvider(original,True)
        elif method=='no_macros':kwargs['probe_budget']=0
        elif method=='no_sharing':kwargs['share_anchor']=False
        elif method=='euclidean_anchor':kwargs['heuristic']='euclidean'
        elif method=='always_hybrid':kwargs['source']='hybrid_always';provider=CachedProvider(forced)
        elif method!='hybrid':raise ValueError(method)
        r=HybridWaypointPlanner(provider=provider,**kwargs).search(q)
        if r.get('provider_error'):raise RuntimeError('Cached provider failed: '+r['provider_error'])
    seconds=r.pop('_measured_seconds',perf_counter()-began)
    path=r.pop('path',[])
    if r['valid']:
        # Correctness audit is outside native timing for every algorithm.
        graph=SegmentGridGraph(q)
        assert path and tuple(path[0])==tuple(q['start']) and tuple(path[-1])==tuple(q['goal'])
        assert all(math.isfinite(graph.cost(tuple(a),tuple(b))) for a,b in zip(path,path[1:]))
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
        assert abs(length-r['length'])<1e-7
        if method not in legacy_names:
            bound=1 if method=='astar' else 1.05 if method in ['hybrid_quality','cut105'] else 2
            assert length<=bound*case['optimal_cost']+1e-7
    r.pop('trace',None)
    r.update(seconds=seconds,cost_ratio=r['length']/case['optimal_cost'] if r['valid'] else None)
    return r,path


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--original',type=Path,nargs='+',required=True)
    p.add_argument('--hybrid',type=Path,nargs='+',required=True)
    p.add_argument('--forced',type=Path);p.add_argument('--methods',nargs='+',default=[
        'original','robust_original','astar','wa2','witness','cut2','cut105','hybrid',
        'hybrid_first','hybrid_quality','geometry_best','geometry_consensus','all_endpoints','llm_only'])
    p.add_argument('--repeats',type=int,default=5);p.add_argument('--timeout',type=float,default=3.)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--audit-only',action='store_true')
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases=json.load(gzip.open(a.cases,'rt'))
    original=load_responses(a.original);hybrid=load_responses(a.hybrid)
    forced=load_responses([a.forced]) if a.forced else {}
    assert all(c['id'] in original and c['id'] in hybrid for c in cases),'Incomplete guidance archive'
    if any(m in ['original_hybrid_prompt','original_hybrid_consensus','original_bounds_prompt','always_hybrid'] for m in a.methods):
        assert all(c['id'] in forced for c in cases),'Complete forced-prompt archive required'
    manifest=json.loads((ROOT/'experiments/results/research_session6/frozen_manifest.json').read_text())
    assert all(hashlib.sha256((WORKSPACE/f).read_bytes()).hexdigest()==h for f,h in manifest['sources'].items()),'Frozen source drift'
    (a.output/'protocol.json').write_text(json.dumps({'args':vars(a),'frozen':manifest,
        'timing':'Fresh graph, candidate and anchor per query. Cached provider reconstructs prompt and decodes actual stored output. API latency excluded from native timing. Warmup excluded, randomized method order, separate heap audit, equal per-trial timeout.'},default=str,indent=2))
    engines=Engines();rng=random.Random(611190);rows=[];paths=[]
    signal.signal(signal.SIGALRM,alarm)
    def trial(case,method,audit=False):
        tick=perf_counter();signal.setitimer(signal.ITIMER_REAL,a.timeout)
        try:return execute(case,original[case['id']],hybrid[case['id']],method,engines,audit,forced.get(case['id']))
        except TrialTimeout:return {'valid':False,'length':None,'seconds':perf_counter()-tick,
            'error':'timeout','operation':None,'unique':None,'cost_ratio':None},[]
        finally:signal.setitimer(signal.ITIMER_REAL,0)
    for ci,case in enumerate(cases):
        if not a.audit_only:
            for method in a.methods:trial(case,method)
        for rep in [-1]+([] if a.audit_only else list(range(a.repeats))):
            methods=list(a.methods);rng.shuffle(methods)
            for method in methods:
                with evaluation.heap_audit(rep==-1) as counts:r,path=trial(case,method,rep==-1)
                if rep==-1:
                    paths.append({'case_id':case['id'],'method':method,'path':path,'length':r['length'],'valid':r['valid']})
                rows.append(dict(r,case_id=case['id'],map_id=case['map_id'],family=case['family'],
                    split=case['split'],method=method,rep=rep,audit=counts if rep==-1 else None))
        if (ci+1)%10==0 or ci+1==len(cases):
            print(ci+1,'/',len(cases),'cases',flush=True)
            tmp=a.output/'checkpoint.tmp'
            with gzip.open(tmp,'wt') as f:json.dump({'runs':rows},f)
            tmp.replace(a.output/'checkpoint.json.gz')
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'runs':rows},f)
    with gzip.open(a.output/'paths.json.gz','wt') as f:json.dump(paths,f)
    (a.output/'completion.json').write_text(json.dumps({'trials':len(rows),'cases':len(cases),
        'methods':a.methods,'all_frozen_sources_match':all(hashlib.sha256((WORKSPACE/f).read_bytes()).hexdigest()==h for f,h in manifest['sources'].items())},indent=2))


if __name__=='__main__':main()
