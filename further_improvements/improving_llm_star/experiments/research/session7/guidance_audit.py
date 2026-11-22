"""Supplementary waypoint-lifetime and genuine response-seed diagnostics."""
import argparse,statistics,math,json,re
from pathlib import Path
from common import read_cases,dump,RESULTS
from native_benchmark import legacy,load_baselines,load_costs,execute,CachedCostProvider,ALPHA,deadline,Timeout
from llmastar.research.spatial_planner import SpatialResidualAStar
from llmastar.research.geometry import SegmentGridGraph

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);engine=legacy.Engines();baseline=load_baselines(RESULTS/'heldout_baselines/responses.json.gz');life=[];validity=[]
 for c in read_cases(RESULTS/'heldout_all.json.gz'):
  row=baseline[c['id'],'original'];q=c['query'];graph=SegmentGridGraph(q);raw=row['response']['choices'][0]['message'].get('content') or '';parsed=legacy.list_parse(raw);parse_valid=isinstance(parsed,list);points=[p for p in parsed if isinstance(p,(list,tuple)) and len(p)==2 and all(type(v) in [int,float] and math.isfinite(v) for v in p)] if parse_valid else [];validity.append({'case_id':c['id'],'generated':len(points),'exact_legacy_list_parse_valid':parse_valid,'legacy_default_without_list':not bool(re.search(r'\[\[.*?\]\]',raw,re.S)),'invalid':sum(not graph.valid_point(tuple(p)) for p in points),'non_goal_waypoints':sum(tuple(p) not in [tuple(q['start']),tuple(q['goal'])] for p in points)})
  try:
   with deadline(5):r=legacy.legacy(c,row,'original',engine,True)
   events=r.get('switches',[]);targets=r.get('llm_output') or [];active=targets[1] if len(targets)>1 else None;previous_pop=0;completed=[]
   for event in events:
    completed.append(dict(event,previous_target=active));active=event['target'];previous_pop=event['pop']
   life.append({'case_id':c['id'],'valid':r['valid'],'expanded':r.get('expanded'),'effective_targets':targets,'switches':completed,'intermediate_durations':[e['active_pops'] for e in completed],'last_active_target':active,'tail_duration':r.get('expanded',0)-previous_pop,'intermediate_censored_at_termination':active is not None and tuple(active)!=tuple(q['goal'])})
  except Timeout:life.append({'case_id':c['id'],'timeout':True})
 all_durations=[v for r in life for v in r.get('intermediate_durations',[])];dump(out/'waypoints.json',{'scope':'Original generated-target switch instrumentation. active_pops counts frozen CLOSED appends including duplicates; not unique expansions. A rebuild event stores the NEW target after the switch; its duration belongs to the PREVIOUS intermediate target, including the event switching TO the goal. Unreached last waypoints are censored and omitted from completed-lifetime statistics. Five-second cap retained.','generated_validity':validity,'lifetimes':life,'intermediate_events':len(all_durations),'median_active_pops':statistics.median(all_durations) if all_durations else None,'fraction_under30':statistics.mean(v<30 for v in all_durations) if all_durations else None})
 cases={c['id']:c for c in read_cases(RESULTS/'validation.json.gz')};original=load_costs(RESULTS/'validation_cost/responses.json.gz');extra=read_cases(RESULTS/'seed_sensitivity/responses.json.gz')['runs'];rows=[]
 for cid in sorted({r['case_id'] for r in extra}):
  c=cases[cid];observations=[dict(original[cid,'image'],seed=20261119)]+[r for r in extra if r['case_id']==cid]
  for row in observations:
   r=SpatialResidualAStar(provider=CachedCostProvider(c['query'],row),alpha=ALPHA,bound=1.05).search(c['query']);rows.append({'case_id':cid,'family':c['family'],'seed':row['seed'],'pops':r['operation'],'pushes':r['heap_pushes'],'unique':r['unique'],'valid':r['valid'],'cost_ratio':r['length']/c['optimal_cost'],'raw_response':row['response']['choices'][0]['message']['content']})
 summary=[]
 for cid in sorted({r['case_id'] for r in rows}):
  rr=[r for r in rows if r['case_id']==cid];summary.append({'case_id':cid,'distinct_raw_responses':len({r['raw_response'] for r in rr}),'min_pops':min(r['pops'] for r in rr),'max_pops':max(r['pops'] for r in rr),'cv_pops':statistics.pstdev(r['pops'] for r in rr)/statistics.mean(r['pops'] for r in rr)})
 dump(out/'seed_search.json.gz',{'scope':'Three genuine cached temperature0 seeds on ten hash-selected validation maps. No final configuration tuning. Repeated native timings are not model replicates.','runs':rows,'per_case':summary});print('Waypoint and seed audits complete')
if __name__=='__main__':main()
