"""Separate traced-memory and CPU-attribution diagnostics, never timing results."""
import argparse
import cProfile
import gc
import gzip
import hashlib
import importlib.util
import io
import json
import pstats
import signal
import statistics
import tracemalloc
from pathlib import Path
from hybrid import ROOT

spec=importlib.util.spec_from_file_location('session6_memory_benchmark',Path(__file__).with_name('final_benchmark.py'))
bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases=json.load(gzip.open(a.root/'heldout_factorial.json.gz','rt'))
    selected=sorted([c for c in cases if c['family']=='team_random_walls'],key=lambda c:hashlib.sha256(c['id'].encode()).hexdigest())[:4]
    for family in sorted({c['family'] for c in cases if c['family']!='team_random_walls'}):
        selected.append(next(c for c in cases if c['family']==family))
    original=bench.load_responses([a.root/'heldout_original_a/responses.json.gz',a.root/'heldout_original_b/responses.json.gz'])
    hybrid=bench.load_responses([a.root/'heldout_hybrid/responses.json.gz']);engines=bench.Engines();rows=[]
    methods=['original','robust_original','astar','wa2','cut2','hybrid','geometry_best','all_endpoints']
    signal.signal(signal.SIGALRM,bench.alarm)
    for case in selected:
        for method in methods:
            gc.collect();tracemalloc.start();signal.setitimer(signal.ITIMER_REAL,10.)
            try:
                result,path=bench.execute(case,original[case['id']],hybrid[case['id']],method,engines)
                _,peak=tracemalloc.get_traced_memory();status='ok'
            except bench.TrialTimeout:peak=None;status='instrumented_timeout'
            finally:signal.setitimer(signal.ITIMER_REAL,0);tracemalloc.stop()
            rows.append({'case_id':case['id'],'family':case['family'],'method':method,
                'peak_traced_bytes':peak,'status':status})
        print(case['id'],'memory completed',flush=True)
    for method in ['original','hybrid','all_endpoints','cut2']:
        profiler=cProfile.Profile();profiler.enable()
        for case in selected[:4]:bench.execute(case,original[case['id']],hybrid[case['id']],method,engines)
        profiler.disable();profiler.dump_stats(str(a.output/(method+'.pstats')))
        stream=io.StringIO();pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(35)
        (a.output/(method+'.txt')).write_text(stream.getvalue())
    summary={}
    for method in methods:
        values=[r['peak_traced_bytes'] for r in rows if r['method']==method and r['peak_traced_bytes'] is not None]
        summary[method]={'measured_cases':len(values),'mean_KiB':statistics.mean(values)/1024,
            'median_KiB':statistics.median(values)/1024,'max_KiB':max(values)/1024}
    (a.output/'memory.json').write_text(json.dumps({'scope':'14 cases chosen before performance inspection: four team cases by hash plus first query/map of each synthetic family. Tracemalloc covers Python and exposed array allocations for planning plus returned diagnostics; it is not full native RSS. Instrumented runtime is excluded from performance claims.','summary':summary,'runs':rows},indent=2))


if __name__=='__main__':main()
