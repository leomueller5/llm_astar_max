"""Separate resource diagnostics; never run concurrently with native timings."""
import argparse,gc,hashlib,cProfile,pstats,io,statistics,tracemalloc,json,random
from pathlib import Path
from time import perf_counter
from common import read_cases,dump,RESULTS
from native_benchmark import execute,legacy,load_baselines,load_costs,verify_sources,deadline,Timeout
from prompts_grounded import build

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cases=read_cases(a.cases);verify_sources(json.loads((RESULTS/'frozen_manifest.json').read_text()));base=load_baselines(RESULTS/'heldout_baselines/responses.json.gz');cost=load_costs(RESULTS/'heldout_cost/responses.json.gz');icl=load_costs(RESULTS/'heldout_icl/responses.json.gz');examples=json.loads((RESULTS/'icl/cost_examples_fixed.json').read_text());engine=legacy.Engines();rows=[]
 # Ex ante hash choices: one per family plus four additional geometries.
 selected=[]
 for family in sorted({c['family'] for c in cases}):selected.append(min((c for c in cases if c['family']==family),key=lambda c:hashlib.sha256(('s7resource'+c['id']).encode()).hexdigest()))
 used={c['map_id'] for c in selected};selected+=sorted((c for c in cases if c['map_id'] not in used),key=lambda c:hashlib.sha256(('s7resourceextra'+c['id']).encode()).hexdigest())[:4]
 dump(out/'selected.json',[c['id'] for c in selected])
 for c in cases:
  tasks=[('image',None),('structured',None),('icl',examples)];random.Random('s7prompt'+c['id']).shuffle(tasks)
  for kind,ex in tasks:
   rep='image' if kind=='icl' else kind;build(c['query'],rep,'cost',4,ex);times=[]
   for _ in range(3):
    tick=perf_counter();messages,fmt,meta,img=build(c['query'],rep,'cost',4,ex);times.append(perf_counter()-tick)
   rows.append({'case_id':c['id'],'type':'prompt','method':kind,'seconds':statistics.median(times),'trials':times,'image_bytes':len(img) if img else 0})
 for c in selected:
  for method in ['original','robust_original','matched_uniform105','optimized_uniform105','rh_image105','vm_geo105']:
   gc.collect();tracemalloc.start();tick=perf_counter();r={'valid':False};error=None
   try:
    with deadline(30):r=execute(c,method,engine,base,cost,icl,False)
   except Timeout:error='instrumented_timeout30seconds'
   seconds=perf_counter()-tick;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
   rows.append({'case_id':c['id'],'type':'memory','method':method,'peak_traced_bytes':peak,'retained_traced_bytes':current,'instrumented_seconds_NOT_NATIVE':seconds,'valid':r['valid'],'error':error})
  print(c['id'],'resource audit complete',flush=True)
 profile_rows=[]
 for c in selected[:3]:
  for method in ['original','matched_uniform105','rh_image105','vm_geo105']:
   profile=cProfile.Profile();profile_error=None;profile.enable()
   try:
    with deadline(30):execute(c,method,engine,base,cost,icl,False)
   except Timeout:profile_error='instrumented_timeout30seconds'
   finally:profile.disable()
   stream=io.StringIO();stats=pstats.Stats(profile,stream=stream);total=sum(v[2] for v in stats.stats.values());heap=sum(v[2] for key,v in stats.stats.items() if 'heappop' in key[2] or 'heappush' in key[2] or 'heapify' in key[2]);profile_rows.append({'case_id':c['id'],'method':method,'error':profile_error,'profile_total_self_seconds':total,'heap_self_seconds':heap,'heap_fraction_of_profile_self_time':heap/total if total else None});stats.strip_dirs().sort_stats('cumulative').print_stats(22);(out/(c['id']+'_'+method+'.txt')).write_text(stream.getvalue().rstrip()+'\n')
 dump(out/'results.json.gz',{'scope':'Prompt/image CPU three repeats after warmup, fresh preprocessing. Tracemalloc memory is Python allocations only, with profiling overhead; never use these timings as native runtime or total RSS. Case selection by fixed hash, not performance. cProfile diagnostics on three fixed queries.','runs':rows,'profile_summaries':profile_rows})
if __name__=='__main__':main()
