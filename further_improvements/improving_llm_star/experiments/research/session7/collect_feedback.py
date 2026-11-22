"""Actual one-shot model corrections from legal frontier evidence; bounded budget."""
import argparse,json
from pathlib import Path
from time import perf_counter
from common import read_cases,dump,Session7Client,RequestUnavailable
from prompts_spatial import decode
from prompts_grounded import build
from cost_controls import Scaled
from feedback import evidence,damp_from_evidence
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--initial',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);archive=out/'results.json.gz';rows=read_cases(archive)['runs'] if archive.exists() else [];done={(r['case_id'],r['method']) for r in rows};cases={c['id']:c for c in read_cases(a.cases)};alpha=read_cases(a.coefficients)['full_development_alpha']['image'];client=Session7Client()
    for initial in read_cases(a.initial)['runs']:
        if initial['representation']!='image':continue
        c=cases[initial['case_id']];q=c['query'];raw=initial['response']['choices'][0]['message']['content'];field,_=decode(q,raw,4,'cost');initial_field=Scaled(field,alpha)
        for method in ['none','classical','targeted','generic_review']:
            if (c['id'],method) in done:continue
            events=[]
            def revise(context):
                pairs=evidence(q,initial_field,context);event={'context':context,'contradictions':pairs,'eligible':len(pairs)>=2,'actual_api_calls':0};events.append(event)
                if len(pairs)<2:return None
                if method=='classical':return damp_from_evidence(q,initial_field,pairs)
                info={'previous_raw_predictions':json.loads(raw),'used_global_alpha':alpha,'request':'Review your additional-cost estimates once. Preserve regions you cannot justify changing.'}
                if method=='targeted':info.update(actual_search=context,verified_legal_edges=pairs,interpretation='Exact remaining costs differ by at most a legal edge cost. These coarse interpolated predictions violate that property beyond the geometric anchor violation. Region samples are distinct from the boundary states; assess useful corrections, do not assume detours are failures.')
                t=perf_counter();messages,fmt,meta,image=build(q,'image','cost',4,feedback=info);event['prompt_processing_seconds']=perf_counter()-t
                t=perf_counter();response,rid,cached=client.chat(messages,{'phase':'search_feedback','case_id':c['id'],'split':c['split'],'prompt_version':'s7_cost_feedback_v1_'+method},max_tokens=1400,response_format=fmt);event.update(response=response,request_id=rid,cached=cached,actual_api_calls=int(not cached),request_wall_seconds=perf_counter()-t)
                replacement,parsed=decode(q,response['choices'][0]['message'].get('content') or '',4,'cost');event['parsed']=parsed
                return Scaled(replacement,alpha)
            try:r=SpatialSearch(mode='heuristic_envelope',base_weight=1).search(q,initial_field,revision=None if method=='none' else revise,revision_after=128)
            except RequestUnavailable:
                dump(out/'availability.json',{'case':c['id'],'method':method,'budget':client.ledger.summary(),'resumable':True});return
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=method,pops=r['heap_pops'],pushes=r['heap_pushes'],unique=r['unique'],valid=r['valid'],cost_ratio=r['length']/c['optimal_cost'],rebuilds=r['rebuilds'],total_seconds=r['total_seconds'],search_seconds=r['search_seconds'],revision_seconds=r['revision_seconds'],events=events));done.add((c['id'],method));dump(archive,{'scope':'Development pilot. Real targeted versus generic self-review; one separately reserved request per eligible query, never per node. Contradiction gate fixed before collection, no reference costs/path in any request. Actual total latency includes online calls; cached reruns are separately marked.','runs':rows,'budget':client.ledger.summary()});print(c['id'],method,'pops',r['heap_pops'],'actual_calls',sum(e.get('actual_api_calls',0) for e in events),flush=True)
if __name__=='__main__':main()
