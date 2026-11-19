"""General model selects a search policy, not coordinates or trusted costs."""
import argparse,json,statistics,math,base64
from pathlib import Path
from time import perf_counter
from common import Session7Client,read_cases,dump,RequestUnavailable
from prompts_spatial import SYSTEM,schema,render
from examples import features
from policy_ceiling import run,reverse_query,local_volume
from llmastar.research.geometry import SegmentGridGraph
POLICIES=['cut_105','cut_2','vm105','vm2','witness']

def context(query):
    t=perf_counter();g=SegmentGridGraph(query);direct=g.lattice_segment(tuple(query['start']),tuple(query['goal'])) is not None
    return {'map':query,'features':features(query),'direct_shortest_lattice_walk_valid':direct,'local_free_volume_radius8':{'forward':local_volume(query,query['start']),'reverse':local_volume(query,query['goal'])}},perf_counter()-t

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--representations',nargs='+',default=['structured']);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);archive=out/'responses.json.gz';rows=read_cases(archive)['runs'] if archive.exists() else [];done={(r['case_id'],r['representation']) for r in rows};client=Session7Client()
    fmt=schema('search_policy',{'policy':{'type':'string','enum':POLICIES},'direction':{'type':'string','enum':['forward','reverse']},'confidence':{'type':'number','minimum':0,'maximum':1}})
    instruction='Choose ONE search policy and launch direction to minimize search work while maintaining short valid paths. cut_105: strong geometric cut heuristic, nearly optimal weight1.05. cut_2: same bound with aggressive weight2. vm105/vm2: verified geometric macro transitions, more setup but potential shortcuts. witness: cheap direct/single-wall certificate then ordinary weighted A*, best for straightforward visible routes, potentially poor in complex mazes. Reverse search starts at the original GOAL and targets the original START on the same undirected graph. Narrow initial branching may help, but downstream traps also matter. feature[1] is cut/octile lower-bound ratio. Prefer high quality when performance is uncertain. You are selecting algorithms, not supplying a path. Do not assume reverse is always better.'
    for c in read_cases(a.cases):
        for representation in a.representations:
            if (c['id'],representation) in done:continue
            facts,prep=context(c['query']);text=instruction+'\n'+json.dumps(facts,separators=(',',':'));content=text;image_seconds=0.
            if representation=='hybrid':
                tick=perf_counter();image,_=render(c['query']);image_seconds=perf_counter()-tick;(out/(c['id']+'.png')).write_bytes(image);content=[{'type':'text','text':text},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image).decode(),'detail':'high'}}]
            try:
                began=perf_counter();response,request_id,cached=client.chat([{'role':'system','content':SYSTEM},{'role':'user','content':content}],{'phase':'controller','case_id':c['id'],'split':c['split'],'prompt_version':'s7_policy_v1_'+representation},max_tokens=96,response_format=fmt);network=perf_counter()-began
            except RequestUnavailable:dump(out/'availability.json',{'failure':c['id'],'budget':client.ledger.summary()});return
            raw=response['choices'][0]['message'].get('content') or '';parsed=json.loads(raw);assert parsed['policy'] in POLICIES and parsed['direction'] in ['forward','reverse']
            rows.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'representation':representation,'selection':parsed,'facts':facts,'feature_seconds':prep,'image_seconds':image_seconds,'request_seconds':network,'response':response,'request_id':request_id,'cached':cached});dump(archive,{'runs':rows,'budget':client.ledger.summary()});done.add((c['id'],representation));print(c['id'],representation,parsed,flush=True)
if __name__=='__main__':main()
