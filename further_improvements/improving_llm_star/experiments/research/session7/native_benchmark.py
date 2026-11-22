"""Frozen Session7 replay: all computational planning costs, separate heap audit.

No network. Cached advice is incoming data. Prompt/image construction and actual
API-inclusive latency are measured separately, never silently treated as free on
first-use claims. Each planning trial constructs fresh query-local preprocessing.
"""
import argparse,contextlib,importlib.util,json,math,random,signal,statistics,sys,hashlib
from pathlib import Path
from time import perf_counter
from common import ROOT,WORKSPACE,RESULTS,read_cases,dump
from llmastar.research.spatial_planner import SpatialResidualAStar
from llmastar.research.spatial_guidance import SpatialSearch,RegionField
from llmastar.research.hybrid_guidance import HybridWaypointPlanner
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.strategic.cut_search import CutStrategySearch

spec=importlib.util.spec_from_file_location('session7_frozen_baselines',ROOT/'experiments/research/session6/final_benchmark.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluate import permuted
from prompts_spatial import decode

ALPHA=.22640953779865894
TEXT_ALPHA=.07056526284991615
METHODS=['original','robust_original','astar_octile','astar_cut','wa_octile2','matched_zero','matched_uniform105','optimized_uniform105','cut105','cut2','witness','vm_geo2','vm_geo105','vm_hybrid2','vm_strict2','rh_image105','rh_image2','rh_text105','rh_text_raw105','rh_raw105','rh_icl105','rh_shuffled105','rh_scalar105','rh_geometry105','rh_macro105']

class Timeout(Exception):pass
def alarm(signum,frame):raise Timeout()

@contextlib.contextmanager
def deadline(seconds):
    previous=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

@contextlib.contextmanager
def heap_audit(enabled):
    import heapq
    original=(heapq.heappush,heapq.heappop,heapq.heapify);counts={'push':0,'pop':0,'heapify':0};labels=[]
    if enabled:
        def push(q,item):counts['push']+=1;return original[0](q,item)
        def pop(q):
            counts['pop']+=1;item=original[1](q)
            if isinstance(item,tuple) and item and hasattr(item[-1],'node') and hasattr(item[-1],'g'):labels.append((item[-1].node,item[-1].g))
            return item
        def heapify(q):counts['heapify']+=1;return original[2](q)
        heapq.heappush,heapq.heappop,heapq.heapify=push,pop,heapify
    try:yield counts,labels
    finally:heapq.heappush,heapq.heappop,heapq.heapify=original

def verify_sources(manifest):
    bad=[name for name,expected in manifest['sources'].items() if hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()!=expected]
    if bad:raise RuntimeError('Frozen source changes: '+','.join(bad))

def load_baselines(path):
    return {(r['case_id'],r['baseline']):r for r in read_cases(path)['runs']}
def load_costs(path):return {(r['case_id'],r['representation']):r for r in read_cases(path)['runs']}

class LiteralVMCachedProvider(legacy.CachedProvider):
    def propose(self,query,candidates):
        if self.row.get('meta',{}).get('strict_provider_error'):raise RuntimeError('frozen_strict_schema_provider_limit')
        return super().propose(query,candidates)

class ShuffledVMCachedProvider(legacy.CachedProvider):
    def __init__(self,row,seed):super().__init__(row);self.seed=seed
    def propose(self,query,candidates):
        proposal=super().propose(query,candidates);fixed={tuple(query['start']),tuple(query['goal'])};points=list(dict.fromkeys(tuple(p) for p in candidates['points'].values() if tuple(p) not in fixed));shuffled=list(points);random.Random(self.seed).shuffle(shuffled);mapping=dict(zip(points,shuffled))
        return {'routes':[[mapping.get(tuple(p),tuple(p)) for p in route] for route in proposal['routes']]}

class AbstainingProvider:
    def propose(self,query,candidates):return {'routes':[]}

class CachedCostProvider:
    def __init__(self,q,row,transform=None,seed=0):self.q=q;self.row=row;self.transform=transform;self.seed=seed
    def predict(self,q,regions):
        if q!=self.q:raise ValueError('Cached guidance query mismatch')
        raw=self.row['response']['choices'][0]['message'].get('content') or ''
        if self.transform is None:return raw
        field,_=decode(q,raw,4,'cost')
        if self.transform=='shuffle':field=permuted(field,f'{self.row["case_id"]}:{self.seed}')
        elif self.transform=='scalar':
            means=statistics.mean(v[0]*v[2] for v in field.values.values()) if field.values else 0.
            field.update([{'region_id':r['id'],'detour':means,'priority':.5,'confidence':1.} for r in field.regions])
        return {'predictions':[{'region_id':k,'detour':v[0],'priority':v[1],'confidence':v[2]} for k,v in field.values.items()]}

def execute(c,method,engines,baselines,costs,icl,audit=False,seed=0):
    q=c['query'];cid=c['id']
    if method=='original_bounds':return legacy.legacy(c,baselines[cid,'bounds'],'original',engines,audit)
    if method in ['original_goal_only','robust_goal_only']:
        neutral={'response':{'choices':[{'message':{'content':'Generated Path: '+json.dumps([q['start'],q['goal']])}}]}}
        return legacy.legacy(c,neutral,'original' if method=='original_goal_only' else 'robust_original',engines,audit)
    if method in ['original','robust_original','paper_astar']:
        result=legacy.legacy(c,baselines.get((cid,'original')),method,engines,audit)
        if method=='paper_astar':
            from correct_paper_orientation import normalize
            result=normalize(result,q)
        return result
    if method in ['astar_octile','astar_cut','wa_octile2']:
        return SpatialSearch(mode='weighted',bound=2. if method=='wa_octile2' else 1.,base_weight=2. if method=='wa_octile2' else 1.,heuristic='cut' if method=='astar_cut' else 'octile').search(q,record_trace=audit)
    if method in ['matched_zero','matched_uniform105']:
        return SpatialResidualAStar(source='none',bound=1.05,base_weight=1. if method=='matched_zero' else 1.05,side=4).search(q,record_trace=audit)
    if method=='optimized_uniform105':return SpatialSearch(mode='weighted',bound=1.05,base_weight=1.05).search(q,record_trace=audit)
    if method=='matched_uniform2':return SpatialResidualAStar(source='none',bound=2.,base_weight=2.,side=4).search(q,record_trace=audit)
    if method in ['rh_macro_zero105','rh_macro_uniform105']:
        return SpatialResidualAStar(source='none',bound=1.05,base_weight=1. if method=='rh_macro_zero105' else 1.05,side=4,macros=True).search(q,record_trace=audit)
    if method in ['cut105','cut2']:
        return CutStrategySearch(bound=1.05 if method=='cut105' else 2.).search(q,None,SegmentGridGraph(q))
    if method=='witness':return EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,fallback_engine='lean',reuse_validation=True).search(q,[],SegmentGridGraph(q))
    if method in ['vm_consensus2','vm_abstain2','vm_shuffled2']:
        provider=AbstainingProvider() if method=='vm_abstain2' else ShuffledVMCachedProvider(baselines[cid,'vm'],f's7vmshuffle:{cid}:{seed}') if method=='vm_shuffled2' else None
        return HybridWaypointPlanner(provider=provider,source='geometry_consensus' if method=='vm_consensus2' else 'hybrid',weight=2.).search(q,record_trace=audit)
    if method in ['vm_geo2','vm_geo105','vm_hybrid2','vm_strict2']:
        provider=(LiteralVMCachedProvider(baselines[cid,'vm']) if method=='vm_strict2' else legacy.CachedProvider(baselines[cid,'vm'])) if method in ['vm_hybrid2','vm_strict2'] else None
        return HybridWaypointPlanner(provider=provider,source='hybrid' if provider else 'all_endpoints',weight=1.05 if method=='vm_geo105' else 2.).search(q,record_trace=audit)
    rep='structured' if method in ['rh_text105','rh_text_raw105'] else 'image';row=icl[cid,'image'] if method=='rh_icl105' else costs[cid,rep]
    provider=CachedCostProvider(q,row,'shuffle' if method=='rh_shuffled105' else 'scalar' if method=='rh_scalar105' else None,seed)
    kwargs={'provider':provider,'bound':2. if method=='rh_image2' else 1.05,'alpha':1. if method in ['rh_raw105','rh_text_raw105'] else TEXT_ALPHA if rep=='structured' else ALPHA,'side':4,'source':'geometry_midpoint' if method=='rh_geometry105' else 'model','macros':method=='rh_macro105'}
    return SpatialResidualAStar(**kwargs).search(q,record_trace=audit)

