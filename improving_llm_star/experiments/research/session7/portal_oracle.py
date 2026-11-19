import argparse,random,statistics,math
from common import read_cases,dump
from oracle import remaining_costs,oracle_path
from portals import candidates,PortalField,geometric_choices,oracle_choices
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=[]
    for c in read_cases(a.cases):
        q=c['query'];cs=candidates(q);costs,work=remaining_costs(q);path=oracle_path(q,costs);geo=geometric_choices(cs);oracle=oracle_choices(cs,path);rng=random.Random(c['id']);randomc={r['id']:(rng.choice(['low','high']),1.) for r in cs}
        for source,choice in [('none',None),('geometry',geo),('oracle',oracle),('random',randomc)]:
            for mode in ['envelope','dual','focal']:
                f=PortalField(q,choice,cs) if choice is not None else None;r=SpatialSearch(mode=mode,signal='detour',base_weight=1.5).search(q,f)
                rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],source=source,mode=mode,pops=r['heap_pops'],unique=r['unique'],seconds=r['total_seconds'],cost_ratio=r['length']/c['optimal_cost'],choices=choice,candidates=cs))
        print(c['id'],'persistent portal ceiling',flush=True)
    summary={}
    for key in sorted({(r['source'],r['mode']) for r in rows}):
        rr=[r for r in rows if (r['source'],r['mode'])==key];summary['/'.join(key)]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),ms=1000*statistics.mean(r['seconds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='Development-only oracle obstacle-side assessment. Labels from a canonical optimal path, no real API. Conditional advice active only before crossing the obstacle plane; not globally switched targets.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
