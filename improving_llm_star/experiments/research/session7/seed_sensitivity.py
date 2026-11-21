"""Secondary real-response sensitivity, never used to select final settings."""
import argparse,hashlib,json
from pathlib import Path
from common import Session7Client,read_cases,dump,RequestUnavailable
from prompts_grounded import build
from prompts_spatial import decode

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);archive=out/'responses.json.gz';rows=read_cases(archive)['runs'] if archive.exists() else [];done={(r['case_id'],r['seed']) for r in rows};allcases=read_cases(a.cases);chosen=[min([c for c in allcases if c['family']==f],key=lambda c:hashlib.sha256(c['id'].encode()).hexdigest()) for f in sorted({c['family'] for c in allcases})];client=Session7Client()
    for c in chosen:
        messages,fmt,meta,image=build(c['query'],'image','cost',4)
        for seed in [20261120,20261121]:
            if (c['id'],seed) in done:continue
            try:response,rid,cached=client.chat(messages,{'phase':'seed_sensitivity','case_id':c['id'],'split':'validation','prompt_version':'s7_cost_image_s4_grounded_v2'},max_tokens=1400,response_format=fmt,seed=seed,temperature=0)
            except RequestUnavailable:dump(out/'availability.json',{'case':c['id'],'budget':client.ledger.summary()});return
            field,meta=decode(c['query'],response['choices'][0]['message'].get('content') or '',4,'cost');rows.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'seed':seed,'response':response,'request_id':rid,'cached':cached,'parsed':meta});done.add((c['id'],seed));dump(archive,{'scope':'Ten validation maps selected by ID hash, one/family; two additional genuine temperature0seeds, combined with originalseed20261119 later. Frozen primary not tuned on these results.','runs':rows});print(c['id'],seed,'actual response cached',flush=True)
if __name__=='__main__':main()
