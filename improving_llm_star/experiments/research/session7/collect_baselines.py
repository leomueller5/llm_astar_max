"""Fresh frozen-original and Session6 advice, same Session7 model conditions."""
import argparse,json,time
from pathlib import Path
from time import perf_counter
from common import Session7Client,read_cases,dump,RequestUnavailable,RESULTS
from api import BudgetClient
from prompts import messages as original_messages,decode as original_decode
from strategic import strict_messages,decode_strict
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.geometric_advice import portfolio
from llmastar.research.strategic.cuts import CutPotential

class TextBaselineClient:
    def __init__(self,base):self.base=base
    def chat(self,messages,metadata):
        c=self.base
        for attempt in range(c.attempts):
            try:
                result=BudgetClient(c.ledger,c.transport).chat(messages,dict(metadata,session=7,retry_attempt=attempt),max_tokens=1000,seed=20261119,temperature=0)
                c.ledger.export();return result
            except RequestUnavailable:
                if c.last_error and not c.last_error.get('retryable'):break
                if attempt+1<c.attempts:time.sleep(c.backoff*2**attempt)
        raise RequestUnavailable('Bounded original-baseline attempts exhausted; holds retained')

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--types',nargs='+',default=['original','vm']);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);archive=out/'responses.json.gz';rows=read_cases(archive)['runs'] if archive.exists() else [];done={(r['case_id'],r['baseline']) for r in rows};client=Session7Client();textclient=TextBaselineClient(client)
    for c in read_cases(a.cases):
        q=c['query']
        for kind in a.types:
            if (c['id'],kind) in done:continue
            began=perf_counter();api_calls=0;cached=False;rid=None;proposal=None
            if kind=='original':
                message,lookup,prep=original_messages(q,'original')
                try:response,rid,cached=textclient.chat(message,{'phase':'heldout_original','case_id':c['id'],'prompt_version':'frozen_original_standard_s7seed'})
                except RequestUnavailable:dump(out/'availability.json',{'case':c['id'],'kind':kind,'budget':client.ledger.summary()});return
                points,meta=original_decode(response,q,'original');api_calls=1
            elif kind=='vm':
                graph=SegmentGridGraph(q)
                try:anchor=CutPotential(q,tuple(q['goal']))
                except ValueError:anchor=None
                proposal=portfolio(q,graph,budget=12,anchor=anchor)
                if proposal['candidates'] and proposal['candidates'][0]['failed_links']==0:
                    response={'choices':[{'message':{'content':'{}'},'finish_reason':'geometry_gate'}]};points=proposal['geometry_best'];meta={'parsed':True,'api_skipped':True}
                else:
                    message,fmt=strict_messages(q,proposal,'multi_strict')
                    try:response,rid,cached=client.chat(message,{'phase':'heldout_frozen_vm','case_id':c['id'],'prompt_version':'s6_multi_strict_v1_common_s7seed'},max_tokens=384,response_format=fmt)
                    except RequestUnavailable:dump(out/'availability.json',{'case':c['id'],'kind':kind,'budget':client.ledger.summary()});return
                    points,meta=decode_strict(response['choices'][0]['message'].get('content') or '',proposal,'multi_strict');api_calls=1
            else:raise ValueError('Unknown baseline')
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],baseline=kind,response=response,points=points,meta=meta,proposal=proposal,request_id=rid,api_calls=api_calls,cached=cached,collection_seconds=perf_counter()-began,seed=20261119));done.add((c['id'],kind));dump(archive,{'scope':'Frozen original and frozen Session6 algorithm/prompt. Fresh responses use the common Session7 snapshot/temperature/seed; original1000 and VM384 output caps retain their respective baseline formats.','runs':rows,'budget':client.ledger.summary()});print(c['id'],kind,'calls',api_calls,flush=True)
if __name__=='__main__':main()
