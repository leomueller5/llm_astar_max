"""New split seeds; guidance input contains no reference paths/costs."""
import sys,json,gzip,random,math,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'session4'))
from maps import make_map,geometry_hash,ROOT
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
FAMILIES=['open','random_walls','rooms','braided_maze','tree_maze','serpentine','u_traps','nested','competing_corridors','bottlenecks']
BASE={'development':5510000,'validation':6610000,'fresh':7710000}


def generate(split,maps_per_family=1,queries=1,sizes=None):
    sizes=sizes or ([40,56] if split=='development' else [48,64] if split=='validation' else [60,84]);cases=[]
    for fi,family in enumerate(FAMILIES):
        for mi in range(maps_per_family):
            seed=BASE[split]+fi*10000+mi;rng=random.Random(seed);size=sizes[(fi+mi)%len(sizes)];q=make_map(family,size,seed,index=3+mi)
            g=SegmentGridGraph(q)
            for qi in range(queries):
                for _ in range(500):
                    s=(rng.randrange(1,g.x1),rng.randrange(1,g.y1));t=(rng.randrange(1,g.x1),rng.randrange(1,g.y1))
                    if not g.valid_point(s) or not g.valid_point(t) or math.dist(s,t)<size/3:continue
                    query=dict(q,start=list(s),goal=list(t));r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(query,[],g)
                    if r['valid']:break
                else:raise RuntimeError('Could not sample reachable query')
                cases.append(dict(id=f's5_{seed}_{qi}',map_id=f's5_{seed}',family=family,split=split,size=size,geometry_hash=geometry_hash(query),query=query,optimal_cost=r['length']))
    return cases

def main():
    p=argparse.ArgumentParser();p.add_argument('--split',default='development',choices=BASE);p.add_argument('--maps',type=int,default=1);p.add_argument('--queries',type=int,default=1);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    cases=generate(a.split,a.maps,a.queries);a.output.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(a.output,'wt') as f:json.dump(cases,f)
    print(len(cases),'cases',len(set(c['geometry_hash'] for c in cases)),'maps')
if __name__=='__main__':main()
