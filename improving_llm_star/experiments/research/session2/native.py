"""Interface-to-interface timing with cached raw responses, fresh geometry, no rendering."""
import sys,json,gzip,copy,contextlib,io,argparse,random,statistics,hashlib
from pathlib import Path
from time import perf_counter,process_time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import ROOT,WORKSPACE,replay,cached_cases,finite_json
from llmastar.pather import CertifiedLLMAStar,WitnessFirstLLMAStar
from llmastar.research.geometry import IndexedGridGraph
from llmastar.research.scheduled import ScheduledCertificateSearch
from llmastar.research.incumbent import IncumbentSearch

class PublicWA2(WitnessFirstLLMAStar):
 def __init__(self,**kwargs):super().__init__(use_waypoints=False,**kwargs)
 def _make_research_planner(self):return ScheduledCertificateSearch(use_waypoints=False,direct=False)

class PublicAStar(PublicWA2):
 def _make_research_planner(self):return IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True)

MODES=['original_native','astar_public','wa2_public','old_cf_public','witness_exact_public','witness_only_public','witness_frontier_public']


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path);p.add_argument('--split',default='validation');p.add_argument('--repeats',type=int,default=7);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 if a.cases:
  with gzip.open(a.cases,'rt') as f:allcases=json.load(f)
  # Fixed one pair/quality per map, rotating quality by seed. No performance selection.
  groups={}
  for c in allcases:groups.setdefault(c['map_id'],[]).append(c)
  cases=[group[(int(mid.split('_')[-1])%4)] for mid,group in sorted(groups.items())]
 else:cases=cached_cases(a.split)[::5]
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='')
 records=[];rng=random.Random(16112026)
 def trial(mode,c):
  if mode=='original_native':planner=Original();planner.model=replay.OfflineModel(c['response'])
  elif mode=='old_cf_public':planner=CertifiedLLMAStar(waypoint_response=c['response'])
  elif mode=='astar_public':planner=PublicAStar(waypoint_response=c['response'])
  elif mode=='wa2_public':planner=PublicWA2(waypoint_response=c['response'])
  else:planner=WitnessFirstLLMAStar(waypoint_response=c['response'],use_waypoints=mode!='witness_only_public',policy='frontier' if mode=='witness_frontier_public' else 'exact')
  query=copy.deepcopy(c['query']);sink=io.StringIO();started=perf_counter();cpu=process_time();error=None
  try:
   with contextlib.redirect_stdout(sink):result=planner.searching(query)
  except (KeyError,IndexError,TypeError,ValueError) as exc:error=type(exc).__name__;result={'operation':len(planner.CLOSED),'length':None}
  seconds=perf_counter()-started;cpu_seconds=process_time()-cpu
  path=planner.plot.path if mode=='original_native' else planner.path
  # Same independent post-timer check for every variant, never timed for just one.
  g=IndexedGridGraph(c['query']);valid=not error and bool(path) and path[0]==tuple(c['query']['start']) and path[-1]==tuple(c['query']['goal']) and all(g.cost(x,y)<float('inf') for x,y in zip(path,path[1:]))
  if valid:assert abs(result['length']-sum(__import__('math').dist(x,y) for x,y in zip(path,path[1:])))<1e-8
  return dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],source=c['source'],variant=mode,seconds=seconds,cpu_seconds=cpu_seconds,valid=valid,error=error,length=result['length'] if valid else None,operation=result['operation'])
 for c in cases[:2]:
  for mode in MODES:trial(mode,c)
 for ci,c in enumerate(cases):
  for repetition in range(a.repeats):
   order=list(MODES);rng.shuffle(order)
   for mode in order:records.append(dict(trial(mode,c),repeat=repetition))
  if ci%5==0:print(ci+1,'/',len(cases),flush=True)
 summary={}
 for mode in MODES:
  med=[statistics.median(r['seconds'] for r in records if r['case_id']==c['id'] and r['variant']==mode) for c in cases]
  summary[mode]={'cases':len(cases),'mean_case_median_ms':statistics.mean(med)*1000,'median_case_median_ms':statistics.median(med)*1000,'max_case_median_ms':max(med)*1000}
 payload={'scope':'Public structured-query API, parsing/copying/geometry/certificates/search/validation included; object construction/imports/rendering/network excluded uniformly. Independent post-timer checking identical for all methods. Cached response only; native original has original collision code.',
  'case_hash':hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),
  'source_hashes':{str(p.relative_to(WORKSPACE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'llmastar/research/geometry.py',ROOT/'llmastar/research/efficient.py',ROOT/'llmastar/pather/llm_a_star/witness.py',WORKSPACE/'llm-astar'/replay.PLANNER_PATH]},
  'sampling':'one query0 fixture rotating by seed modulo4 per fresh map; or fixed query indices0,5 per cached map','actual_api_calls':0,'repeats':a.repeats,'summary':summary,'runs':records}
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json(payload),f,separators=(',',':'),allow_nan=False)
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
