"""Verify every saved final path with independent Shapely predicates."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from audit_production import verify_path


def geometry_key(q):
    value={k:q[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
    for k in ['horizontal_barriers','vertical_barriers']:value[k]=sorted(value[k])
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--paths',type=Path,required=True);p.add_argument('--development',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    seen=set()
    for path in a.development:
        for c in json.load(gzip.open(path,'rt')):seen.add(geometry_key(c['query']))
    overlap={geometry_key(c['query']) for c in cases.values()}&seen
    assert not overlap,'Map geometry leakage detected'
    paths=json.load(gzip.open(a.paths,'rt'));count=edges=0
    for row in paths:
        if not row['valid']:continue
        q=cases[row['case_id']]['query'];result={'valid':True,'length':row['length'],
            'path':[tuple(p) for p in row['path']]}
        edges+=verify_path(q,result);count+=1
    report={'valid_paths_independently_checked':count,'independent_unit_edges':edges,
            'heldout_cases':len(cases),'heldout_map_geometries':len({geometry_key(c['query']) for c in cases.values()}),
            'development_geometry_overlap':len(overlap),
            'predicate':'Shapely STRtree intersects on original closed line segments, plus bounds and exact unit-step cost'}
    a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
