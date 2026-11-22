"""Actual in-search model intervention on original LLMAStar, max one correction."""
import sys,argparse,json,gzip,contextlib,io,hashlib,signal,shutil
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from benchmark import ROOT,WORKSPACE,replay,finite_json
from api_budget import BudgetClient,Ledger,MODEL,RequestUnavailable,BudgetExceeded
from prompts import messages,decode
from repair import repaired_class
from llmastar.utils import list_parse
from llmastar.research.geometry import SegmentGridGraph

class SearchLimit(Exception):pass
def limit(signum,frame):raise SearchLimit()


def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--responses',type=Path,required=True);p.add_argument('--prompt',default='original');p.add_argument('--phase',default='dynamic_pilot');p.add_argument('--threshold',type=int,default=16);p.add_argument('--gated',action='store_true');p.add_argument('--generic',action='store_true');p.add_argument('--rep',type=int,default=0);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);source_hashes={}
 for file in [Path(__file__),Path(__file__).with_name('repair.py'),Path(__file__).with_name('prompts.py'),Path(__file__).with_name('api_budget.py'),WORKSPACE/'llm-astar'/replay.PLANNER_PATH]:
  relative=file.relative_to(WORKSPACE);target=a.output/'sources'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target);source_hashes[str(relative)]=hashlib.sha256(file.read_bytes()).hexdigest()
 with gzip.open(a.cases,'rt') as f:cases={c['id']:c for c in json.load(f)}
 with gzip.open(a.responses,'rt') as f:responses=[r for r in json.load(f)['runs'] if r.get('response') and r['prompt']==a.prompt]
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='');Variant=repaired_class(Original);rows=[]
 for row in responses:
  c=cases[row['case_id']];q=c['query'];raw=row['response']['choices'][0]['message'].get('content') or '';pts,_=decode(raw,q,a.prompt)
  if a.prompt in ['original','coords_v1']:pts=list_parse(raw);original_raw=raw
  else:original_raw='Generated Path: '+json.dumps(pts)
  requests=[]
  def callback(context):
   feedback={'geometry':context['contradiction'],'observed_search':{k:v for k,v in context.items() if k not in ['query','contradiction']}}
   msg,_,_=messages(q,a.prompt,feedback=None if a.generic else feedback,previous=raw)
   msg[-1]['content']+='\nReturn only the required compact path array or JSON; no explanation.'
   meta={'phase':a.phase,'case_id':c['id'],'prompt_version':a.prompt,'intervention':'self' if a.generic else 'targeted','expanded':context['expanded'],'rep':a.rep,'revision_format':'compact_v2'}
   try:
    response,rid,cached=BudgetClient().chat(msg,meta,max_tokens=1024,seed=20261118+a.rep)
    requests.append({'request_id':rid,'response':response,'context':feedback,'cache_hit':cached});new,parse_metadata=decode(response,q,a.prompt)
    if not parse_metadata.get('parse_valid'):return None
    if a.prompt in ['original','coords_v1']:new=list_parse(response['choices'][0]['message'].get('content') or '')
    return new
   except (RequestUnavailable,BudgetExceeded) as exc:requests.append({'error':str(exc)});return None
  planner=Variant();planner.model=replay.OfflineModel(original_raw);planner.set_repair(q,pts,callback,a.threshold,a.gated);graph=SegmentGridGraph(q);planner.cost=graph.cost;planner.is_collision=lambda x,y:not math.isfinite(graph.cost(x,y))
  import math
  began=perf_counter();error=None
  try:
   with contextlib.redirect_stdout(io.StringIO()):result=planner.searching(json.loads(json.dumps(q)))
   path=planner.plot.path;valid=bool(path) and path[0]==tuple(q['start']) and path[-1]==tuple(q['goal']) and all(math.isfinite(graph.cost(tuple(x),tuple(y))) for x,y in zip(path,path[1:]))
  except (KeyError,IndexError,ValueError) as exc:error=type(exc).__name__;result={'length':None,'operation':len(planner.CLOSED)};path=[];valid=False
  elapsed=perf_counter()-began
  if valid:assert abs(result['length']-sum(math.dist(x,y) for x,y in zip(path,path[1:])))<1e-7
  record=dict(path=path,case_id=c['id'],map_id=c['map_id'],family=c['family'],prompt=a.prompt,valid=valid,length=result['length'],operation=result['operation'],unique=len(set(planner.CLOSED)),seconds=elapsed,correction_block_seconds=planner.repair_seconds,search_without_correction_seconds=elapsed-planner.repair_seconds,attempts=planner.repair_attempts,accepted=planner.repair_accepted,events=planner.repair_events,requests=requests,error=error,optimal_cost=c['optimal_cost'],initial_request_id=row['request_id'])
  rows.append(record);(a.output/(c['id']+'.json')).write_text(json.dumps(finite_json(record),indent=2));print(c['id'],'attempts',record['attempts'],'accepted',record['accepted'],'ops',record['operation'],flush=True)
 for name,h in source_hashes.items():assert hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest()==h
 with gzip.open(a.output/'results.json.gz','wt') as f:json.dump(finite_json({'source_hashes':source_hashes,'model':MODEL,'phase':a.phase,'threshold':a.threshold,'gated':a.gated,'generic':a.generic,'runs':rows}),f,separators=(',',':'))
 Ledger().export();print(json.dumps(Ledger().summary()))
if __name__=='__main__':main()
