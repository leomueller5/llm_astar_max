"""Post-freeze diagnostics: source quality and local-refinement ablations.

No algorithm parameters selected here. Same frozen engine, fixtures and budgets;
these secondary comparisons cannot be used to tune the opened fresh set.
"""
import sys,json,gzip,random,math,hashlib,shutil,argparse,statistics
from pathlib import Path
from time import perf_counter,process_time
sys.path.insert(0,str(Path(__file__).resolve().parent));from maps import ROOT
from benchmark import WORKSPACE,finite_json
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.local_routes import LocalRouteProvider
from llmastar.research.strategic.providers import StaticProvider,GeometricRouteProvider
from llmastar.research.strategic.schema import parse_guidance
from llmastar.research.geometry import SegmentGridGraph


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--repeats',type=int,default=7);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);hashes={}
 for f in list((ROOT/'llmastar/research').rglob('*.py'))+[Path(__file__)]:
  relative=f.relative_to(WORKSPACE);dest=a.output/'source_snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);hashes[str(relative)]=hashlib.sha256(f.read_bytes()).hexdigest()
 with gzip.open(a.cases,'rt') as f:cases=json.load(f)
 for c in cases:
  parsed=parse_guidance(c['response']);points=list(parsed.strategies[0].waypoints) if parsed.strategies else []
  rng=random.Random(202611174+sum(map(ord,c['id'])));rng.shuffle(points);c['shuffled_response']={'strategies':[{'id':'shuffled','waypoints':points}]}
 modes=['local_raw','local_none','local_random','local_wrong','local_shuffled','local_norepair','local_noshortcut'];rows=[];rng=random.Random(2026111745)
 def trial(c,mode):
  q=c['query'];raw=c['random_response'] if mode=='local_random' else c['wrong_query_response'] if mode=='local_wrong' else c['shuffled_response'] if mode=='local_shuffled' else c['response']
  began=perf_counter();cpu=process_time();graph=SegmentGridGraph(q)
  underlying=GeometricRouteProvider() if mode=='local_none' else StaticProvider(raw,source=mode)
  provider=LocalRouteProvider(underlying,graph,total_expansions=0 if mode=='local_norepair' else 128,shortcut=mode!='local_noshortcut')
  r=CutStrategySearch(bound=2).search(q,provider,graph);elapsed=perf_counter()-began;cpu_seconds=process_time()-cpu
  path=r.pop('path');assert not r['valid'] or all(math.isfinite(graph.cost(x,y)) for x,y in zip(path,path[1:]))
  if r['valid']:assert r['length']<=2*c['optimal_cost']+1e-7
  return dict(r,case_id=c['id'],map_id=c['map_id'],family=c['family'],source=c['source'],seconds=elapsed,cpu_seconds=cpu_seconds,mode=mode,optimal_cost=c['optimal_cost'],reachable=c['optimal_cost'] is not None)
 for c in cases[:2]:
  for mode in modes:trial(c,mode)
 for ci,c in enumerate(cases):
  for repeat in range(a.repeats):
   order=list(modes);rng.shuffle(order)
   for mode in order:rows.append(dict(trial(c,mode),repeat=repeat))
  if ci%50==0:print(ci+1,'/',len(cases),flush=True)
 for name,h in hashes.items():assert hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()==h
 data={'scope':'Secondary post-freeze source/repair diagnostics; no tuning permitted. Cold full pipeline, seven shuffled repetitions and two excluded warmup cases. All sources use identical frozen engine and repair budgets except named ablations. Unavailable oracle-derived synthetic guidance on fresh maps is not real LLM output.','args':{'bound':2,'repeats':a.repeats},'actual_api_calls':0,'source_hashes':hashes,'case_hash':hashlib.sha256(json.dumps(finite_json(cases),sort_keys=True).encode()).hexdigest(),'runs':rows}
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json(data),f,separators=(',',':'))
 print('Completed',len(rows),'secondary trials, sources unchanged')
if __name__=='__main__':main()
