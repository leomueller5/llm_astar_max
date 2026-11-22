"""Reproducible cProfile diagnostics; never use these times as native runtimes."""
import sys,argparse,gzip,json,cProfile,pstats,io
from pathlib import Path


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--oracle',action='store_true');p.add_argument('--loops',type=int,default=1);p.add_argument('--family',nargs='*');p.add_argument('--size',type=int);p.add_argument('--snapshot',type=Path);p.add_argument('--legacy',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root))
 if a.snapshot:
  import llmastar
  llmastar.__path__.insert(0,str(a.snapshot/'llmastar'))
 from llmastar.research.strategic.cut_search import CutStrategySearch
 from llmastar.research.strategic.providers import StaticProvider
 from llmastar.research.geometry import SegmentGridGraph
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 with gzip.open(a.cases,'rt') as f:cases=json.load(f)
 cases=[c for c in cases if (not a.family or c['family'] in a.family) and (not a.size or c.get('size')==a.size)]
 rows=[];profile=cProfile.Profile();profile.enable()
 for _ in range(a.loops):
  for c in cases:
   provider=StaticProvider({'strategies':[{'id':'oracle','waypoints':c['oracle_waypoints']}]},'oracle',parser_limits={'max_points':100000}) if a.oracle else None
   r=CutStrategySearch(max_segments=20000,interpret_legacy=a.legacy).search(c['query'],provider,SegmentGridGraph(c['query']))
   rows.append({k:r.get(k) for k in ['unique','operation','seed_count','candidate_seconds','provider_seconds','cut_preprocess_seconds','lazy_heuristic_seconds','total_seconds']})
 profile.disable();text=io.StringIO();pstats.Stats(profile,stream=text).sort_stats('cumtime').print_stats(40)
 (a.output/'profile.txt').write_text(text.getvalue());(a.output/'components.json').write_text(json.dumps({'scope':'Instrumented diagnostics, not native runtime. Snapshot option imports archived modules without altering sources. Oracle production excluded and unavailable.','args':vars(a),'runs':rows},default=str,indent=2));print(text.getvalue())
if __name__=='__main__':main()
