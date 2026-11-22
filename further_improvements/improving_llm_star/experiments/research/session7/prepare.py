"""Independent Session7 maps; use references only for evaluation, never prompts."""
import argparse,hashlib,random,math,sys
from common import ROOT,RESULTS,read_cases,dump
sys.path.insert(0,str(ROOT/'experiments/research/session4'))
from maps import make_map,geometry_hash
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.incumbent import IncumbentSearch
FAMILIES=['open','random_walls','rooms','braided_maze','tree_maze','serpentine','u_traps','nested','competing_corridors','bottlenecks']
def main():
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','validation','heldout'],required=True);p.add_argument('--maps',type=int,default=2);p.add_argument('--queries',type=int,default=1);p.add_argument('--frozen',type=str);p.add_argument('--seed-base',type=int);p.add_argument('--sizes',type=int,nargs='+');p.add_argument('--output',required=True);a=p.parse_args()
    from pathlib import Path
    if Path(a.output).exists():raise FileExistsError(a.output)
    if a.split=='heldout':
        import json
        if not a.frozen or json.loads(Path(a.frozen).read_text()).get('status')!='frozen':raise ValueError('Freeze before generating test maps')
    base=a.seed_base if a.seed_base is not None else {'development':13110000,'validation':14210000,'heldout':15310000}[a.split];sizes=a.sizes or {'development':[72,104],'validation':[80,112],'heldout':[94,126,158,190]}[a.split];cases=[]
    for fi,family in enumerate(FAMILIES):
        for mi in range(a.maps):
            seed=base+fi*10000+mi;rng=random.Random(seed);size=sizes[mi%len(sizes)];q=make_map(family,size,seed,index=6+mi);g=SegmentGridGraph(q)
            for qi in range(a.queries):
                for _ in range(2000):
                    s=(rng.randrange(1,g.x1),rng.randrange(1,g.y1));t=(rng.randrange(1,g.x1),rng.randrange(1,g.y1))
                    if not g.valid_point(s) or not g.valid_point(t) or math.dist(s,t)<size/3:continue
                    query=dict(q,start=list(s),goal=list(t));r=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(query,[],g)
                    if r['valid']:break
                else:raise RuntimeError('Sampling exhausted')
                cases.append({'id':f's7_{seed}_{qi}','map_id':f's7_{seed}','family':family,'split':a.split,'query':query,'geometry_hash':geometry_hash(query),'optimal_cost':r['length'],'source':'fresh_independent_synthetic_geometry'})
            print(a.split,family,size,flush=True)
    dump(a.output,cases);dump(str(a.output)+'.manifest.json',{'split':a.split,'base':base,'sizes':sizes,'families':FAMILIES,'maps':a.maps,'queries':a.queries,'sha256':hashlib.sha256(Path(a.output).read_bytes()).hexdigest()})
if __name__=='__main__':main()
