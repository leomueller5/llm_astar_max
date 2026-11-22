"""Resumable paid collection; every attempt passes the cumulative budget gate."""
import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter

from api import RetryClient, RequestUnavailable
from hybrid import portfolio,messages,decode,ROOT


def write_archive(path,rows):
    tmp=path.with_suffix('.tmp')
    with gzip.open(tmp,'wt') as f:
        json.dump({'runs':rows},f)
    tmp.replace(path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--prompts',nargs='+',default=['original','rank','repair','policy'])
    p.add_argument('--limit',type=int)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-tokens',type=int,default=384)
    p.add_argument('--original-max-tokens',type=int,default=1000)
    a=p.parse_args()
    cases=json.load(gzip.open(a.cases,'rt'))[:a.limit]
    a.output.mkdir(parents=True,exist_ok=True)
    path=a.output/'responses.json.gz'
    rows=json.load(gzip.open(path,'rt'))['runs'] if path.exists() else []
    done={(r['case_id'],r['prompt']) for r in rows}
    client=RetryClient()
    failures=0
    for case in cases:
        proposal=portfolio(case['query'])
        for version in a.prompts:
            if (case['id'],version) in done:
                continue
            tick=perf_counter()
            try:
                response,rid,cached=client.chat(messages(case['query'],version,proposal),
                    {'phase':'hybrid_'+case['split'],'prompt_version':'s6_'+version+'_v1',
                     'case_id':case['id']},max_tokens=a.original_max_tokens if version in ['original','bounds_original'] else a.max_tokens)
            except RequestUnavailable:
                failures+=1
                print(json.dumps({'case':case['id'],'prompt':version,'failed':True,
                                  'diagnostic':client.last_error}),flush=True)
                if failures>=3:
                    print('Stopping collection after three failed logical requests',flush=True)
                    return
                continue
            raw=response['choices'][0]['message'].get('content') or ''
            points,meta=decode(raw,case['query'],version,proposal)
            rows.append({'case_id':case['id'],'prompt':version,'request_id':rid,
                         'response':response,'cached':cached,'points':points,'meta':meta,
                         'proposal':proposal,'collection_seconds':perf_counter()-tick})
            write_archive(path,rows)
            print(json.dumps({'case':case['id'],'prompt':version,'points':len(points),
                'parsed':meta.get('parsed'),'cached':cached,
                'budget':client.ledger.summary()}),flush=True)
    client.ledger.export()


if __name__=='__main__':
    main()
