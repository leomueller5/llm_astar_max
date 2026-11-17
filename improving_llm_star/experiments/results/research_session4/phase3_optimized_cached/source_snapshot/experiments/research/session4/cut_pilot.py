"""Cold-query cut relaxation, primal advice and matched source ablations."""
import sys,json,gzip,random,math,statistics,argparse,hashlib,shutil
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parent));from maps import ROOT
from benchmark import cached_cases,finite_json
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider,ScriptedProvider
from llmastar.research.strategic.roadmap import RoadmapProvider
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch,compress_collinear


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path);p.add_argument('--limit',type=int,default=120);p.add_argument('--repeats',type=int,default=5);p.add_argument('--bound',type=float,default=1.1);p.add_argument('--modes',nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 sources=list((ROOT/'llmastar/research').rglob('*.py'))+[Path(__file__)]
 manifest={}
 for f in sources:
  dest=a.output/'source_snapshot'/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);manifest[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
 if a.cases:
  with gzip.open(a.cases,'rt') as f:cases=json.load(f)
 else:
  cases=[]
  for c in cached_cases('development')[::5][:a.limit]:
   ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(c['query'],[],SegmentGridGraph(c['query']))
   cases.append(dict(c,oracle_path=ref['path'],oracle_waypoints=compress_collinear(ref['path']),optimal_cost=ref['length'],family='cached_real'))
 (a.output/'manifest.json').write_text(json.dumps({'sources':manifest,'cases_sha256':hashlib.sha256(json.dumps(finite_json(cases),sort_keys=True).encode()).hexdigest(),'args':vars(a)},default=str,indent=2))
 with gzip.open(a.output/'cases.json.gz','wt') as f:json.dump(finite_json(cases),f)
 rng=random.Random(2026111743);rows=[]
 modes=a.modes or ['astar','weighted','witness','cut_anchor','cut_geo','cut_real','cut_oracle','cut_imperfect','cut_random','cut_dynamic','cut_legacy_off']
 for ci,c in enumerate(cases):
  q=c['query'];graph=SegmentGridGraph(q);points=c.get('points',[]);oracle=c['oracle_waypoints']
  local=random.Random(sum(map(ord,c['id'])));random_points=[]
  while len(random_points)<max(2,len(oracle)):
   point=local.randrange(graph.x0+1,graph.x1),local.randrange(graph.y0+1,graph.y1)
   if graph.valid_point(point):random_points.append(point)
  imperfect=[tuple(q['start'])]+[(x+local.choice([-1,0,1]),y+local.choice([-1,0,1])) for x,y in oracle[1:-1]]+[tuple(q['goal'])]
  inputs={'real':points,'oracle':oracle,'imperfect':imperfect,'random':random_points}
  for repeat in range(a.repeats):
   jobs=list(modes);rng.shuffle(jobs)
   for mode in jobs:
    provider=None
    if mode in ['cut_real','cut_oracle','cut_imperfect','cut_random','cut_legacy_off']:
     source=mode[4:] if mode!='cut_legacy_off' else 'real'
     provider=StaticProvider(c.get('response',{'strategies':[{'id':source,'waypoints':inputs[source]}]}) if source=='real' else {'strategies':[{'id':source,'waypoints':inputs[source]}]},'cached_real' if source=='real' else source,parser_limits={'max_points':100000} if source=='oracle' else None)
    elif mode.startswith('roadmap_'):provider=RoadmapProvider(points if mode=='roadmap_real' else oracle if mode=='roadmap_oracle' else [],source=mode)
    elif mode=='cut_dynamic':provider=ScriptedProvider([{'strategies':[{'id':'wrong','waypoints':random_points}]},{'strategies':[{'id':'revised_oracle','waypoints':oracle}]}],source='simulated_oracle_revision')
    began=perf_counter();g=SegmentGridGraph(q)
    if mode in ['astar','weighted']:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1 if mode=='astar' else a.bound).search(q,[],g)
    elif mode=='witness':r=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,fallback_engine='lean',reuse_validation=True).search(q,[],g)
    else:r=CutStrategySearch(bound=a.bound,geometry_candidates=mode!='cut_anchor',intervention='effort' if mode=='cut_dynamic' else 'blocked',interpret_legacy=mode!='cut_legacy_off',selection='none' if mode=='cut_octile' else 'all',cache_heuristic=mode!='cut_uncached',max_segments=20000 if mode=='cut_oracle' else 512).search(q,provider,g)
    elapsed=perf_counter()-began;path=r.pop('path',[])
    assert not r['valid'] or (path[0]==tuple(q['start']) and path[-1]==tuple(q['goal']) and all(math.isfinite(g.cost(x,y)) for x,y in zip(path,path[1:])))
    if mode.startswith(('cut_','roadmap_')) and r['valid']:assert r['length']<=a.bound*c['optimal_cost']+1e-7
    rows.append(dict(r,case_id=c['id'],map_id=c['map_id'],family=c['family'],mode=mode,repeat=repeat,seconds=elapsed,optimal_cost=c['optimal_cost']))
  if ci%10==0:print(ci+1,'/',len(cases),flush=True)
 summary={}
 for mode in modes:
  rr=[r for r in rows if r['mode']==mode];one=[r for r in rr if r['repeat']==0];times=[statistics.median(r['seconds'] for r in rr if r['case_id']==c['id']) for c in cases]
  ratio=[r['length']/r['optimal_cost'] for r in one if r['valid']]
  summary[mode]={'mean_case_median_ms':statistics.mean(times)*1000,'median_case_ms':statistics.median(times)*1000,'mean_unique':statistics.mean(r['unique'] for r in one),'mean_pops':statistics.mean(r['operation'] for r in one),'gm_cost_ratio':math.exp(statistics.mean(math.log(x) for x in ratio)) if ratio else None,'max_cost_ratio':max(ratio,default=None),'valid':sum(r['valid'] for r in one),'provider_requests':sum(r.get('provider_requests',0) for r in one),'certified':sum(r.get('certificate') in ['cut_start_bound','intervention_start_bound'] for r in one),'mean_start_bound_ratio':statistics.mean(r['start_lower_bound']/r['optimal_cost'] for r in one if r['valid'] and r.get('start_lower_bound') and r['optimal_cost']) if any(r['valid'] and r.get('start_lower_bound') for r in one) else None}
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json({'scope':'Cold query. All graph, witness, cut preprocessing, parsing, candidate checks and lazy transforms included. Advice/oracle production excluded and labelled; zero actual API calls. Witness default weight2 is a contextual baseline, weighted and cut variants share requested bound.','bound':a.bound,'summary':summary,'runs':rows}),f,separators=(',',':'))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
