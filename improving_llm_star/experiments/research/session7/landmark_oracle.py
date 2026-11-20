import argparse,math,statistics,random
from common import read_cases,dump
from oracle import remaining_costs,anchor
from landmarks import choose_landmarks,LandmarkCostField
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);p.add_argument('--extension',choices=['via','difference'],default='via');a=p.parse_args();rows=[]
    for c in read_cases(a.cases):
        q=c['query'];points=choose_landmarks(q);costs,work=remaining_costs(q);h=anchor(q,'cut');rng=random.Random(c['id']);scale=math.hypot(q['range_x'][1],q['range_y'][1])
        for source,cc in [('none',{}),('geometry',{k:h(n) for k,n in points.items()}),('oracle',{k:costs.get(n,math.inf) for k,n in points.items()}),('noisy_oracle',{k:costs.get(n,math.inf)*rng.uniform(.8,1.2) for k,n in points.items()}),('random',{k:h(n)+rng.random()*.3*scale for k,n in points.items()})]:
            for visible in [False,True]:
                f=LandmarkCostField(q,points,cc,visibility=visible,extension=a.extension) if source!='none' else None;r=SpatialSearch(mode='heuristic_envelope',base_weight=1).search(q,f)
                rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],source=source,visibility=visible,pops=r['heap_pops'],unique=r['unique'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost'],visibility_probes=f.probes if f else 0,landmarks=len(points)))
        print(c['id'],'landmark information ceiling',flush=True)
    summary={}
    for source,visible in sorted({(r['source'],r['visibility']) for r in rows}):
        rr=[r for r in rows if (r['source'],r['visibility'])==(source,visible)];summary[source+'/'+str(visible)]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(extension=a.extension,scope='Development oracle diagnostic only. Landmark selection uses geometry only; oracle remaining costs computed offline and never sent to model. Dense per-node visibility overhead counted in search, landmark/reference preprocessing separately excluded in this pilot.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