METRICS=['operation','storage','length','valid','expanded','unique','stale','duplicates','duplicate_pops','reopens','rebuilds','macro_probes','macro_accepted','provider_calls','provider_seconds','provider_error','prediction_parse_error','rejected_predictions','prediction_coverage','global_alpha','grid_seconds','region_seconds','prediction_parse_seconds','candidate_seconds','preprocess_seconds','search_seconds','total_seconds','compute_excluding_provider_seconds','heuristic_seconds','guidance_seconds','total_heap_pops','total_heap_pushes']

def classify_labels(labels,trace):
    if not trace:return None
    index=0;closed={};duplicate=stale=0
    for node,g in labels:
        if index<len(trace) and tuple(trace[index]['node'])==tuple(node) and trace[index]['g']==g:
            closed[tuple(node)]=g;index+=1
        else:
            stale+=1
            if tuple(node) in closed and g>=closed[tuple(node)]-1e-12:duplicate+=1
    return {'label_heap_pops':len(labels),'matched_expansions':index,'trace_expansions':len(trace),'stale_label_pops':stale,'already_closed_label_pops':duplicate,'trace_fully_matched':index==len(trace)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--baselines',required=True);p.add_argument('--costs',required=True);p.add_argument('--icl',required=True);p.add_argument('--methods',nargs='+',default=METHODS);p.add_argument('--repeats',type=int,default=5);p.add_argument('--timeout',type=float,default=5.);p.add_argument('--shuffle-seeds',type=int,default=5);p.add_argument('--output',required=True);p.add_argument('--fixture-smoke',action='store_true');p.add_argument('--skip-warmup',action='store_true',help='Counts-only runs, requires repeats0');a=p.parse_args();out=Path(a.output)
    if a.skip_warmup and a.repeats:raise ValueError('Timing runs require warmup')
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);manifest=json.loads((RESULTS/'frozen_manifest.json').read_text());verify_sources(manifest)
    cases=read_cases(a.cases);baseline=load_baselines(a.baselines);costs=load_costs(a.costs);icl=load_costs(a.icl);engines=legacy.Engines();rows=[];paths=[];traces=[]
    dump(out/'protocol.json',dict(cases=a.cases,methods=a.methods,repeats=a.repeats,timeout=a.timeout,shuffle_seeds=a.shuffle_seeds,scope='Offline cached-guidance computational planning, fresh preprocessing every trial; separate first-use prompt/image and API-inclusive measurements required. Five shuffle seeds are averaged within query, not independent map samples.',fixture_smoke=a.fixture_smoke,skip_warmup=a.skip_warmup,manifest_sha256=hashlib.sha256((RESULTS/'frozen_manifest.json').read_bytes()).hexdigest()))
    for ci,c in enumerate(cases):
        tasks=[(m,seed) for m in a.methods for seed in range(a.shuffle_seeds if m in ['rh_shuffled105','vm_shuffled2'] else 1)];random.Random('s7native:'+c['id']).shuffle(tasks)
        for method,seed in tasks:
            # One method-local warmup, excluded from all timing summaries.
            try:
                if not a.skip_warmup:
                    with deadline(a.timeout):execute(c,method,engines,baseline,costs,icl,False,seed)
            except (Timeout,legacy.TrialTimeout):pass
            for rep in [-1]+list(range(a.repeats)):
                tick=perf_counter();r=None;error=None;counts={'push':None,'pop':None,'heapify':None};labels=[]
                try:
                    with deadline(a.timeout),heap_audit(rep==-1) as (counter,events):
                        r=execute(c,method,engines,baseline,costs,icl,rep==-1,seed)
                    if rep==-1:counts=counter;labels=events
                except (Timeout,legacy.TrialTimeout):error='timeout'
                except Exception as exc:
                    dump(out/'failure.json',{'case':c['id'],'method':method,'kind':type(exc).__name__});raise
                seconds=perf_counter()-tick
                row=dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],size=max(c['query']['range_x'][1],c['query']['range_y'][1]),stratum='large' if c['id'].startswith('s7_164') or c['id'].startswith('s7_165') else 'primary',method=method,seed=seed,rep=rep,seconds=seconds,error=error,actual_api_calls=0)
                if r is not None:
                    row.update({k:r.get(k) for k in METRICS});row['cost_ratio']=r['length']/c['optimal_cost'] if r.get('valid') else None
                    if r.get('valid'):
                        if method.startswith('rh_') and method!='rh_image2':assert row['cost_ratio']<=1.05+1e-7
                        elif method not in ['original','robust_original','original_bounds','original_goal_only','robust_goal_only']:assert row['cost_ratio']<=2.+1e-7
                    if rep==-1:
                        row['audit']=counts;row['label_pop_classification']=classify_labels(labels,r.get('trace',[]))
                        paths.append({'case_id':c['id'],'method':method,'seed':seed,'valid':r.get('valid',False),'length':r.get('length'),'path':r.get('path',[])})
                        if method in ['rh_image105','astar_cut','vm_geo105']:
                            traces.append({'case_id':c['id'],'method':method,'trace':r.get('trace',[]),'switches':r.get('switches',[]),'alpha_by_region':r.get('alpha_by_region')})
                else:row.update(valid=False,cost_ratio=None,audit=counts if rep==-1 else None)
                rows.append(row)
        dump(out/'checkpoint.json.gz',{'runs':rows});dump(out/'paths.json.gz',paths);dump(out/'traces.json.gz',traces);print(ci+1,'/',len(cases),c['id'],'native complete',flush=True)
    verify_sources(manifest);dump(out/'results.json.gz',{'runs':rows});dump(out/'completion.json',{'cases':len(cases),'records':len(rows),'frozen_sources_match':True,'input_query_sha256':hashlib.sha256(json.dumps([c['query'] for c in cases],sort_keys=True).encode()).hexdigest()})
if __name__=='__main__':main()
