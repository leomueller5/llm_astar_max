import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter
from api import RetryClient,RequestUnavailable
from hybrid import portfolio
from vision import visual_input


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int)
    p.add_argument('--hard-only',action='store_true');a=p.parse_args()
    cases=json.load(gzip.open(a.cases,'rt'))[:a.limit];a.output.mkdir(parents=True,exist_ok=True)
    path=a.output/'responses.json.gz';rows=json.load(gzip.open(path,'rt'))['runs'] if path.exists() else []
    done={(r['case_id'],r['prompt']) for r in rows};client=RetryClient();failures=0
    for case in cases:
        q=case['query'];proposal=portfolio(q)
        if a.hard_only and proposal['candidates'][0]['failed_links']==0:continue
        for image in [False,True]:
            version='visual_v1' if image else 'visual_text_v1'
            if (case['id'],version) in done:continue
            msgs,fmt,lookup,png,seconds=visual_input(q,proposal,image)
            if png:(a.output/(case['id']+'.png')).write_bytes(png)
            tick=perf_counter()
            try:
                response,rid,cached=client.chat(msgs,{'phase':'vision_'+case['split'],
                    'prompt_version':'s6_'+version,'case_id':case['id']},max_tokens=192,response_format=fmt)
            except RequestUnavailable:
                failures+=1;print(json.dumps({'failed':True,'case':case['id'],'diagnostic':client.last_error}),flush=True)
                if failures>=3:return
                continue
            raw=response['choices'][0]['message'].get('content') or ''
            try:ids=json.loads(raw).get('targets',[])
            except ValueError:ids=[]
            points=[lookup[i] for i in ids if isinstance(i,str) and i in lookup]
            rows.append({'case_id':case['id'],'prompt':version,'request_id':rid,'response':response,
                'points':points,'meta':{'parsed':len(ids)==len(points),'provided_ids':ids},
                'proposal':proposal,'prompt_preprocess_seconds':seconds,
                'collection_seconds':perf_counter()-tick,'cached':cached,'api_calls':1})
            tmp=path.with_suffix('.tmp')
            with gzip.open(tmp,'wt') as f:json.dump({'runs':rows},f)
            tmp.replace(path)
            print(json.dumps({'case':case['id'],'prompt':version,'points':len(points),
                'usage':response.get('usage'),'budget':client.ledger.summary()}),flush=True)


if __name__=='__main__':main()
