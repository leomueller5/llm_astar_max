"""Build development/validation cases without opening held-out query geometry."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

from hybrid import ROOT
sys.path.insert(0,str(ROOT / 'experiments/research'))
from benchmark import finite_json
from llmastar.research.incumbent import IncumbentSearch


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--split',choices=['development','validation','heldout'],default='development')
    p.add_argument('--maps',type=int,default=8)
    p.add_argument('--queries',type=int,default=2)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frozen-manifest',type=Path)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    if a.split=='heldout' and not a.frozen_manifest:
        raise ValueError('Held-out evaluation requires a frozen configuration manifest')
    split=json.loads((ROOT/'experiments/results/research_session6/team_split.json').read_text())
    ids=sorted(split[a.split],key=lambda i:hashlib.sha256(f'case-order-{i}'.encode()).hexdigest())[:a.maps]
    maps=json.loads((ROOT/'dataset/environment_100_60.json').read_text())
    cases=[]
    for m in maps:
        if m['id'] not in ids:
            continue
        for j,sg in enumerate(m['start_goal'][:a.queries]):
            q={k:m[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
            q=dict(q,start=sg[0],goal=sg[1])
            ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[])
            cases.append({'id':f'team_{m["id"]}_{j}','map_id':f'team_{m["id"]}',
                'family':'team_random_walls','split':a.split,'query':q,
                'optimal_cost':ref['length'],'reference_valid':ref['valid']})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(a.output,'wt') as f:
        json.dump(finite_json(cases),f)
    print(json.dumps({'cases':len(cases),'maps':len(ids),'solvable':sum(c['reference_valid'] for c in cases)}))


if __name__=='__main__':
    main()
