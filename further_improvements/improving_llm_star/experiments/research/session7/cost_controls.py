"""Does spatial model information beat scalar inflation / calibrated trust?"""
import argparse,math,statistics,random
from common import read_cases,dump
from prompts_spatial import decode
from oracle import remaining_costs,anchor
from llmastar.research.spatial_guidance import SpatialSearch,RegionField

class Constant:
    def __init__(self,value,confidence=1.):self.delta=value;self.confidence=confidence
    def value(self,n):return self.delta,.5,self.confidence
class Scaled:
    def __init__(self,field,scale,relative=False):
        self.field=field;self.scale=scale;self.relative=relative;self.h=anchor(field.query,'cut');self.centers={r['id']:tuple(r['sample']) for r in field.regions if r['sample']}
    def value(self,n):
        d,p,c=self.field.value(n)
        if self.relative:
            center=self.centers.get(self.field.identifier(n));d*=self.h(n)/max(1.,self.h(center)) if center else 0.
        return self.scale*d,p,c

def fit_alpha(rows):
    numerator=sum(pred*target for pred,target in rows);denominator=sum(pred*pred for pred,target in rows)
    return max(0.,min(1.,numerator/denominator)) if denominator else 0.
def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};responses=read_cases(a.responses)['runs'];fields={};training={};rows=[];coefficients={}
    for rr in responses:
        c=cases[rr['case_id']];f,_=decode(c['query'],rr['response']['choices'][0]['message']['content'],rr['side'],'cost');fields[c['id'],rr['representation']]=f;costs,_=remaining_costs(c['query']);h=anchor(c['query'],'cut');scale=math.hypot(f.width,f.height);data=[]
        for region in f.regions:
            n=tuple(region['sample']) if region['sample'] else None
            if n not in costs:continue
            d,pr,conf=f.value(n);data.append((d*conf/scale,max(0.,costs[n]-h(n))/scale))
        training[c['id'],rr['representation']]=data
    for rep in sorted({r['representation'] for r in responses}):
        coefficients[rep]=fit_alpha([item for (cid,r),data in training.items() if r==rep for item in data])
    for rr in responses:
        c=cases[rr['case_id']];q=c['query'];rep=rr['representation'];field=fields[c['id'],rep];scale=math.hypot(field.width,field.height);loo=[item for (cid,r),data in training.items() if cid!=c['id'] and r==rep for item in data];alpha=fit_alpha(loo)
        mean_prediction=statistics.mean(d*conf for d,p,conf in field.values.values());constant_training=statistics.mean(target for prediction,target in loo)*scale
        for method,f,weight in [('none',None,1.),('real',field,1.),('query_mean',Constant(mean_prediction),1.),('fixed_diagonal_10pct',Constant(.1*scale),1.),('training_mean_true_residual',Constant(constant_training),1.),('calibrated_alpha_loo',Scaled(field,alpha),1.),('relative_residual',Scaled(field,1.,True),1.),('relative_calibrated_alpha_loo',Scaled(field,alpha,True),1.)]+[(f'weighted_{w}',None,w) for w in [1.05,1.2,1.5,2.]]:
            r=SpatialSearch(mode='weighted' if method.startswith('weighted_') else 'envelope',base_weight=weight,signal='detour').search(q,f)
            assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],representation=rep,method=method,alpha=alpha,pops=r['heap_pops'],unique=r['unique'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost']))
        print(c['id'],rep,'cost/scalar controls',flush=True)
    summary={}
    for rep,method in sorted({(r['representation'],r['method']) for r in rows}):
        rr=[r for r in rows if r['representation']==rep and r['method']==method];summary[rep+'/'+method]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,{'scope':'Development-only controls. Trust coefficient learned by residual prediction MSE, not search-outcome tuning. Every evaluation map excluded from its coefficient fit. Final all-development coefficients saved for validation/frozen tests. Offline reference cost generation excluded from search timing and explicitly used only for training diagnostics.','full_development_alpha':coefficients,'summary':summary,'runs':rows});print(summary);print('fitted alpha',coefficients)
if __name__=='__main__':main()
