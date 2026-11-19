"""Explicitly paid collection. All attempts reserve against the cumulative cap."""
import argparse,json,hashlib
from pathlib import Path
from time import perf_counter
from common import Session7Client,RESULTS,read_cases,dump,RequestUnavailable
from prompts_spatial import build,decode

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--representations',nargs='+',default=['structured']);p.add_argument('--task',choices=['cost','corridor'],default='corridor');p.add_argument('--side',type=int,default=8);p.add_argument('--limit',type=int);p.add_argument('--examples');p.add_argument('--grounded',action='store_true');p.add_argument('--nearest-examples',action='store_true');p.add_argument('--output',required=True);a=p.parse_args()
    output=Path(a.output);output.mkdir(parents=True,exist_ok=True);archive=output/'responses.json.gz';runs=read_cases(archive)['runs'] if archive.exists() else [];done={(r['case_id'],r['representation']) for r in runs};client=Session7Client()
    if a.grounded:
        from prompts_grounded import build as builder
    else:builder=build
    examples=json.loads(Path(a.examples).read_text()) if a.examples else None
    for c in read_cases(a.cases)[:a.limit]:
        for representation in a.representations:
            if (c['id'],representation) in done:continue
            selected_examples=examples
            if a.nearest_examples:
                from examples import select_examples
                selected_examples=select_examples(examples,c['query'])
            if any(e.get('map_id')==c['map_id'] for e in selected_examples or []):raise ValueError('Training/evaluation map leakage')
            began=perf_counter();messages,fmt,meta,image=builder(c['query'],representation,a.task,a.side,selected_examples)
            meta['example_case_ids']=[e.get('case_id') for e in selected_examples or []]
            prompt_seconds=perf_counter()-began;version=f's7_{a.task}_{representation}_s{a.side}_'+('grounded_v2' if a.grounded else 'v1')+((('_nearest_icl_' if a.nearest_examples else '_fixed_icl_')+hashlib.sha256(Path(a.examples).read_bytes()).hexdigest()[:12]) if a.examples else '')
            if image:(output/(c['id']+'_'+representation+'.png')).write_bytes(image)
            try:
                t=perf_counter();response,identifier,cached=client.chat(messages,{'phase':'spatial_collection','case_id':c['id'],'split':c['split'],'prompt_version':version,'representation':representation,'task':a.task,'side':a.side},max_tokens=1400 if a.task=='cost' else 512,response_format=fmt);network_seconds=perf_counter()-t
            except RequestUnavailable:
                dump(output/'availability.json',{'failed_case':c['id'],'diagnostic':client.last_error,'budget':client.ledger.summary(),'resumable':True});print('Bounded API failure; results and reservations preserved.',flush=True);return
            raw=response['choices'][0]['message'].get('content') or '';field,parsed=decode(c['query'],raw,a.side,a.task)
            runs.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'split':c['split'],'representation':representation,'task':a.task,'side':a.side,'prompt_version':version,'request_id':identifier,'response':response,'parsed':parsed,'prediction_values':field.values,'meta':meta,'prompt_processing_seconds':prompt_seconds,'request_wall_seconds':network_seconds,'cached':cached,'examples_sha256':hashlib.sha256(Path(a.examples).read_bytes()).hexdigest() if a.examples else None})
            dump(archive,{'runs':runs,'budget':client.ledger.summary()});done.add((c['id'],representation));print(c['id'],representation,'parsed',parsed.get('parsed'),'tokens',response['usage']['total_tokens'],'exposure',round(client.ledger.summary()['accounted_usd']+client.ledger.summary()['held_worst_case_usd'],5),flush=True)
if __name__=='__main__':main()
