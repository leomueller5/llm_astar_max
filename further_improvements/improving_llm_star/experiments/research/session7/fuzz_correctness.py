"""Correctness stress outside benchmark geometry; zero API calls, no tuning."""
import argparse,random,math
from common import dump
from oracle import remaining_costs
from llmastar.research.spatial_guidance import SpatialSearch,RegionField
from llmastar.research.geometry import SegmentGridGraph
from shapely.geometry import LineString
from shapely.strtree import STRtree

def main():
    p=argparse.ArgumentParser();p.add_argument('--maps',type=int,default=240);p.add_argument('--output',required=True);a=p.parse_args();runs=[];edge_count=0
    for i in range(a.maps):
        rng=random.Random(20261120000+i);width=rng.randrange(9,24);height=rng.randrange(9,26);x0=rng.randrange(-12,4);y0=rng.randrange(-12,4);walls={'horizontal_barriers':[],'vertical_barriers':[]};fractional=i%4==0
        for j in range(rng.randrange(1,10)):
            axis=rng.randrange(2);size=height if axis else width;other=width if axis else height;offset=y0 if axis else x0;base=x0 if axis else y0
            fixed=offset+rng.randrange(1,size-1)+(.5 if fractional else 0);lo=base+rng.randrange(0,max(1,other-3));hi=base+rng.randrange(int(lo-base)+1,other)
            walls['horizontal_barriers' if axis else 'vertical_barriers'].append([fixed,lo,hi])
        q=dict(range_x=[x0,x0+width],range_y=[y0,y0+height],**walls);q.update(start=[x0+1,y0+1],goal=[x0+width-2,y0+height-2]);g=SegmentGridGraph(q)
        free=[(x,y) for x in range(g.x0+1,g.x1) for y in range(g.y0+1,g.y1) if g.valid_point((x,y))]
        if len(free)<2:continue
        q.update(start=list(rng.choice(free)),goal=list(rng.choice(free)));costs,work=remaining_costs(q);reference=costs.get(tuple(q['start']));field=RegionField(q,4)
        field.update([{'region_id':r['id'],'detour':rng.random()*1000,'priority':rng.random(),'confidence':rng.random()} for r in field.regions])
        lines=[LineString([(lo,y),(hi,y)]) for y,lo,hi in q['horizontal_barriers']]+[LineString([(x,lo),(x,hi)]) for x,lo,hi in q['vertical_barriers']];tree=STRtree(lines)
        for mode in ['heuristic_envelope','envelope','focal','dual']:
            for revision in [False,True] if i<40 else [False]:
                bound=1.05 if i%2 else 2.;r=SpatialSearch(mode=mode,bound=bound,base_weight=1.).search(q,field,revision=(lambda context:field) if revision else None,revision_after=12)
                assert r['valid']==(reference is not None),(i,mode,'reachability')
                if r['valid']:
                    assert r['length']<=bound*reference+1e-7,(i,mode,'bound',r['length'],reference)
                    assert abs(r['length']-sum(math.dist(x,y) for x,y in zip(r['path'],r['path'][1:])))<1e-7
                    for x,y in zip(r['path'],r['path'][1:]):
                        assert max(abs(x[0]-y[0]),abs(x[1]-y[1]))==1
                        segment=LineString([x,y]);assert not any(segment.intersects(lines[int(k)]) for k in tree.query(segment)),(i,mode,'collision');edge_count+=1
                runs.append({'case':i,'mode':mode,'fractional':fractional,'revision':revision,'bound':bound,'valid':r['valid'],'reference_reachable':reference is not None,'cost_ratio':r['length']/reference if reference else None,'reopens':r['reopens'],'stale':r['stale'],'rebuilds':r['rebuilds']})
        if i%20==0:print(i,'stress maps checked',flush=True)
    dump(a.output,{'scope':'Independent random small nonsquare maps with negative coordinates, fractional closed walls, disconnected queries and arbitrary adversarial fields. No model calls. All paths additionally checked using independent Shapely segments/STRtree. Same-field revisions deliberately stress queue rebuilding; primary has no revisions.','maps':a.maps,'runs':runs,'independently_verified_edges':edge_count,'all_checks_passed':True});print('Verified',len(runs),'runs and',edge_count,'edges')
if __name__=='__main__':main()
