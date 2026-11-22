"""Development-only schema-constrained decisions and geometry-gated requests."""
import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter

from api import RetryClient,RequestUnavailable
from hybrid import portfolio
from strategic import strict_messages,fork_context,fork_messages,decode_strict
def write_archive(path,rows):
    tmp=path.with_suffix('.tmp')
    with gzip.open(tmp,'wt') as f:
        json.dump({'runs':rows},f)
    tmp.replace(path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prompts',nargs='+',default=['rank_strict','repair_strict','multi_strict','fork'])
    p.add_argument('--limit',type=int);p.add_argument('--seed',type=int,default=20261118)
    p.add_argument('--temperature',type=float,default=0)
    p.add_argument('--force',action='store_true',help='Prompt-only ablation: request advice even when geometry has a complete route')
    a=p.parse_args()
    cases=json.load(gzip.open(a.cases,'rt'))[:a.limit]
    a.output.mkdir(parents=True,exist_ok=True);path=a.output/'responses.json.gz'
    rows=json.load(gzip.open(path,'rt'))['runs'] if path.exists() else []
    done={(r['case_id'],r['prompt']) for r in rows};client=RetryClient();failures=0
    for case in cases:
        q=case['query'];proposal=portfolio(q);context=fork_context(q,proposal)
        for version in a.prompts:
            if (case['id'],version) in done:
                continue
            tick=perf_counter()
            if version!='rank_strict' and not a.force and proposal['candidates'][0]['failed_links']==0:
                row={'case_id':case['id'],'prompt':version,'request_id':None,
                    'response':{'choices':[{'message':{'content':'{}'},'finish_reason':'geometry_gate'}]},
                    'points':proposal['geometry_best'],'meta':{'parsed':True,'api_skipped':True},
                    'proposal':proposal,'collection_seconds':0.,'api_calls':0}
            elif version=='fork' and context is None:
                row={'case_id':case['id'],'prompt':version,'request_id':None,
                    'response':{'choices':[{'message':{'content':'{}'},'finish_reason':'no_options'}]},
                    'points':proposal['geometry_best'],'meta':{'parsed':True,'api_skipped':True},
                    'proposal':proposal,'collection_seconds':0.,'api_calls':0}
            else:
                message,fmt=fork_messages(context) if version=='fork' else strict_messages(q,proposal,version)
                try:
                    response,rid,cached=client.chat(message,{'phase':'strategic_'+case['split'],
                        'prompt_version':'s6_'+version+'_v1','case_id':case['id']},
                        max_tokens=640 if version=='deliberate_strict' else 384 if version=='multi_strict' else 192,response_format=fmt,
                        seed=a.seed,temperature=a.temperature)
                except RequestUnavailable:
                    failures+=1;print(json.dumps({'failed':True,'case':case['id'],
                        'prompt':version,'diagnostic':client.last_error}),flush=True)
                    if failures>=3:return
                    continue
                raw=response['choices'][0]['message'].get('content') or ''
                points,meta=decode_strict(raw,proposal,version,context)
                row={'case_id':case['id'],'prompt':version,'request_id':rid,'response':response,
                     'points':points,'meta':meta,'proposal':proposal,'context':context,
                     'collection_seconds':perf_counter()-tick,'cached':cached,'api_calls':1}
            rows.append(row);write_archive(path,rows)
            print(json.dumps({'case':case['id'],'prompt':version,'api_calls':row['api_calls'],
                'parsed':row['meta']['parsed'],'points':len(row['points']),
                'budget':client.ledger.summary()}),flush=True)


if __name__=='__main__':main()
