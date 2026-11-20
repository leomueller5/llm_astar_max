"""Marginal spatial information on a prespecified strong w=1.05 anchor profile."""
import argparse,statistics,math,random
from common import read_cases,dump
from prompts_spatial import decode
from cost_controls import Scaled
from evaluate import permuted
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alpha=read_cases(a.coefficients)['full_development_alpha'];rows=[]
    for rr in read_cases(a.responses)['runs']:
        c=cases[rr['case_id']];q=c['query'];rep=rr['representation'];f,_=decode(q,rr['response']['choices'][0]['message']['content'],rr['side'],'cost');shuffled=permuted(f,c['id'])
        for method,field,base,bound in [('strong_none',None,1.05,2.),('strong_real',f,1.05,2.),('strong_calibrated',Scaled(f,alpha[rep]),1.05,2.),('strong_shuffled_calibrated',Scaled(shuffled,alpha[rep]),1.05,2.),('tight_none',None,1.05,1.05),('tight_variable',Scaled(f,alpha[rep]),1.,1.05)]:
            r=SpatialSearch(mode='heuristic_envelope',bound=bound,base_weight=base).search(q,field)
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=rep,method=method,pops=r['heap_pops'],unique=r['unique'],cost_ratio=r['length']/c['optimal_cost'],seconds=r['total_seconds']))
        print(c['id'],rep,'strong-anchor marginal control',flush=True)
    summary={}
    for rep,method in sorted({(r['representation'],r['method']) for r in rows}):
        rr=[r for r in rows if (r['representation'],r['method'])==(rep,method)];summary[rep+'/'+method]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='Follow-up integration hypothesis: add the SAME development-fitted residual to the already prespecified strong1.05 geometric anchor. No alpha refitting or parameter sweep; two quality profiles distinguish fixed base from tight total-bound control.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
