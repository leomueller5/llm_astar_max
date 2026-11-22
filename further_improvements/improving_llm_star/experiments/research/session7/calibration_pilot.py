import argparse,statistics,math
from common import read_cases,dump
from prompts_spatial import decode
from llmastar.research.spatial_calibration import sample_intervals,VerifiedResidualField
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--alphas',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alphas=read_cases(a.alphas)['full_development_alpha'];rows=[];bounds={}
    for rr in read_cases(a.responses)['runs']:
        c=cases[rr['case_id']];q=c['query'];rep=rr['representation'];raw=rr['response']['choices'][0]['message']['content'];field,_=decode(q,raw,rr['side'],'cost')
        if c['id'] not in bounds:bounds[c['id']]=sample_intervals(q,rr['side'])
        intervals,work=bounds[c['id']]
        for method,source,alpha,relative in [('verified_model','model',1.,False),('verified_model_relative','model',1.,True),('verified_model_scaled','model',alphas[rep],False),('verified_midpoint','midpoint',1.,False),('verified_upper','upper',1.,False),('zero','zero',1.,False)]:
            f=VerifiedResidualField(field,intervals,source,alpha,relative);r=SpatialSearch(mode='envelope',base_weight=1.,signal='detour').search(q,f)
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=rep,method=method,pops=r['heap_pops'],unique=r['unique'],cost_ratio=r['length']/c['optimal_cost'],search_seconds=r['total_seconds'],preprocessing_seconds=work['seconds'],full_compute_seconds=r['total_seconds']+work['seconds'],alpha_values=f.alpha_values,interval_work=work))
        print(c['id'],rep,'verified residual pilot',flush=True)
    summary={}
    for rep,method in sorted({(r['representation'],r['method']) for r in rows}):
        rr=[r for r in rows if r['representation']==rep and r['method']==method];summary[rep+'/'+method]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['full_compute_seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,{'scope':'Development pilot, cached real costs. Uses collision-checked geometric witnesses only, not optimal reference costs. Scaled variant uses all-development supervised alpha and is in-sample exploratory; unscaled model/midpoint/upper do not use reference labels. Reused bound construction time allocated equally; final timing must reconstruct per trial.','summary':summary,'runs':rows,'bounds':{k:{'intervals':v[0],'work':v[1]} for k,v in bounds.items()}});print(summary)
if __name__=='__main__':main()
