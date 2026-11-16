"""Fresh-query repeated offline timing; every variant pays its geometry costs."""
import sys,json,gzip,random,statistics,math,hashlib,argparse,gc,platform
from pathlib import Path
from time import perf_counter,process_time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark import cached_cases,ROOT,WORKSPACE,GridGraph,legacy_run,replay,finite_json
from llmastar.research.search import LazyGridGraph
from llmastar.research.geometry import IndexedGridGraph,SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import EfficientCertificateSearch
from llmastar.research.scheduled import ScheduledCertificateSearch
from llmastar.research.corridor import CorridorSearch

CERT=dict(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True)
VARIANTS={
 'corridor1':(SegmentGridGraph,CorridorSearch,dict(radius=1)),
 'corridor2':(SegmentGridGraph,CorridorSearch,dict(radius=2)),
 'corridor_no_incumbent':(SegmentGridGraph,CorridorSearch,dict(radius=1,incumbent=False)),
 'witness_frontier':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,fallback_engine='lean',reuse_validation=True,witness=True,uncertified='frontier')),
 'witness_chain':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0,chain_only=True,fallback_engine='lean',reuse_validation=True,witness=True,uncertified='frontier')),
 'witness_cf':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,fallback_engine='lean',reuse_validation=True,witness=True)),
 'witness_only':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',use_waypoints=False,fallback_engine='lean',reuse_validation=True,witness=True)),
 'witness_raw':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0,fallback_engine='lean',reuse_validation=True,witness=True)),
 'lean_cf':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,fallback_engine='lean',reuse_validation=True)),
 'lean_pivot':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,pivot_only=True,fallback_engine='lean',reuse_validation=True)),
 'lean_raw':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0,fallback_engine='lean',reuse_validation=True)),
 'lean_direct':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',use_waypoints=False,fallback_engine='lean',reuse_validation=True)),
 'scheduled_wa2':(SegmentGridGraph,ScheduledCertificateSearch,dict(use_waypoints=False,direct=False)),
 'scheduled_direct':(SegmentGridGraph,ScheduledCertificateSearch,dict(use_waypoints=False)),
 'scheduled16':(SegmentGridGraph,ScheduledCertificateSearch,dict(threshold=16)),
 'scheduled64':(SegmentGridGraph,ScheduledCertificateSearch,dict(threshold=64)),
 'frontier_incumbent':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,uncertified='frontier')),
 'chain_frontier':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0,chain_only=True,uncertified='frontier')),
 'chain_prune':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0,chain_only=True,uncertified='prune')),
 'compressed_cf':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True)),
 'pivot_cf':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,pivot_only=True)),
 'quality102':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,certificate_ratio=1.02)),
 'quality105':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,certificate_ratio=1.05)),
 'quality110':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,certificate_ratio=1.1)),
 'compressed_raw':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',compress=True,repair_radius=0)),
 'segment_cf':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic')),
 'segment_raw':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',repair_radius=0)),
 'segment_direct':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',use_waypoints=False)),
 'segment_gate':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',gate='sparse')),
 'segment_accept':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',uncertified='accept_bound')),
 'segment_prune':(SegmentGridGraph,EfficientCertificateSearch,dict(segment_mode='analytic',uncertified='prune')),
 'fast_cf':(IndexedGridGraph,EfficientCertificateSearch,{}),
 'fast_goal_first':(IndexedGridGraph,EfficientCertificateSearch,dict(ordering='goal_first')),
 'fast_direct':(IndexedGridGraph,EfficientCertificateSearch,dict(use_waypoints=False)),
 'gate_detour':(IndexedGridGraph,EfficientCertificateSearch,dict(gate='detour')),
 'gate_distance':(IndexedGridGraph,EfficientCertificateSearch,dict(gate='distance')),
 'gate_sparse':(IndexedGridGraph,EfficientCertificateSearch,dict(gate='sparse')),
 'raw_cf':(IndexedGridGraph,EfficientCertificateSearch,dict(repair_radius=0)),
 'uncertified_accept':(IndexedGridGraph,EfficientCertificateSearch,dict(uncertified='accept_bound')),
 'uncertified_prune':(IndexedGridGraph,EfficientCertificateSearch,dict(uncertified='prune')),
 'old_cf':(LazyGridGraph,IncumbentSearch,CERT),
 'indexed_cf':(IndexedGridGraph,IncumbentSearch,CERT),
 'old_wa2':(LazyGridGraph,IncumbentSearch,dict(use_waypoints=False,visibility_budget=0,certificate_only=True)),
 'indexed_wa2':(IndexedGridGraph,IncumbentSearch,dict(use_waypoints=False,visibility_budget=0,certificate_only=True)),
 'old_astar':(LazyGridGraph,IncumbentSearch,dict(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True)),
 'indexed_astar':(IndexedGridGraph,IncumbentSearch,dict(use_waypoints=False,visibility_budget=0,goal_weight=1,certificate_only=True)),
}


