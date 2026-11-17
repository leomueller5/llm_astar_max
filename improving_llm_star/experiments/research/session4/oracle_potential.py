"""Phase1: fixed real/oracle/random/geometric/imperfect guidance potential."""
import sys,json,gzip,random,math,statistics,hashlib,argparse
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark import ROOT,cached_cases,finite_json
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch,compress_collinear
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.guidance import WaypointGuidanceSearch
from llmastar.research.strategic.route import RouteRefinementSearch


def main():
 p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=120);p.add_argument('--repeats',type=int,default=5);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);allcases=cached_cases('development');cases=allcases[::5][:a.limit];rows=[];oracle_seconds=0.
 planners={'witness':lambda:EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,fallback_engine='lean',reuse_validation=True),
  'prefix':lambda:WaypointGuidanceSearch(lazy=True,cut_filter=True),
  'ordered_route':lambda:RouteRefinementSearch(),
  'verified_chain':lambda:EfficientCertificateSearch(segment_mode='analytic',witness=True,compress=True,repair_radius=0,chain_only=True,uncertified='frontier',fallback_engine='lean',reuse_validation=True)}
 rng=random.Random(202611174)
 for ci,c in enumerate(cases):
  t=perf_counter();ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(c['query'],[],SegmentGridGraph(c['query']));oracle_seconds+=perf_counter()-t
  corners=compress_collinear(ref['path']);graph=SegmentGridGraph(c['query']);start,goal=tuple(c['query']['start']),tuple(c['query']['goal'])
  geometric=[]
  for x,lo,hi in graph.vertical:geometric.extend([(x,lo-1),(x,hi+1)])
  for y,lo,hi in graph.horizontal:geometric.extend([(lo-1,y),(hi+1,y)])
  geometric=[p for p in geometric if graph.valid_point(p)]
  random_points=[]
  while len(random_points)<max(2,len(corners)):
   q=rng.randrange(graph.x0+1,graph.x1),rng.randrange(graph.y0+1,graph.y1)
   if graph.valid_point(q):random_points.append(q)
  imperfect=[start]+[(x+rng.choice([-1,0,1]),y+rng.choice([-1,0,1])) for x,y in corners[1:-1]]+[goal]
  inputs={'cached_real':c['points'],'oracle':corners,'imperfect_oracle':imperfect,'random':random_points,'geometry':geometric,'none':[]}
  jobs=[(method,source) for method in planners for source in inputs if method!='witness' or source=='none']
  for repeat in range(a.repeats):
   rng.shuffle(jobs)
   for method,source in jobs:
    began=perf_counter();g=SegmentGridGraph(c['query']);r=planners[method]().search(c['query'],inputs[source],g);elapsed=perf_counter()-began
    rows.append({'case_id':c['id'],'map_id':c['map_id'],'method':method,'source':source,'repeat':repeat,'valid':r['valid'],'length':r['length'],'optimal_cost':ref['length'],'unique':r['unique'],'pops':r['operation'],'seconds':elapsed,'search_seconds':r.get('search_seconds'), 'source_points':len(inputs[source])})
  if ci%30==0:print(ci+1,'/',len(cases),flush=True)
 summary={}
 for method,source in sorted({(r['method'],r['source']) for r in rows}):
  rr=[r for r in rows if r['method']==method and r['source']==source];one=[r for r in rr if r['repeat']==0]
  times=[statistics.median(r['seconds'] for r in rr if r['case_id']==c['id']) for c in cases]
  summary[method+'/'+source]={'mean_case_median_ms':statistics.mean(times)*1000,'mean_unique':statistics.mean(r['unique'] for r in one),'mean_pops':statistics.mean(r['pops'] for r in one),'gm_path_ratio':math.exp(statistics.mean(math.log(r['length']/r['optimal_cost']) for r in one if r['valid'])),'valid':sum(r['valid'] for r in one)}
 data={'scope':'Fixed development queries; oracle-generation and response generation excluded from planner timing and separately labelled. Ordered-route pilot has validity-only guarantee, not global quality bound. No paid calls. Random/geometric sets may contain many irrelevant points; input sizes recorded.','oracle_generation_seconds':oracle_seconds,'case_count':len(cases),'summary':summary,'runs':rows}
 with gzip.open(a.output/'results.json.gz','wt') as f:f.write(json.dumps(finite_json(data),separators=(',',':')))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
