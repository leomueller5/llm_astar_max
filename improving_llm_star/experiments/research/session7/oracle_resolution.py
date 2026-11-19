"""Different information compression, not a parameter sweep of real test results."""
import argparse,math,statistics
from common import read_cases,dump
from oracle import remaining_costs,regional_reference,oracle_path
from llmastar.research.spatial_guidance import SpatialSearch,RegionField

class SmoothField:
    def __init__(self,field):
        self.field=field;self.samples=[(tuple(r['sample']),field.values[r['id']]) for r in field.regions if r['sample'] and r['id'] in field.values];self.cache={}
    def value(self,n):
        if n not in self.cache:
            closest=sorted(((math.dist(n,p),v) for p,v in self.samples),key=lambda t:t[0])[:4]
            weights=[1/max(.5,d)**2 for d,v in closest];total=sum(weights)
            self.cache[n]=tuple(sum(w*v[i] for w,(d,v) in zip(weights,closest))/total for i in range(3)) if total else (0.,.5,0.)
        return self.cache[n]

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=[]
    for c in read_cases(a.cases):
        q=c['query'];costs,_=remaining_costs(q);path=oracle_path(q,costs)
        for side in [4,8,16]:
            field=regional_reference(q,side,costs);corridor=RegionField(q,side);hit={corridor.identifier(n) for n in path}
            corridor.update([{'region_id':r['id'],'priority':float(r['id'] in hit),'detour':0.,'confidence':1.} for r in corridor.regions])
            for name,f,signal,weight in [('detour',field,'detour',1.),('smooth_detour',SmoothField(field),'detour',1.),('corridor',corridor,'priority',1.5)]:
                for mode in ['envelope','focal'] if name=='corridor' else ['envelope']:
                    r=SpatialSearch(mode=mode,base_weight=weight,signal=signal).search(q,f)
                    rows.append(dict(case_id=c['id'],family=c['family'],method=f'{name}{side}_{mode}',pops=r['heap_pops'],unique=r['unique'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost']))
        print(c['id'],'resolution control',flush=True)
    summary={}
    for m in sorted({r['method'] for r in rows}):
        rr=[r for r in rows if r['method']==m];summary[m]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='Development only, oracle diagnostics. All path/cost labels offline, no real API requests. Smoothing work included in search timing but oracle generation excluded and labelled.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
