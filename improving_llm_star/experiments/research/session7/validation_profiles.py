"""Evaluate profiles using coefficients frozen from DEVELOPMENT, never refit here."""
import argparse,statistics,math
from time import perf_counter
from common import read_cases,dump
from prompts_spatial import decode
from cost_controls import Scaled,Constant
from llmastar.research.spatial_guidance import SpatialSearch
from llmastar.research.spatial_calibration import sample_intervals,VerifiedResidualField,BilinearResidualField

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alphas=read_cases(a.coefficients)['full_development_alpha'];rows=[];bounds={}
    for rr in read_cases(a.responses)['runs']:
        c=cases[rr['case_id']];q=c['query'];rep=rr['representation'];f,_=decode(q,rr['response']['choices'][0]['message']['content'],rr['side'],'cost')
        if c['id'] not in bounds:bounds[c['id']]=sample_intervals(q,rr['side'])
        intervals,work=bounds[c['id']];alpha=alphas[rep];scale=math.hypot(f.width,f.height)
        variants=[('none',None,1.,0.),('real',f,1.,0.),('calibrated',Scaled(f,alpha),1.,0.),('bilinear_relative',BilinearResidualField(f,relative=True),1.,0.),('verified',VerifiedResidualField(f,intervals),1.,work['seconds']),('verified_calibrated',VerifiedResidualField(f,intervals,alpha=alpha),1.,work['seconds']),('geometry_midpoint',VerifiedResidualField(f,intervals,source='midpoint'),1.,work['seconds']),('geometry_upper',VerifiedResidualField(f,intervals,source='upper'),1.,work['seconds']),('fixed_diagonal10pct',Constant(.1*scale),1.,0.)]+[(f'weighted_{w}',None,w,0.) for w in [1.05,1.2,1.5,2.]]
        for name,field,w,extra in variants:
            r=SpatialSearch(mode='weighted' if name.startswith('weighted_') else 'heuristic_envelope',base_weight=w).search(q,field)
            assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=rep,method=name,pops=r['heap_pops'],pushes=r['heap_pushes'],unique=r['unique'],expanded=r['expanded'],cost_ratio=r['length']/c['optimal_cost'],search_seconds=r['total_seconds'],preprocessing_seconds=extra,compute_seconds=r['total_seconds']+extra))
        print(c['id'],rep,'independent validation profiles',flush=True)
    summary={}
    for rep,method in sorted({(r['representation'],r['method']) for r in rows}):
        rr=[r for r in rows if (r['representation'],r['method'])==(rep,method)];summary[rep+'/'+method]=dict(cases=len(rr),pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['compute_seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='Independent validation, fixed all-development alpha. No oracle values used in planner. Pilot field construction reused; final native harness must independently measure all preprocessing and prompt/render costs.',coefficients=alphas,summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