def execute(mode,case):
 Graph,Planner,kwargs=VARIANTS[mode]
 started=perf_counter();cpu=process_time();graph=Graph(case['query']);geometry=perf_counter()-started
 r=Planner(**kwargs).search(case['query'],case['points'],graph)
 r['fresh_seconds']=perf_counter()-started;r['cpu_seconds']=process_time()-cpu;r['geometry_init_seconds']=geometry;r['geometry_checks']=graph.edge_checks
 return r


def summarize(rows):
 out={}
 for mode in sorted({r['variant'] for r in rows}):
  rr=[r for r in rows if r['variant']==mode];by={}
  for r in rr:by.setdefault(r['case_id'],[]).append(r)
  # First reduce repetition noise within each query; then aggregate cases.
  med=[statistics.median(r['fresh_seconds'] for r in records) for records in by.values()]
  one=[v[0] for v in by.values()]
  out[mode]={'cases':len(one),'mean_case_median_ms':statistics.mean(med)*1000,'median_case_median_ms':statistics.median(med)*1000,
   'p95_case_median_ms':sorted(med)[min(len(med)-1,int(.95*len(med)))]*1000,
   'mean_unique':statistics.mean(r['unique'] for r in one),'mean_pops':statistics.mean(r['operation'] for r in one),
   'successes':sum(r['valid'] for r in one),'certificate_fraction':statistics.mean(r.get('certified_early_return',False) for r in one),
   'mean_length':statistics.mean(r['length'] for r in one if r['valid']),
   'mean_preprocessing_ms':statistics.mean(r.get('preprocess_seconds',0)+r['geometry_init_seconds'] for r in rr)*1000,
   'mean_search_ms':statistics.mean(r.get('search_seconds',0) for r in rr)*1000,
   'mean_visibility_checks':statistics.mean(r.get('visibility_edge_checks',0) for r in one)}
 return out


def run(cases,modes,repeats,output):
 output=Path(output)
 if output.exists():raise FileExistsError('Preserve old results; choose a new output directory')
 output.mkdir(parents=True)
 src=[Path(__file__),ROOT/'llmastar/research/geometry.py',ROOT/'llmastar/research/incumbent.py',ROOT/'llmastar/research/efficient.py',ROOT/'llmastar/research/scheduled.py',ROOT/'llmastar/research/corridor.py']
 source_hashes={str(p.relative_to(WORKSPACE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
 snapshot=output/'source_snapshot';snapshot.mkdir()
 for p in src:(snapshot/p.name).write_bytes(p.read_bytes())
 for c in cases[:4]:
  for mode in modes:execute(mode,c)
 rng=random.Random(20261116);rows=[];journal=(output/'runs.jsonl').open('w')
 for ci,c in enumerate(cases):
  for repeat in range(repeats):
   order=list(modes);rng.shuffle(order)
   for mode in order:
    r=execute(mode,c);r.pop('path',None)
    rows.append(dict(r,case_id=c['id'],map_id=c['map_id'],family=c['family'],source=c['source'],optimal_cost=c.get('optimal_cost'),variant=mode,repeat=repeat))
  for record in rows[-repeats*len(modes):]:journal.write(json.dumps(finite_json(record),separators=(',',':'))+'\n')
  journal.flush()
  if ci%100==0:print(f'{ci+1}/{len(cases)}',flush=True)
 journal.close()
 summary=summarize(rows)
 src=[Path(__file__),ROOT/'llmastar/research/geometry.py',ROOT/'llmastar/research/incumbent.py']
 fast=ROOT/'llmastar/research/efficient.py'
 if fast.exists():src.append(fast)
 data={'case_count':len(cases),'repeats':repeats,'actual_api_calls':0,'warmup':'first four cases per mode, excluded',
  'timing':'fresh graph+planner+certificate+fallback+path validation; cached raw parsing outside all core timings; default GC, randomized interleaving',
  'case_hash':hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),
  'source_hashes':source_hashes,'python':sys.version,'platform':platform.platform(),
  'variants':{m:{'graph':VARIANTS[m][0].__name__,'planner':VARIANTS[m][1].__name__,'options':VARIANTS[m][2]} for m in modes},'summary':summary,'runs':rows}
 with gzip.open(output/'results.json.gz','wt') as f:json.dump(finite_json(data),f,separators=(',',':'),allow_nan=False)
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
 return data


def main():
 p=argparse.ArgumentParser();p.add_argument('--split',default='development',choices=['development','validation','test'])
 p.add_argument('--cases',type=Path);p.add_argument('--prompts',nargs='+',default=['standard']);p.add_argument('--stride',type=int,default=1);p.add_argument('--repeats',type=int,default=5)
 p.add_argument('--variants',nargs='+',default=list(VARIANTS));p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.cases:
  with gzip.open(a.cases,'rt') as f:cases=json.load(f)
 else:cases=cached_cases(a.split,a.prompts)
 run(cases[::a.stride],a.variants,a.repeats,a.output)
if __name__=='__main__':main()
