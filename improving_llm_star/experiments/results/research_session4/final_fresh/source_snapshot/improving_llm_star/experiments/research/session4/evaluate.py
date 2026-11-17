"""Frozen serial cold-query evaluation; paired baselines and source ablations."""
import sys,json,gzip,random,math,statistics,argparse,hashlib,shutil,signal,contextlib,io,platform,os
from pathlib import Path
from time import perf_counter,process_time
sys.path.insert(0,str(Path(__file__).resolve().parent));from maps import ROOT
from benchmark import WORKSPACE,cached_cases,finite_json,replay,legacy_run
from strategy_controls import source_response
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.local_routes import LocalRouteProvider
from llmastar.research.strategic.providers import StaticProvider,ScriptedProvider,GeometricRouteProvider
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch,compress_collinear

class TrialTimeout(Exception):pass
def expired(signum,frame):raise TrialTimeout('uniform timeout')


def prepare(cases):
 for c in cases:
  if 'oracle_path' not in c:
   r=IncumbentSearch(use_waypoints=False,goal_weight=1,visibility_budget=0).search(c['query'],[],SegmentGridGraph(c['query']))
   c.update(oracle_path=r['path'],oracle_waypoints=compress_collinear(r['path']),optimal_cost=r['length'])
  if 'response' not in c:
   # Oracle-derived noisy guidance, explicitly synthetic. One and three strategy
   # variants share the EXACT same first candidate. No real LLM on new maps.
   response=source_response(c,'portfolio');c['portfolio']=response
   c['response']='Generated Path: '+json.dumps(response['strategies'][0]['waypoints'])
   c['source']='synthetic_imperfect_oracle_coordinates'
  from llmastar.utils import list_parse
  if 'points' not in c:c['points']=list_parse(c['response'])
  q=c['query'];g=SegmentGridGraph(q);local=random.Random(202611174+sum(map(ord,c['id'])));points=[]
  from llmastar.research.strategic.schema import parse_guidance
  parsed=parse_guidance(c['response']);n=len(parsed.strategies[0].waypoints) if parsed.strategies else 2
  while len(points)<n:
   p=local.randrange(g.x0+1,g.x1),local.randrange(g.y0+1,g.y1)
   if g.valid_point(p):points.append(p)
  c['random_response']={'strategies':[{'id':'random','waypoints':points}]}
 groups={}
 for c in cases:groups.setdefault(c['map_id'],[]).append(c)
 for group in groups.values():
  for i,c in enumerate(group):c['wrong_query_response']=group[(i+1)%len(group)]['response']
 return cases


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path);p.add_argument('--split',default='validation');p.add_argument('--prompts',nargs='+',default=['standard']);p.add_argument('--stride',type=int,default=1);p.add_argument('--repeats',type=int,default=7);p.add_argument('--timeout',type=float,default=5);p.add_argument('--bound',type=float,default=2);p.add_argument('--output',type=Path,required=True);p.add_argument('--modes',nargs='+',default=['astar','weighted','witness','witness_raw','cut_none','cut_raw','local_none','local_raw','local_portfolio','cut_oracle','cut_random','cut_wrong']);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 source_files=list((ROOT/'llmastar/research').rglob('*.py'))+list(Path(__file__).parent.glob('*.py'))+[WORKSPACE/'llm-astar'/replay.PLANNER_PATH,WORKSPACE/'llm-astar/llmastar/utils/utils.py',ROOT/'llmastar/utils/utils.py',WORKSPACE/'llm-astar/llmastar/env/search/env.py',ROOT/'llmastar/env/search/env.py']
 hashes={}
 for f in source_files:
  relative=f.relative_to(WORKSPACE);dest=a.output/'source_snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);hashes[str(relative)]=hashlib.sha256(f.read_bytes()).hexdigest()
 if a.cases:
  with gzip.open(a.cases,'rt') as f:cases=json.load(f)[::a.stride]
 else:cases=cached_cases(a.split,tuple(a.prompts))[::a.stride]
 cases=prepare(cases)
 with gzip.open(a.output/'cases.json.gz','wt') as f:json.dump(finite_json(cases),f,separators=(',',':'))
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='') if any(m.startswith('original') for m in a.modes) else None
 signal.signal(signal.SIGALRM,expired);rng=random.Random(2026111749);rows=[]
 def trial(mode,c):
  q=c['query'];provider=None
  if mode in ['cut_raw','local_raw']:provider=StaticProvider(c['response'],'cached_real' if c['source'].startswith('repository') else c['source'])
  elif mode=='cut_random':provider=StaticProvider(c['random_response'],'random')
  elif mode=='cut_wrong':provider=StaticProvider(c['wrong_query_response'],'wrong_query_same_map')
  elif mode=='cut_oracle':provider=StaticProvider({'strategies':[{'id':'oracle','waypoints':c['oracle_waypoints']}]},'oracle',parser_limits={'max_points':100000})
  elif mode=='local_none':provider=GeometricRouteProvider()
  elif mode=='local_portfolio':provider=StaticProvider(c.get('portfolio',{'strategies':[]}), 'synthetic_imperfect_oracle_portfolio',parser_limits={'max_points':100000})
  elif mode=='cut_dynamic':provider=ScriptedProvider([c['random_response'],{'strategies':[{'id':'oracle_revision','waypoints':c['oracle_waypoints']}]}],'simulated_oracle_revision',parser_limits={'max_points':100000})
  error=None;began=perf_counter();cpu=process_time();signal.setitimer(signal.ITIMER_REAL,a.timeout)
  try:
   g=SegmentGridGraph(q)
   if mode.startswith('original'):r=legacy_run(Original,c,g,native=mode=='original_native')
   elif mode in ['astar','weighted']:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1 if mode=='astar' else a.bound).search(q,[],g)
   elif mode in ['witness','witness_raw']:r=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=mode=='witness_raw',witness=True,fallback_engine='lean',reuse_validation=True).search(q,c.get('points',[]),g)
   else:
    if mode.startswith('local_'):provider=LocalRouteProvider(provider,g)
    r=CutStrategySearch(bound=a.bound,intervention='effort' if mode=='cut_dynamic' else 'blocked',max_segments=20000 if mode=='cut_oracle' else 512,seed_prefix=mode!='cut_noseed',geometry_candidates=mode!='cut_nogeometry',selection='none' if mode=='cut_octile' else 'all').search(q,provider,g)
  except TrialTimeout:error='timeout';r={'valid':False,'path':[],'length':None}
  except (KeyError,IndexError,TypeError,ValueError) as exc:error=type(exc).__name__+': '+str(exc);r={'valid':False,'path':[],'length':None}
  finally:signal.setitimer(signal.ITIMER_REAL,0)
  seconds=perf_counter()-began;cpu_seconds=process_time()-cpu;path=r.pop('path',[])
  # Same independent endpoint/edge/cost audit outside timing for EVERY method.
  valid=bool(path) and path[0]==tuple(q['start']) and path[-1]==tuple(q['goal']) and all(math.isfinite(g.cost(x,y)) for x,y in zip(path,path[1:]))
  assert valid==r['valid'],(mode,c['id'],'valid flag')
  if valid:
   cost=sum(math.dist(x,y) for x,y in zip(path,path[1:]));assert abs(cost-r['length'])<1e-7
   if not mode.startswith(('original','witness')):assert cost<=(1 if mode=='astar' else a.bound)*c['optimal_cost']+1e-7
  if mode=='witness_raw' and 'points' not in c:
   # Both Witness variants intentionally receive no extra generated fixtures in
   # this mode; synthetic raw parsing is handled by the new provider only.
   r['guidance_note']='No points field in generated case; see raw comparator.'
  return dict(r,path=path,case_id=c['id'],map_id=c['map_id'],family=c['family'],source=c['source'],mode=mode,seconds=seconds,cpu_seconds=cpu_seconds,error=error,optimal_cost=c['optimal_cost'],reachable=c['optimal_cost'] is not None)
 # Two predetermined warmup cases, excluded from all summary statistics.
 for c in cases[:2]:
  for mode in a.modes:trial(mode,c)
 journal=(a.output/'journal.jsonl').open('w')
 for ci,c in enumerate(cases):
  for repeat in range(a.repeats):
   order=list(a.modes);rng.shuffle(order)
   for mode in order:
    r=dict(trial(mode,c),repeat=repeat);rows.append(r);journal.write(json.dumps(finite_json(r),separators=(',',':'))+'\n');journal.flush()
  if ci%5==0:print(ci+1,'/',len(cases),flush=True)
 journal.close()
 for name,h in hashes.items():assert hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()==h,('Source changed during benchmark',name)
 data={'scope':'Serial randomized order, two fixed warmup cases excluded; cold geometry and all advice parsing/local repair/certificates/search included. Oracle/synthetic RESPONSE GENERATION unavailable and excluded. No API/model/network calls. Native original uses frozen collision code; matched original changes geometry only. Repeated timings are not extra observations.','actual_api_calls':0,'modes':a.modes,'args':vars(a),'source_hashes':hashes,'case_hash':hashlib.sha256(json.dumps(finite_json(cases),sort_keys=True).encode()).hexdigest(),'environment':{'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'load_average':os.getloadavg()},'runs':rows}
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json(data),f,separators=(',',':'),default=str)
 # Canonical compressed artifact retained; journal only serves interrupted runs.
 journal_path=a.output/'journal.jsonl';journal_path.unlink()
 print('Completed',len(rows),'trials; source hashes unchanged',flush=True)
if __name__=='__main__':main()
