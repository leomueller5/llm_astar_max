"""Development-only full fresh-query profile; never contacts a model."""
import sys,json,cProfile,pstats,io,tracemalloc,statistics
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark import cached_cases,ROOT
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.search import LazyGridGraph
OUT=ROOT/'experiments/results/research_session2'
CONFIG=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True)

def run(c):
 t=perf_counter();graph=LazyGridGraph(c['query']);made=perf_counter()
 r=IncumbentSearch(**CONFIG).search(c['query'],c['points'],graph)
 r['geometry_init_seconds']=made-t;r['fresh_seconds']=perf_counter()-t;r['geometry_checks']=graph.edge_checks
 return r

def main():
 cases=cached_cases('development')[::5] # fixed 2 queries per development map
 for c in cases[:8]:run(c)
 rows=[]
 for repeat in range(5):
  for c in cases:
   r=run(c);rows.append({k:v for k,v in r.items() if k not in ['path']})
 prof=cProfile.Profile();prof.enable()
 for c in cases:run(c)
 prof.disable();stream=io.StringIO();pstats.Stats(prof,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(45)
 (OUT/'baseline_profile.txt').write_text(stream.getvalue().rstrip()+'\n')
 keys=['fresh_seconds','geometry_init_seconds','preprocess_seconds','search_seconds','visibility_edge_checks','geometry_checks']
 summary={k:{'mean':statistics.mean(r[k] for r in rows),'median':statistics.median(r[k] for r in rows)} for k in keys}
 peaks=[]
 for c in cases[::10]:
  tracemalloc.start();run(c);peaks.append(tracemalloc.get_traced_memory()[1]);tracemalloc.stop()
 output={'cases':len(cases),'repeats':5,'split':'development','config':CONFIG,'summary':summary,'tracemalloc_peak_bytes':peaks,'profile':stream.getvalue()}
 (OUT/'baseline_profile.json').write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps(summary,indent=2));print(stream.getvalue())
if __name__=='__main__':main()
