"""Small genuine first-use latency audit on reserved queries, not selection data."""
import argparse,hashlib,io,contextlib,json,random
from pathlib import Path
from time import perf_counter
from common import Session7Client,read_cases,dump,RESULTS,RequestUnavailable
from collect_baselines import TextBaselineClient
from native_benchmark import legacy,ALPHA,deadline,Timeout
from prompts_grounded import build
from llmastar.research.spatial_planner import SpatialResidualAStar
from llmastar.research.geometry import SegmentGridGraph

class LiveField:
 def __init__(self,client,c):self.client=client;self.case=c;self.records=[]
 def predict(self,q,regions):
  tick=perf_counter();msg,fmt,meta,img=build(q,'image','cost',4);prep=perf_counter()-tick;tick=perf_counter();response,rid,cached=self.client.chat(msg,{'session':7,'phase':'reserved_live_latency','case_id':self.case['id'],'prompt_version':'s7_cost_image_s4_grounded_v2'},max_tokens=1400,response_format=fmt);wall=perf_counter()-tick
  self.records.append({'response':response,'request_id':rid,'cached':cached,'prompt_seconds':prep,'client_wall_seconds':wall});return response['choices'][0]['message']['content']

class LiveOriginal:
 def __init__(self,client,c):self.client=TextBaselineClient(client);self.case=c;self.records=[]
 def ask(self,**kwargs):
  tick=perf_counter();response,rid,cached=self.client.chat([{'role':'user','content':kwargs['prompt']}],{'phase':'reserved_live_latency','case_id':self.case['id'],'prompt_version':'frozen_original_standard_s7seed'});self.records.append({'response':response,'request_id':rid,'cached':cached,'client_wall_seconds':perf_counter()-tick});return response['choices'][0]['message']['content']

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--limit',type=int,default=6);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cases=read_cases(RESULTS/'latency_candidates.json.gz');selected=[]
 for family in sorted({c['family'] for c in cases}):selected.append(min((c for c in cases if c['family']==family),key=lambda c:hashlib.sha256(('s7live'+c['id']).encode()).hexdigest()))
 selected=sorted(selected,key=lambda c:hashlib.sha256(('s7livefamilies'+c['family']).encode()).hexdigest())[:a.limit];dump(out/'protocol.json',{'selected':[c['id'] for c in selected],'order':'Within-query deterministic shuffled method order, seed s7liveorder+caseID','selection':'Fixed hash of family/query IDs, never search performance. Distinct reserved queries, not used for tuning. Includes actual credential-safe API calls, response caching, ledger/export and prompt/image CPU. Original search receives the API response directly through original model.ask. No artificial API latency simulation.'});client=Session7Client();engine=legacy.Engines();rows=[]
 # Warm import/font paths once; exclude only process startup, not per-query render/geometry.
 build(selected[0]['query'],'image','cost',4)
 for c in selected:
  methods=['original','rh_image105'];random.Random('s7liveorder'+c['id']).shuffle(methods)
  for method in methods:
   provider=LiveField(client,c) if method=='rh_image105' else LiveOriginal(client,c);tick=perf_counter();error=None;r=None
   try:
    if method=='rh_image105':r=SpatialResidualAStar(provider=provider,bound=1.05,alpha=ALPHA).search(c['query'])
    else:
     graph=SegmentGridGraph(c['query']);planner=engine.Original();planner.model=provider;planner.cost=graph.cost;planner.is_collision=graph.collision
     with contextlib.redirect_stdout(io.StringIO()),deadline(90):r=planner.searching(json.loads(json.dumps(c['query'])))
     r.update(valid=bool(planner.plot.path),path=planner.plot.path)
   except (RequestUnavailable,Timeout) as exc:error=type(exc).__name__
   row={'case_id':c['id'],'family':c['family'],'method':method,'actual_end_to_end_seconds':perf_counter()-tick,'error':error,'valid':r.get('valid') if r else False,'length':r.get('length') if r else None,'calls':provider.records,'provider_error':r.get('provider_error') if r else None}
   rows.append(row);dump(out/'results.json.gz',{'runs':rows,'budget':client.ledger.summary()});print(c['id'],method,'seconds',round(row['actual_end_to_end_seconds'],3),'calls',len(provider.records),flush=True)
 client.ledger.export()
if __name__=='__main__':main()
