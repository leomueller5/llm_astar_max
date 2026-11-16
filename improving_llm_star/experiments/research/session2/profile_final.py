"""Fresh-query development profiles and isolated Python-allocation measurements."""
import sys,json,cProfile,pstats,io,tracemalloc,gc,statistics,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import execute,cached_cases,ROOT,finite_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);cases=cached_cases('development')[::5]
 modes=['old_cf','indexed_cf','compressed_cf','lean_cf','witness_cf','witness_only','scheduled_wa2']
 output={}
 for mode in modes:
  for c in cases[:4]:execute(mode,c)
  results=[execute(mode,c) for c in cases]
  phases={}
  for k in sorted({k for r in results for k in r.get('phase_seconds',{})}):
   phases[k]=statistics.mean(r.get('phase_seconds',{}).get(k,0) for r in results)*1000
  profiler=cProfile.Profile();profiler.enable()
  for c in cases:execute(mode,c)
  profiler.disable();stream=io.StringIO();stats=pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative');stats.print_stats(35)
  (a.output/(mode+'.txt')).write_text(stream.getvalue().rstrip()+'\n')
  memory=[]
  for c in cases[::5]:
   gc.collect();tracemalloc.start();r=execute(mode,c);current,peak=tracemalloc.get_traced_memory();snapshot=tracemalloc.take_snapshot();tracemalloc.stop()
   memory.append({'case_id':c['id'],'map_id':c['map_id'],'peak_python_bytes':peak,'retained_python_bytes':current,'live_allocated_blocks':sum(s.count for s in snapshot.statistics('filename'))})
   del r
  output[mode]={'cases':len(cases),'mean_phase_ms':phases,'mean_total_ms':statistics.mean(r['fresh_seconds'] for r in results)*1000,
    'mean_geometry_init_ms':statistics.mean(r['geometry_init_seconds'] for r in results)*1000,
    'mean_preprocess_ms':statistics.mean(r['preprocess_seconds'] for r in results)*1000,
    'mean_search_ms':statistics.mean(r['search_seconds'] for r in results)*1000,
    'profile_primitive_calls':stats.prim_calls,'profile_total_calls':stats.total_calls,'profile_total_seconds':stats.total_tt,
    'mean_peak_python_bytes':statistics.mean(r['peak_python_bytes'] for r in memory),
    'max_peak_python_bytes':max(r['peak_python_bytes'] for r in memory),'memory':memory}
 payload={'scope':'Development 120 fixed cases; profiles instrumented and not used for speed claims. Memory: 24 fixed cases, GC collected before each independent tracemalloc run; includes fresh query structures, excludes previously imported libraries and native Shapely allocations; not RSS.', 'actual_api_calls':0,'modes':output}
 (a.output/'profile.json').write_text(json.dumps(finite_json(payload),indent=2)+'\n')
 for mode,v in output.items():print(mode,v['mean_total_ms'],v['mean_phase_ms'],'peak',v['mean_peak_python_bytes'],flush=True)
if __name__=='__main__':main()
