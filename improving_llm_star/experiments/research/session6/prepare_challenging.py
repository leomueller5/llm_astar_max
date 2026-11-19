"""Fresh independent seeds/sizes, shared with no algorithm or guidance provider."""
import argparse
import gzip
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from hybrid import ROOT

sys.path.insert(0,str(ROOT/'experiments/research/session4'))
from maps import make_map,geometry_hash
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch

FAMILIES=['open','random_walls','rooms','braided_maze','tree_maze','serpentine',
          'u_traps','nested','competing_corridors','bottlenecks']
BASE={'development':8610000,'validation':9710000,'heldout':10810000}
SIZES={'development':[72,104],'validation':[80,112],'heldout':[88,120]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--split',choices=BASE,default='development')
    p.add_argument('--maps',type=int,default=2);p.add_argument('--queries',type=int,default=1)
    p.add_argument('--families',nargs='+',default=FAMILIES)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frozen-manifest',type=Path)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    if a.split=='heldout' and (not a.frozen_manifest or not a.frozen_manifest.is_file()
        or json.loads(a.frozen_manifest.read_text()).get('status')!='frozen'):
        raise ValueError('Freeze candidate before held-out generation')
    cases=[]
    for family in a.families:
        fi=FAMILIES.index(family)
        for mi in range(a.maps):
            seed=BASE[a.split]+fi*10000+mi;rng=random.Random(seed)
            size=SIZES[a.split][mi%2];q=make_map(family,size,seed,index=6+mi)
            graph=SegmentGridGraph(q)
            for qi in range(a.queries):
                for _ in range(1000):
                    s=(rng.randrange(1,graph.x1),rng.randrange(1,graph.y1))
                    t=(rng.randrange(1,graph.x1),rng.randrange(1,graph.y1))
                    if not graph.valid_point(s) or not graph.valid_point(t) or math.dist(s,t)<size/3:continue
                    query=dict(q,start=list(s),goal=list(t))
                    reference=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(query,[],graph)
                    if reference['valid']:break
                else:raise RuntimeError('Reachable query sampling exhausted')
                cases.append({'id':f's6_{seed}_{qi}','map_id':f's6_{seed}',
                    'family':family,'split':a.split,'query':query,'optimal_cost':reference['length'],
                    'geometry_hash':geometry_hash(query),'source':'independently_seeded_synthetic_geometry'})
            print(family,size,seed,flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(a.output,'wt') as f:json.dump(cases,f)
    a.output.with_suffix('.manifest.json').write_text(json.dumps({'generator':'session6/prepare_challenging.py',
        'base_seeds':BASE,'sizes':SIZES,'families':FAMILIES,
        'heldout_policy':'No generation/reference search until frozen configuration exists',
        'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':main()
