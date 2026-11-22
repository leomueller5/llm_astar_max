import argparse,statistics,math
from common import read_cases,dump
from prompts_spatial import decode
from cost_controls import Scaled
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alpha=read_cases(a.coefficients)['full_development_alpha']['image'];rows=[]
    for rr in read_cases(a.responses)['runs']:
        if rr['representation']!='image':continue
        c=cases[rr['case_id']];q=c['query'];f,_=decode(q,rr['response']['choices'][0]['message']['content'],4,'cost')
        for method,field,base,bound in [('astar',None,1.,1.),('weighted105',None,1.05,1.05),('weighted2',None,2.,2.),('calibrated2',Scaled(f,alpha),1.,2.),('calibrated105',Scaled(f,alpha),1.,1.05),('raw2',f,1.,2.),('strong_addition',Scaled(f,alpha),1.05,2.)]:
            r=SpatialSearch(mode='heuristic_envelope',bound=bound,base_weight=base).search(q,field)
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=method,pops=r['heap_pops'],pushes=r['heap_pushes'],queue_operations=r['heap_pops']+r['heap_pushes'],unique=r['unique'],expanded=r['expanded'],stale=r['stale'],reopens=r['reopens'],cost_ratio=r['length']/c['optimal_cost']))
    summary={m:{key:statistics.mean(r[key] for r in rows if r['method']==m) for key in ['pops','pushes','queue_operations','unique','expanded','stale','reopens','cost_ratio']} for m in sorted({r['method'] for r in rows})};dump(a.output,dict(summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
