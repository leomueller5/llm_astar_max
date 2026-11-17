"""Development-only information-quality audit; not a runtime benchmark."""
import sys,json,gzip,math,statistics,argparse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from benchmark import ROOT,cached_cases,finite_json
from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route
from llmastar.research.efficient import EfficientCertificateSearch,compress_collinear
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.strategic.schema import parse_guidance
from llmastar.research.strategic.cut_search import legacy_bypasses


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);rows=[];references={};witness={}
 for c in cached_cases('development',('standard','cot','repe')):
  q=c['query'];g=SegmentGridGraph(q);key=c['id'].rsplit('_',1)[0]
  if key not in references:
   ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],g);references[key]=ref['length']
   witness[key]=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=True,prepare_only=True,reuse_validation=True).search(q,[],g)['valid']
  parsed=parse_guidance(c['response'],'cached_real');points=list(parsed.strategies[0].waypoints) if parsed.strategies else []
  free=[p for p in points if g.valid_point(p)];onwalls=sum(g.inside(p) and g.blocked(p) for p in points);outside=sum(not g.inside(p) for p in points)
  path=compress_collinear([tuple(q['start'])]+free+[tuple(q['goal'])]);route=[tuple(q['start'])];valid=True;failed=0
  for x,y in zip(path,path[1:]):
   piece=g.lattice_segment(x,y)
   if piece:route.extend(expand_lattice_route(piece)[1:])
   else:valid=False;failed+=1
  bypasses,invalid,ambiguous=legacy_bypasses(q,points) if points else ([],0,0)
  ratio=sum(math.dist(x,y) for x,y in zip(route,route[1:]))/references[key] if valid else None
  same=[tuple(p) for p in c['points']]==points
  rows.append({'case_id':c['id'],'map_id':c['map_id'],'style':c['source'].removeprefix('repository_cached_'),'points':len(points),'free':len(free),'on_wall':onwalls,'outside':outside,'abstain':parsed.abstain,'warnings':parsed.warnings,'legacy_parser_same':same,'legacy_parse_fallback':c['parse_fallback'],'cleaned_chain_valid':valid,'nonempty_guided_chain_valid':valid and bool(points),'chain_cost_ratio':ratio,'failed_links':failed,'wall_crossing_violations':invalid,'ambiguous_bypasses':ambiguous,'inferred_bypasses':len(bypasses),'witness_solved':witness[key],'response_characters':len(c['response'])})
 summary={}
 for style in ['standard','cot','repe']:
  for scope in ['all','witness_residual']:
   rr=[r for r in rows if r['style']==style and (scope=='all' or not r['witness_solved'])];costs=[r['chain_cost_ratio'] for r in rr if r['cleaned_chain_valid']]
   summary[style+'/'+scope]={'cases':len(rr),'parse_abstentions':sum(r['abstain'] for r in rr),'parser_differences':sum(not r['legacy_parser_same'] for r in rr),'mean_points':statistics.mean(r['points'] for r in rr),'point_on_wall_rate':sum(r['on_wall'] for r in rr)/max(1,sum(r['points'] for r in rr)),'point_outside_rate':sum(r['outside'] for r in rr)/max(1,sum(r['points'] for r in rr)),'cases_with_crossing_violation':sum(r['wall_crossing_violations']>0 for r in rr),'valid_cleaned_chains':sum(r['cleaned_chain_valid'] for r in rr),'valid_nonempty_guided_chains':sum(r['nonempty_guided_chain_valid'] for r in rr),'gm_valid_chain_cost_ratio':math.exp(statistics.mean(math.log(x) for x in costs)) if costs else None,'mean_response_characters':statistics.mean(r['response_characters'] for r in rr)}
 data={'scope':'1800 cached observations on 60 existing DEVELOPMENT maps, 600 distinct queries, three prompting styles. Reference paths generated for audit only; no planner receives these costs. Straight raw-polyline crossing violations are a necessary geometric diagnostic, not a proof that every possible route between two waypoints is impossible. Cleaned chain removes invalid coordinates and checks actual shortest two-piece lattice links.','input_source_sha256':{str(f.relative_to(ROOT.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT.parent/'table1_reproduction').glob('antworten_*.json'))},'summary':summary,'runs':rows}
 with gzip.open(a.output/'audit.json.gz','wt') as f:json.dump(finite_json(data),f,separators=(',',':'))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
