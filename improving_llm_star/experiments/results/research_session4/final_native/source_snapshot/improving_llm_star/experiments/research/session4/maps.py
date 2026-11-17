"""Algorithm-independent challenging map families, split by seed and size.

Solutions/oracle guidance are created only after map/start-goal generation and are
explicitly outside any deployable planner. No map embeds a proposed solution.
"""
import sys,random,math,json,gzip,argparse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark import ROOT
from llmastar.research.strategic.abstraction import RasterGridGraph
from llmastar.research.incumbent import IncumbentSearch
from llmastar.research.efficient import compress_collinear

FAMILIES=['open','random_walls','rooms','braided_maze','tree_maze','serpentine','u_traps','nested','competing_corridors','bottlenecks','disconnected']
BASES={'development':4110000,'validation':4220000,'fresh':4330000}
SIZES={'development':[64,128,256],'validation':[80,160,320],'fresh':[96,192,384]}


def _wall_with_gap(walls,fixed,lo,hi,gap,half=1):
    if gap-half-1>=lo:walls.append([fixed,lo,gap-half-1])
    if gap+half+1<=hi:walls.append([fixed,gap+half+1,hi])


def make_map(family,size,seed,index=0):
    rng=random.Random(seed);w=size;h=max(25,size-9-2*index);hs=[];vs=[]
    if family=='random_walls':
        for i in range(max(6,size//8)):
            if rng.random()<.5:
                lo=rng.randrange(1,w-5);hs.append([rng.randrange(3,h-2),lo,min(w,lo+rng.randrange(4,max(5,w//3)))])
            else:
                lo=rng.randrange(1,h-5);vs.append([rng.randrange(3,w-2),lo,min(h,lo+rng.randrange(4,max(5,h//3)))])
    elif family in ['rooms','braided_maze','tree_maze']:
        cell=16 if family=='rooms' else 8
        nx=max(2,w//cell);ny=max(2,h//cell);xs=[round(i*(w+1)/nx) for i in range(nx+1)];ys=[round(i*(h+1)/ny) for i in range(ny+1)]
        openings=set();seen={(0,0)};stack=[(0,0)]
        while stack:
            a=stack[-1];options=[(a[0]+dx,a[1]+dy) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
            options=[b for b in options if 0<=b[0]<nx and 0<=b[1]<ny and b not in seen]
            if not options:stack.pop();continue
            b=rng.choice(options);openings.add(frozenset([a,b]));seen.add(b);stack.append(b)
        for x in range(nx):
            for y in range(ny):
                for dx,dy in [(1,0),(0,1)]:
                    b=x+dx,y+dy
                    if b[0]>=nx or b[1]>=ny:continue
                    pair=frozenset([(x,y),b]);opened=pair in openings or rng.random()<(0.55 if family=='rooms' else .18 if family=='braided_maze' else 0.)
                    if dx:
                        lo,hi=ys[y],ys[y+1];fixed=xs[x+1]
                        if opened:_wall_with_gap(vs,fixed,lo,hi,rng.randrange(lo+2,hi-1),0 if family!='rooms' else 1)
                        else:vs.append([fixed,lo,hi])
                    else:
                        lo,hi=xs[x],xs[x+1];fixed=ys[y+1]
                        if opened:_wall_with_gap(hs,fixed,lo,hi,rng.randrange(lo+2,hi-1),0 if family!='rooms' else 1)
                        else:hs.append([fixed,lo,hi])
    elif family=='serpentine':
        spacing=max(8,h//8)
        for i,y in enumerate(range(spacing,h-2,spacing)):
            hs.append([y,0,w-4] if i%2==0 else [y,4,w+1])
    elif family=='u_traps':
        for i,x in enumerate(range(5,w-14,18)):
            bottom=rng.randrange(4,max(5,h//3));top=min(h-3,bottom+rng.randrange(max(6,h//3),max(7,2*h//3)))
            width=rng.randrange(6,12);vs.extend([[x,bottom,top],[x+width,bottom,top]])
            hs.append([bottom if i%2==0 else top,x,x+width])
    elif family=='nested':
        for i,inset in enumerate(range(5,min(w,h)//2-5,7)):
            left,right,bottom,top=inset,w+1-inset,inset,h+1-inset;side=(i+rng.randrange(4))%4
            if side==0:_wall_with_gap(vs,left,bottom,top,(bottom+top)//2,1)
            else:vs.append([left,bottom,top])
            if side==1:_wall_with_gap(vs,right,bottom,top,(bottom+top)//2,1)
            else:vs.append([right,bottom,top])
            if side==2:_wall_with_gap(hs,bottom,left,right,(left+right)//2,1)
            else:hs.append([bottom,left,right])
            if side==3:_wall_with_gap(hs,top,left,right,(left+right)//2,1)
            else:hs.append([top,left,right])
    elif family=='competing_corridors':
        left,right=5,w-4;ys=[1,h//3,2*h//3,h]
        hs.extend([[ys[1],left,right],[ys[2],left,right]])
        for band in range(3):
            n=rng.randrange(2,9);bottom,top=ys[band],ys[band+1]
            for j in range(n):
                x=left+round((j+1)*(right-left)/(n+1));gap=bottom+2 if j%2 else top-2
                _wall_with_gap(vs,x,bottom,top,gap,0)
    elif family=='bottlenecks':
        for i,x in enumerate(range(max(10,w//5),w-3,max(10,w//5))):
            gap=3 if i%2 else h-2;_wall_with_gap(vs,x,0,h+1,gap,0)
    elif family=='disconnected':vs.append([w//2,0,h+1])
    return {'range_x':[0,w+2],'range_y':[0,h+2],'horizontal_barriers':hs,'vertical_barriers':vs}


def geometry_hash(q):
    d={k:q[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
    for k in ['horizontal_barriers','vertical_barriers']:d[k]=sorted(d[k])
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()


def generate(split='development',maps_per_family=2,queries_per_map=4,sizes=None,families=None):
    cases=[];sizes=sizes or SIZES[split];families=families or FAMILIES
    for fi,family in enumerate(families):
        for mi in range(maps_per_family):
            size=sizes[mi%len(sizes)];seed=BASES[split]+fi*10000+mi;rng=random.Random(seed);q=make_map(family,size,seed,mi)
            graph=RasterGridGraph(q);map_hash=geometry_hash(q)
            for qi in range(queries_per_map):
                for attempt in range(400):
                    start=(rng.randrange(1,graph.width+1),rng.randrange(1,graph.height+1));goal=(rng.randrange(1,graph.width+1),rng.randrange(1,graph.height+1))
                    if not graph.valid_point(start) or not graph.valid_point(goal):continue
                    if math.dist(start,goal)<min(graph.width,graph.height)/3:continue
                    if family=='disconnected' and (start[0]<size//2)==(goal[0]<size//2):continue
                    query=dict(q,start=list(start),goal=list(goal))
                    oracle=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(query,[],graph)
                    if oracle['valid'] or family=='disconnected':break
                else:raise RuntimeError(f'Unable to sample {family}:{seed}')
                cases.append({'id':f's4_{seed}_{qi}','map_id':f's4_{seed}','geometry_hash':map_hash,'family':family,'split':split,'size':size,'query':query,
                    'oracle_path':oracle['path'],'oracle_waypoints':compress_collinear(oracle['path']),'optimal_cost':oracle['length'],'source':'generated_map_with_explicit_reference_oracle'})
            print(f'{family} size{size} seed{seed}: {queries_per_map} queries',flush=True)
    return cases


def main():
    p=argparse.ArgumentParser();p.add_argument('--split',choices=BASES,default='development');p.add_argument('--maps-per-family',type=int,default=2);p.add_argument('--queries',type=int,default=4);p.add_argument('--sizes',nargs='+',type=int);p.add_argument('--families',nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    cases=generate(a.split,a.maps_per_family,a.queries,a.sizes,a.families)
    with gzip.open(a.output,'wt') as f:f.write(json.dumps(cases,separators=(',',':')))
    print(len(cases),'cases')
if __name__=='__main__':main()
