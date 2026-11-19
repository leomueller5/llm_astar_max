import argparse,statistics,math
from common import read_cases,dump
from prompts_spatial import decode
from llmastar.research.spatial_guidance import SpatialSearch
from llmastar.research.spatial_calibration import BilinearResidualField

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--alphas',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alphas=read_cases(a.alphas)['full_development_alpha'];rows=[]
    for rr in read_cases(a.responses)['runs']:
        c=cases[rr['case_id']];q=c['query'];rep=rr['representation'];f,_=decode(q,rr['response']['choices'][0]['message']['content'],rr['side'],'cost')
        variants=[('nearest',f),('bilinear',BilinearResidualField(f)),('bilinear_relative',BilinearResidualField(f,relative=True)),('bilinear_scaled',BilinearResidualField(f,alpha=alphas[rep])),('none',None)]
        for mode in ['envelope','heuristic_envelope','dual']:
            for method,field in variants:
                r=SpatialSearch(mode=mode,base_weight=1.,signal='detour').search(q,field)
                rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=rep,mode=mode,method=method,pops=r['heap_pops'],unique=r['unique'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost']))
        print(c['id'],rep,'interpolation/cap pilot',flush=True)
    summary={}
    for rep,mode,method in sorted({(r['representation'],r['mode'],r['method']) for r in rows}):
        rr=[r for r in rows if (r['representation'],r['mode'],r['method'])==(rep,mode,method)];summary['/'.join([rep,mode,method])]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,{'scope':'Development mechanism alternatives: smooth interpolation, state-relative correction, pointwise heuristic envelope versus full-key envelope, anchor-gated dual queue. Scaled coefficients are in-sample exploratory here; select only after independent validation.','summary':summary,'runs':rows});print(summary)
if __name__=='__main__':main()
