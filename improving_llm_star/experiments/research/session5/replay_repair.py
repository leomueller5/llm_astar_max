"""Offline counterfactuals use the EXACT same successful online corrections."""
import sys,json,gzip,random,math,statistics,argparse,contextlib,io,hashlib
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from benchmark import ROOT,WORKSPACE,replay,finite_json
from repair import repaired_class,quality
from prompts import decode
from llmastar.utils import list_parse
from llmastar.research.geometry import SegmentGridGraph

class Restart(Exception):
    def __init__(self,points):self.points=points


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--dynamic',type=Path,required=True);p.add_argument('--repeats',type=int,default=7);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True)
 with gzip.open(a.cases,'rt') as f:cases={c['id']:c for c in json.load(f)}
 with gzip.open(a.initial,'rt') as f:initial={r['case_id']:r for r in json.load(f)['runs'] if r.get('response') and r['prompt']=='original'}
 with gzip.open(a.dynamic,'rt') as f:dynamic={r['case_id']:r for r in json.load(f)['runs']}
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='');Variant=repaired_class(Original)
 modes=['original','no_guidance','noop','egor_gated','egor_ungated','restart_gated','shuffle_gated','random_gated'];rows=[];rng=random.Random(2026111851)
 for cid,c in cases.items():
  raw=initial[cid]['response']['choices'][0]['message'].get('content') or '';points=list_parse(raw);source=dynamic[cid]
  successful=[r for r in source['requests'] if r.get('response')];new=None
  if successful:
   data=successful[0]['response'];new,meta=decode(data,c['query'],'original')
   if meta.get('parse_valid'):new=list_parse(data['choices'][0]['message'].get('content') or '')
   else:new=None
  local=random.Random(sum(map(ord,cid)));start,goal=tuple(c['query']['start']),tuple(c['query']['goal']);interior=[p for p in (new or []) if tuple(p) not in [start,goal]];local.shuffle(interior);shuffled=[start]+interior+[goal];random_points=[start];check=SegmentGridGraph(c['query'])
  while len(random_points)<len(interior)+1:
   point=local.randrange(check.x0+1,check.x1),local.randrange(check.y0+1,check.y1)
   if check.valid_point(point):random_points.append(point)
  random_points.append(goal)
  for rep in range(a.repeats):
   order=list(modes);rng.shuffle(order)
   for mode in order:
    began=perf_counter();graph=SegmentGridGraph(c['query']);planraw=raw if mode!='no_guidance' else 'Generated Path: '+json.dumps([c['query']['start'],c['query']['goal']]);planner=Original() if mode in ['original','no_guidance'] else Variant();correction=new
    if mode=='shuffle_gated':correction=shuffled
    if mode=='random_gated':correction=random_points
    def callback(ctx):
     if mode=='noop':return None
     if mode=='restart_gated' and correction is not None and quality(c['query'],correction)<quality(c['query'],points):
      normalized=planner._filter_valid_nodes(correction)
      if not normalized or normalized[0]!=planner.s_start:normalized.insert(0,planner.s_start)
      if not normalized or normalized[-1]!=planner.s_goal:normalized.append(planner.s_goal)
      if normalized!=planner.target_list:raise Restart(correction)
     return correction
    if mode not in ['original','no_guidance']:planner.set_repair(c['query'],points,callback,16,mode!='egor_ungated')
    planner.model=replay.OfflineModel(planraw);planner.cost=graph.cost;planner.is_collision=lambda x,y:not math.isfinite(graph.cost(x,y));prefix_ops=0;prefix_closed=set();restarted=False
    with contextlib.redirect_stdout(io.StringIO()):
     try:result=planner.searching(json.loads(json.dumps(c['query'])))
     except Restart as signal:
      prefix_ops=len(planner.CLOSED);prefix_closed=set(planner.CLOSED);restarted=True
      planner=Original();planner.model=replay.OfflineModel('Generated Path: '+json.dumps(signal.points));planner.cost=graph.cost;planner.is_collision=lambda x,y:not math.isfinite(graph.cost(x,y));result=planner.searching(json.loads(json.dumps(c['query'])))
    elapsed=perf_counter()-began;path=planner.plot.path
    assert path[0]==tuple(c['query']['start']) and path[-1]==tuple(c['query']['goal']) and all(math.isfinite(graph.cost(x,y)) for x,y in zip(path,path[1:]))
    assert abs(result['length']-sum(math.dist(x,y) for x,y in zip(path,path[1:])))<1e-7
    rows.append(dict(case_id=cid,map_id=c['map_id'],family=c['family'],mode=mode,rep=rep,operation=prefix_ops+result['operation'],unique=len(prefix_closed|set(planner.CLOSED)),length=result['length'],optimal_cost=c['optimal_cost'],seconds=elapsed,valid=True,restarted=restarted,accepted=getattr(planner,'repair_accepted',int(restarted)),attempts=getattr(planner,'repair_attempts',int(restarted))))
 summary={}
 for mode in modes:
  rr=[r for r in rows if r['mode']==mode];one=[r for r in rr if r['rep']==0];times=[statistics.median(r['seconds'] for r in rr if r['case_id']==cid) for cid in cases]
  summary[mode]=dict(mean_ms=statistics.mean(times)*1000,mean_pops=statistics.mean(r['operation'] for r in one),mean_unique=statistics.mean(r['unique'] for r in one),gm_cost_ratio=math.exp(statistics.mean(math.log(r['length']/r['optimal_cost']) for r in one)),accepted=sum(r['accepted'] for r in one))
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json({'scope':'Offline exact successful-correction replay. Restart pays actual initial16 expansions and full restarted search; no new API calls. All variants preserve original code scoring/duplicates/switching except named intervention. Random/shuffle corrections synthetic controls. Development only, no held-out claim.','summary':summary,'runs':rows}),f,separators=(',',':'))
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
