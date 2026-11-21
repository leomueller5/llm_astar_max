"""Secondary information-bottleneck test; no change to frozen primary."""
import argparse,math,statistics,random
from common import read_cases,dump
from oracle import remaining_costs,oracle_path
from llmastar.research.spatial_guidance import SpatialSearch
from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route
from llmastar.research.geometric_advice import portfolio

class Rectangles:
    def __init__(self,rects):self.rects=rects
    def value(self,n):return 0.,1. if any(x0<=n[0]<=x1 and y0<=n[1]<=y1 for x0,y0,x1,y1 in self.rects) else .5,1.

def cover(path,count=4,padding=2):
    if not path:return []
    rectangles=[]
    for i in range(count):
        part=path[math.floor(i*(len(path)-1)/count):math.floor((i+1)*(len(path)-1)/count)+1]
        rectangles.append([min(n[0] for n in part)-padding,min(n[1] for n in part)-padding,max(n[0] for n in part)+padding,max(n[1] for n in part)+padding])
    return rectangles

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=[]
    for c in read_cases(a.cases):
        q=c['query'];costs,work=remaining_costs(q);route=oracle_path(q,costs);geo=portfolio(q,SegmentGridGraph(q),budget=12)['geometry_best'];oracle=cover(route);geometry=cover(expand_lattice_route(geo));rng=random.Random(c['id']);randomrects=[]
        for x0,y0,x1,y1 in oracle:
            w,h=x1-x0,y1-y0;x=rng.uniform(0,max(1,q['range_x'][1]-w));y=rng.uniform(0,max(1,q['range_y'][1]-h));randomrects.append([x,y,x+w,y+h])
        for source,rects in [('none',[]),('geometry',geometry),('oracle',oracle),('random',randomrects)]:
            f=Rectangles(rects);r=SpatialSearch(mode='heuristic_envelope',base_weight=1.5,bound=2.,signal='priority').search(q,f)
            rows.append(dict(case_id=c['id'],family=c['family'],source=source,pops=r['heap_pops'],unique=r['unique'],cost_ratio=r['length']/c['optimal_cost'],rectangles=rects))
    summary={s:dict(pops=statistics.mean(r['pops'] for r in rows if r['source']==s),unique=statistics.mean(r['unique'] for r in rows if r['source']==s),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rows if r['source']==s))) for s in ['none','geometry','oracle','random']};dump(a.output,dict(scope='Secondary development-only compact adaptive rectangles rather than fixed grid IDs. Oracle/canonical paths are labelled diagnostics, never model prompts. Primary already frozen and unaffected.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
