import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter
from api import RetryClient,RequestUnavailable
from roadmap import Roadmap,roadmap_messages
from llmastar.research.strategic.cuts import CutPotential


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int)
    p.add_argument('--prompts',nargs='+',default=['complete','graph_only']);a=p.parse_args()
    cases=json.load(gzip.open(a.cases,'rt'))[:a.limit];a.output.mkdir(parents=True,exist_ok=True)
    path=a.output/'responses.json.gz';rows=json.load(gzip.open(path,'rt'))['runs'] if path.exists() else []
    done={(r['case_id'],r['prompt']) for r in rows};client=RetryClient();failures=0
    for case in cases:
        q=case['query'];roadmap=Roadmap(q);proposal=roadmap.proposal()
        lower=CutPotential(q,tuple(q['goal'])).value(tuple(q['start']))
        gate=proposal['geometric_route_cost'] is not None and proposal['geometric_route_cost']<=1.05*lower+1e-9
        for version in a.prompts:
            if (case['id'],version) in done:continue
            if gate:
                row={'case_id':case['id'],'prompt':version,'api_calls':0,'api_skipped':True,
                    'routes':[proposal['geometric_route']],'proposal':proposal,'collection_seconds':0.}
            else:
                msgs,fmt=roadmap_messages(q,proposal,version);tick=perf_counter()
                try:
                    response,rid,hit=client.chat(msgs,{'phase':'roadmap_'+case['split'],
                        'prompt_version':'s6_roadmap_'+version+'_v1','case_id':case['id']},
                        max_tokens=256,response_format=fmt)
                except RequestUnavailable:
                    failures+=1
                    print(json.dumps({'failed':True,'case':case['id'],'diagnostic':client.last_error}),flush=True)
                    if failures>=3:return
                    continue
                try:routes=json.loads(response['choices'][0]['message'].get('content') or '{}').get('routes',[])
                except ValueError:routes=[]
                row={'case_id':case['id'],'prompt':version,'api_calls':1,'api_skipped':False,
                    'routes':routes,'proposal':proposal,'response':response,'request_id':rid,
                    'collection_seconds':perf_counter()-tick,'cached':hit}
            rows.append(row);tmp=path.with_suffix('.tmp')
            with gzip.open(tmp,'wt') as f:json.dump({'runs':rows},f)
            tmp.replace(path)
            print(json.dumps({'case':case['id'],'prompt':version,'api_calls':row['api_calls'],
                'route_count':len(row['routes']),'budget':client.ledger.summary()}),flush=True)


if __name__=='__main__':main()
