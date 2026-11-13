"""Fresh per-query native timing: original Shapely and selected lazy geometry."""
import contextlib,io,json,random,statistics,math
from time import perf_counter
from benchmark import cached_cases,GridGraph,ROOT,WORKSPACE,legacy_run,replay,SEED,finite_json
from llmastar.research.search import LazyGridGraph,WaypointSearch,SearchConfig
from llmastar.research.incumbent import IncumbentSearch
from llmastar.pather import CertifiedLLMAStar


def main():
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='')
 allcases=cached_cases('test');cases=[c for c in allcases if c['id'].split('_')[2] in ['0','5']]
 # Fixed two query indices per held-out map, not chosen by performance.
 assert len(cases)==40
 rows=[];rng=random.Random(SEED)
 for i,c in enumerate(cases):
  graph=GridGraph(c['query'])
  for repetition in range(3):
   modes=['original','wa2','direct_only','selected'];rng.shuffle(modes)
   for mode in modes:
    if mode=='original':
     r=legacy_run(Original,c,graph,native=True);seconds=r['total_seconds']
    elif mode=='selected':
     p=CertifiedLLMAStar(waypoint_response=c['response']);started=perf_counter()
     with contextlib.redirect_stdout(io.StringIO()):result=p.searching(c['query'])
     seconds=perf_counter()-started;r=p.research_result
    else:
     started=perf_counter();lazy=LazyGridGraph(c['query'])
     if mode=='wa2':r=WaypointSearch(SearchConfig(alpha=0,goal_weight=2)).search(c['query'],[c['query']['start'],c['query']['goal']],lazy)
     else:r=IncumbentSearch(use_waypoints=False).search(c['query'],[],lazy)
     seconds=perf_counter()-started
    assert r['valid']
    rows.append({'case_id':c['id'],'map_id':c['map_id'],'mode':mode,'repeat':repetition,
                 'seconds':seconds,'length':r['length'],'unique':r['unique'],'operation':r['operation']})
  if i%10==0:print(f'{i+1}/40 native queries',flush=True)
 med={}
 for mode in ['original','wa2','direct_only','selected']:
  times=[r['seconds'] for r in rows if r['mode']==mode]
  med[mode]={'median_ms':statistics.median(times)*1000,'mean_ms':statistics.mean(times)*1000}
 p=ROOT/'experiments/results/research/native_timing.json'
 p.write_text(json.dumps({'scope':'40 held-out standard-prompt queries, indices 0 and 5 per map; 3 shuffled repetitions; cached response only. Selected includes inherited initial processing and fresh lazy geometry. Controls include fresh geometry. No precomputed graph supplied to search. Imports/model network excluded.',
                          'actual_api_calls':0,'summary':med,'runs':rows},indent=2)+'\n')
 print(json.dumps(med,indent=2))
if __name__=='__main__':main()
