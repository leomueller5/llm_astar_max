"""Matched prompt × original-related search mechanisms, entirely cached replay."""
import sys,argparse,json,gzip,math,random,statistics,hashlib,shutil,signal
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from benchmark import ROOT,WORKSPACE,finite_json,legacy_run,replay
from prompts import decode,feedback_for
from llmastar.utils import list_parse
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.real_guidance.lineage import PathConsistentSearch
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.strategic.local_routes import LocalRouteProvider
CONFIGS={'neighbor':dict(progress='global_neighbor'),'popped':dict(progress='global_pop'),
 'lineage':dict(progress='lineage'),'lineage_trust':dict(score='normalized',trust=True),
 'lineage_budget':dict(path_budget=True),'lineage_bounded':dict(score='bounded'),
 'lineage_full':dict(score='bounded',trust=True,path_budget=True,skip_unverified=True),
 'none':dict(score='bounded',guidance=False)}
class Timeout(Exception):pass
def timeout(signum,frame):raise Timeout()


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--responses',type=Path,nargs='+',required=True);p.add_argument('--repeats',type=int,default=3);p.add_argument('--methods',nargs='+',default=['original','neighbor','popped','lineage','lineage_trust','lineage_budget','lineage_bounded','lineage_full','none','astar','wa2','witness','cut_none','cut_real']);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);manifest={}
 sources=list((ROOT/'llmastar/research/real_guidance').glob('*.py'))+list(Path(__file__).parent.glob('*.py'))+[WORKSPACE/'llm-astar'/replay.PLANNER_PATH]
 for f in sources:
  dest=a.output/'sources'/f.relative_to(WORKSPACE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);manifest[str(f.relative_to(WORKSPACE))]=hashlib.sha256(f.read_bytes()).hexdigest()
 with gzip.open(a.cases,'rt') as f:cases={c['id']:c for c in json.load(f)}
 responses=[]
 for file in a.responses:
  with gzip.open(file,'rt') as f:
   for row in json.load(f)['runs']:
    if row.get('response'):responses.append(row)
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='');rng=random.Random(202611185);runs=[];qualities=[]
 signal.signal(signal.SIGALRM,timeout)
 for ri,response in enumerate(responses):
  c=cases[response['case_id']];q=c['query'];raw=response['response']['choices'][0]['message'].get('content') or '';version=response['prompt'];pts,meta=decode(raw,q,version)
  # Coordinates use the SAME legacy-decoded list that frozen original sees.
  if version in ['original','coords_v1']:pts=list_parse(raw);original_raw=raw
  else:original_raw='Generated Path: '+json.dumps(pts)
  basegraph=SegmentGridGraph(q);nonend=[p for p in pts if tuple(p) not in [tuple(q['start']),tuple(q['goal'])]]
  qualities.append(dict(case_id=c['id'],prompt=version,feedback=response.get('feedback','none'),points=len(pts),invalid_points=sum(not basegraph.valid_point(tuple(p)) for p in pts),valid_intermediate=sum(basegraph.valid_point(tuple(p)) for p in nonend),contradiction=feedback_for(q,pts),**meta))
  for rep in range(a.repeats):
   order=list(a.methods);rng.shuffle(order)
   for method in order:
    began=perf_counter();g=SegmentGridGraph(q);error=None
    signal.setitimer(signal.ITIMER_REAL,3.)
    try:
     if method=='original':r=legacy_run(Original,dict(c,response=original_raw),g)
     elif method in CONFIGS:r=PathConsistentSearch(**CONFIGS[method]).search(q,pts,g)
     elif method in ['astar','wa2']:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1 if method=='astar' else 2).search(q,[],g)
     elif method=='witness':r=EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,fallback_engine='lean',reuse_validation=True).search(q,[],g)
     elif method in ['cut_none','cut_real']:
      provider=LocalRouteProvider(StaticProvider({'strategies':[{'id':'actual_llm','waypoints':pts}]},'real_'+version),g) if method=='cut_real' else None
      r=CutStrategySearch(bound=2).search(q,provider,g)
     else:raise ValueError(method)
    except Timeout:r={'valid':False,'length':None,'path':[]};error='timeout'
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    seconds=perf_counter()-began;path=r.pop('path',[])
    if r['valid']:
     assert all(math.isfinite(g.cost(tuple(x),tuple(y))) for x,y in zip(path,path[1:]));assert abs(r['length']-sum(math.dist(x,y) for x,y in zip(path,path[1:])))<1e-7
     if method in ['lineage_bounded','lineage_full','none','astar','wa2','cut_none','cut_real']:assert r['length']<=(1 if method=='astar' else 2)*c['optimal_cost']+1e-7
    r.pop('trace',None);runs.append(dict(r,case_id=c['id'],map_id=c['map_id'],family=c['family'],method=method,prompt=version,feedback=response.get('feedback','none'),request_id=response['request_id'],rep=rep,seconds=seconds,error=error,optimal_cost=c['optimal_cost']))
  if ri%10==0:print(ri+1,'/',len(responses),'responses',flush=True)
 for name,h in manifest.items():assert hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()==h
 summary={}
 for method,prompt,feedback in sorted({(r['method'],r['prompt'],r['feedback']) for r in runs}):
  rr=[r for r in runs if (r['method'],r['prompt'],r['feedback'])==(method,prompt,feedback)];one=[r for r in rr if r['rep']==0];times=[statistics.median(x['seconds'] for x in rr if x['case_id']==r['case_id'] and x['request_id']==r['request_id']) for r in one];valid=[r for r in one if r['valid']]
  summary[f'{prompt}/{feedback}/{method}']={'observations':len(one),'valid':len(valid),'mean_ms':statistics.mean(times)*1000,'mean_unique':statistics.mean(r.get('unique_total',r.get('unique',0)) for r in one),'mean_expanded':statistics.mean(r.get('expanded',0) for r in one),'mean_pops':statistics.mean(r.get('total_heap_pops',r.get('operation',0)) for r in one),'mean_rebuilds':statistics.mean(r.get('rebuilds',0) or 0 for r in one),'gm_cost_ratio':math.exp(statistics.mean(math.log(r['length']/r['optimal_cost']) for r in valid)) if valid else None,'max_cost_ratio':max((r['length']/r['optimal_cost'] for r in valid),default=None)}
 data={'scope':'Same exact live-generated response per prompt reused by all algorithms. All indexed geometry fresh and same. Frozen original code unchanged except exact geometry replacement. Prompt-only and algorithm-only factorial controls. All measured times are offline cold replay; generation/API excluded and reported separately in authoritative ledger.','sources':manifest,'summary':summary,'quality':qualities,'runs':runs}
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json(data),f,separators=(',',':'))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('Completed',len(runs),'search trials')
if __name__=='__main__':main()
