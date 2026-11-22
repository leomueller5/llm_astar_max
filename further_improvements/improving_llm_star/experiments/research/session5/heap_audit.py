"""Separate exact heap/memory accounting; no API and no timing claims."""
import sys,json,gzip,math,heapq,tracemalloc,contextlib,io,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from benchmark import ROOT,WORKSPACE,replay
from repair import repaired_class
from prompts import decode
from llmastar.utils import list_parse
from llmastar.research.geometry import SegmentGridGraph


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 root=a.root;cases=json.load(gzip.open(root/'development.json.gz','rt'));initial={r['case_id']:r for r in json.load(gzip.open(root/'prompt_pilot/responses.json.gz','rt'))['runs'] if r['prompt']=='original'};dynamic={r['case_id']:r for r in json.load(gzip.open(root/'dynamic_pilot/results.json.gz','rt'))['runs']};expected=json.load(open(root/'repair_replay_controls_v2/summary.json'))
 replay.BACKEND='installed';Original=replay.load_planner(WORKSPACE/'llm-astar',response='');Variant=repaired_class(Original);rows=[]
 for c in cases:
  raw=initial[c['id']]['response']['choices'][0]['message'].get('content') or '';points=list_parse(raw);requests=[r for r in dynamic[c['id']]['requests'] if r.get('response')];new=None
  if requests:
   response=requests[0]['response'];new,meta=decode(response,c['query'],'original')
   new=list_parse(response['choices'][0]['message'].get('content') or '') if meta.get('parse_valid') else None
  for method in ['original','no_guidance','egor_gated']:
   counts=dict(push=0,pop=0,heapify=0,rebuilds=0);saved=heapq.heappush,heapq.heappop,heapq.heapify
   def push(q,v):counts['push']+=1;return saved[0](q,v)
   def pop(q):counts['pop']+=1;return saved[1](q)
   def heapify(q):counts['heapify']+=1;return saved[2](q)
   tracemalloc.start();heapq.heappush,heapq.heappop,heapq.heapify=push,pop,heapify
   try:
    graph=SegmentGridGraph(c['query']);planner=Variant() if method=='egor_gated' else Original();planner.model=replay.OfflineModel('Generated Path: '+json.dumps([c['query']['start'],c['query']['goal']]) if method=='no_guidance' else raw)
    if method=='egor_gated':planner.set_repair(c['query'],points,lambda ctx:new,16,True)
    original_update=planner._update_queue
    def rekey():counts['rebuilds']+=1;return original_update()
    planner._update_queue=rekey;planner.cost=graph.cost;planner.is_collision=lambda x,y:not math.isfinite(graph.cost(x,y))
    with contextlib.redirect_stdout(io.StringIO()):r=planner.searching(json.loads(json.dumps(c['query'])))
    _,peak=tracemalloc.get_traced_memory()
   finally:heapq.heappush,heapq.heappop,heapq.heapify=saved;tracemalloc.stop()
   assert counts['pop']==r['operation']
   rows.append(dict(case_id=c['id'],method=method,operation=r['operation'],cost=r['length'],peak_traced_bytes=peak,**counts))
 for method in ['original','no_guidance','egor_gated']:
  rr=[r for r in rows if r['method']==method];assert abs(sum(r['operation'] for r in rr)/len(rr)-expected[method]['mean_pops'])<1e-9
 a.output.write_text(json.dumps({'scope':'Separate30 instrumented trials on development data. Heap API calls include original retarget rekeys. Tracemalloc tracks Python/exposed-buffer allocations, not full native RSS; instrumented times excluded from performance results. No network.','runs':rows},indent=2));print('30 heap/memory audits match replay operation counts; no new API calls')
if __name__=='__main__':main()
