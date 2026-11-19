"""Baseline-format entry point; offline unless --online is explicitly supplied."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from api import RetryClient,CumulativeLedger,MODEL
from strategic import strict_messages,decode_strict,schema
from hybrid import ROOT
from llmastar.research.hybrid_guidance import HybridWaypointPlanner


class BudgetedGuidanceProvider:
    """One logical model call, bounded retries, persistent cumulative $3 ledger."""
    def __init__(self,client=None):
        self.client=client or RetryClient();self.last_metrics={};self.history=[]

    def parse_query(self,text):
        pair={'type':'array','minItems':2,'maxItems':2,'items':{'type':'integer'}}
        walls={'type':'array','items':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'integer'}}}
        fmt=schema('planning_query',{'start':pair,'goal':pair,'range_x':pair,'range_y':pair,
                                    'horizontal_barriers':walls,'vertical_barriers':walls})
        messages=[{'role':'system','content':'Parse the original LLM-A* planning input. Return only the map dictionary. Width W and height H mean range_x=[0,W], range_y=[0,H]. Horizontal walls are [y,x_min,x_max]; vertical walls are [x,y_min,y_max]. Do not plan a route.'},
                  {'role':'user','content':text}]
        identity=hashlib.sha256(text.encode()).hexdigest()
        response,rid,cached=self.client.chat(messages,{'phase':'deployable_parser',
            'prompt_version':'s6_query_parser_v1','text_sha256':identity},max_tokens=4096,response_format=fmt)
        self.history.append({'request_id':rid,'cached':cached,'usage':response.get('usage',{}),'purpose':'query_parser'})
        return json.loads(response['choices'][0]['message']['content'])

    def propose(self,query,candidates):
        messages,fmt=strict_messages(query,candidates,'multi_strict')
        identity=hashlib.sha256(json.dumps(query,sort_keys=True).encode()).hexdigest()
        tick=perf_counter()
        response,rid,cached=self.client.chat(messages,{'phase':'deployable_hybrid',
            'prompt_version':'s6_multi_strict_v1','query_sha256':identity},
            max_tokens=384,response_format=fmt)
        raw=response['choices'][0]['message'].get('content') or ''
        points,meta=decode_strict(raw,candidates,'multi_strict')
        if response.get('model')!=MODEL:raise RuntimeError('Unexpected provider model; do not use guidance')
        self.last_metrics={'model':MODEL,'request_id':rid,'cached':cached,
            'usage':response.get('usage',{}),'provider_seconds':perf_counter()-tick,
            'logical_requests':1,'budget':self.client.ledger.summary()}
        self.history.append(dict(self.last_metrics,purpose='waypoint_guidance'))
        return {'routes':meta.get('routes') or [points]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--query-file',type=Path,required=True)
    p.add_argument('--routes-file',type=Path);p.add_argument('--online',action='store_true')
    p.add_argument('--source',default='hybrid',choices=['hybrid','hybrid_always','geometry_best','geometry_consensus','all_endpoints','goal_only','llm_only'])
    p.add_argument('--selection',default='consensus',choices=['first','consensus','consensus_rank','portfolio'])
    p.add_argument('--weight',type=float,default=2.);p.add_argument('--output',type=Path)
    a=p.parse_args();query=json.loads(a.query_file.read_text())
    if a.output and a.output.exists():raise FileExistsError(a.output)
    routes=json.loads(a.routes_file.read_text()) if a.routes_file else None
    provider=BudgetedGuidanceProvider() if a.online else None
    planner=HybridWaypointPlanner(provider=provider,source=a.source,
        selection=a.selection,weight=a.weight)
    result=planner.searching(query,routes=routes)
    if provider is not None:
        result['llm_generation']=provider.last_metrics;result['llm_request_history']=provider.history
    if a.output:
        if a.output.exists():raise FileExistsError(a.output)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['path','trace','events']},indent=2))


if __name__=='__main__':main()
