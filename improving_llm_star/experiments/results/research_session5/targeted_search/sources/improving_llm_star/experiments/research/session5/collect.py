"""Explicitly authorized cached OpenAI collection; all calls use the same cap."""
import argparse,gzip,json,sqlite3,concurrent.futures
from pathlib import Path
from time import perf_counter
from api_budget import BudgetClient,Ledger,MODEL,RequestUnavailable,BudgetExceeded
from prompts import messages,decode,feedback_for


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--prompts',nargs='+',default=['original','coords_v1','endpoints_v1','ascii_v1']);p.add_argument('--phase',default='pilot');p.add_argument('--workers',type=int,default=3);p.add_argument('--limit',type=int);p.add_argument('--rep',type=int,default=0);p.add_argument('--feedback',choices=['none','targeted','self'],default='none');p.add_argument('--parent',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True)
    with gzip.open(a.cases,'rt') as f:cases=json.load(f)
    if a.limit:cases=cases[:a.limit]
    parents={}
    if a.parent:
        with gzip.open(a.parent,'rt') as f:
            for row in json.load(f)['runs']:parents[row['case_id'],row['prompt']]=row
    rows=[];jobs=[(c,prompt) for c in cases for prompt in a.prompts]
    def job(pair):
        c,version=pair;previous=None;feedback=None
        if a.feedback!='none':
            parent=parents.get((c['id'],version))
            if not parent or not parent.get('response'):return None
            previous=parent['response']['choices'][0]['message'].get('content') or ''
            points,_=decode(previous,c['query'],version);feedback=feedback_for(c['query'],points)
            if feedback is None:return None
        msg,lookup,prep=messages(c['query'],version,feedback if a.feedback=='targeted' else None,previous)
        metadata=dict(phase=a.phase,case_id=c['id'],prompt_version=version,feedback=a.feedback,rep=a.rep)
        try:
            client=BudgetClient();r,rid,cached=client.chat(msg,metadata,max_tokens=1024,seed=20261118+a.rep)
            row=dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],prompt=version,feedback=a.feedback,response=r,request_id=rid,cache_hit=cached,prompt_seconds=prep)
            path=a.output/(rid+'.json');path.write_text(json.dumps(row,indent=2))
            return row
        except (RequestUnavailable,BudgetExceeded) as exc:return dict(case_id=c['id'],prompt=version,error=str(exc))
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for row in pool.map(job,jobs):
            if row:rows.append(row);print(row['case_id'],row['prompt'],row.get('error','cached' if row.get('cache_hit') else 'ok'),flush=True)
    ledger=Ledger();ledger.export()
    with gzip.open(a.output/'responses.json.gz','wt') as f:json.dump({'model':MODEL,'phase':a.phase,'concurrency':a.workers,'rep':a.rep,'budget':ledger.summary(),'runs':rows},f,separators=(',',':'))
    print(json.dumps(ledger.summary()))
if __name__=='__main__':main()
