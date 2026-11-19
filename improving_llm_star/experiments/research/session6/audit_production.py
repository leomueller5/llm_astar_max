"""Independent Shapely verification and prototype/production parity, no API."""
import argparse
import gzip
import json
import math
from pathlib import Path
from hybrid import ROOT
from llmastar.research.hybrid_guidance import HybridWaypointPlanner


def verify_path(query,result):
    from shapely.geometry import LineString
    from shapely.strtree import STRtree
    if not result['valid']:return 0
    path=result['path'];assert path[0]==tuple(query['start']) and path[-1]==tuple(query['goal'])
    walls=[LineString([(a,y),(b,y)]) for y,a,b in query['horizontal_barriers']]
    walls += [LineString([(x,a),(x,b)]) for x,a,b in query['vertical_barriers']]
    tree=STRtree(walls)
    for p in path:
        assert query['range_x'][0]<p[0]<query['range_x'][1]-1
        assert query['range_y'][0]<p[1]<query['range_y'][1]-1
    cost=0.
    for a,b in zip(path,path[1:]):
        assert max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1
        assert len(tree.query(LineString([a,b]),predicate='intersects'))==0
        cost+=math.dist(a,b)
    assert abs(cost-result['length'])<1e-7
    return len(path)-1


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--expected',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    inputs=json.load(gzip.open(a.responses,'rt'))['runs'];expected={}
    if a.expected:
        d=json.load(gzip.open(a.expected,'rt'))
        expected={(r['case_id'],r['source']):r for r in d['runs'] if r['rep']==-1 and r['config']=='consensus'}
    paths=edges=parity=0
    for response in inputs:
        c=cases[response['case_id']];routes=response['meta'].get('routes') or [response['points']]
        for source,key in [('hybrid','llm'),('geometry_consensus','geometry'),('all_endpoints','all')]:
            r=HybridWaypointPlanner(source=source).search(c['query'],routes={'routes':routes})
            assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
            edges+=verify_path(c['query'],r);paths+=1
            if (c['id'],key) in expected:
                old=expected[c['id'],key]
                assert r['total_heap_pops']==old['audit']['pop'],(c['id'],key,'pops')
                assert r['total_heap_pushes']==old['audit']['push'],(c['id'],key,'pushes')
                assert abs(r['length']-old['length'])<1e-7,(c['id'],key,'length')
                parity+=1
    a.output.write_text(json.dumps({'paths_checked':paths,'independent_shapely_edges':edges,
        'prototype_parity_comparisons':parity,'scope':'Fresh complete query execution; exact path cost, boundaries, unit edges and Shapely STRtree collision predicates. No API calls.'},indent=2))
    print(a.output.read_text())


if __name__=='__main__':main()
