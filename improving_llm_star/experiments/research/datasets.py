"""Procedural map-disjoint suites. Waypoints are fixtures, never called LLM output."""
import math
import random
from llmastar.research.search import GridGraph, SearchConfig, WaypointSearch

FAMILIES=['open','random_walls','dense','corridors','maze','dead_ends','enclosed','disconnected']


def make_map(family,seed):
    rng=random.Random(seed);w=rng.choice([32,40,48]);h=rng.choice([24,30,36])
    hs=[];vs=[]
    if family in ['random_walls','dense']:
        for _ in range(5 if family=='random_walls' else 18):
            if rng.random()<.5:
                a=rng.randrange(1,w-4);hs.append([rng.randrange(2,h-2),a,min(w-1,a+rng.randrange(3,w//2))])
            else:
                a=rng.randrange(1,h-4);vs.append([rng.randrange(2,w-2),a,min(h-1,a+rng.randrange(3,h//2))])
    elif family=='corridors':
        for j,y in enumerate(range(6,h-2,6)):
            hs.append([y,0,w-4] if j%2==0 else [y,4,w])
    elif family=='maze':
        nx=rng.choice([8,10,12]);ny=rng.choice([6,8,10]);w,h=2*nx,2*ny
        seen={(0,0)};stack=[(0,0)];openings=set()
        while stack:
            a=stack[-1];neighbors=[(a[0]+dx,a[1]+dy) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
            choices=[b for b in neighbors if 0<=b[0]<nx and 0<=b[1]<ny and b not in seen]
            if not choices:stack.pop();continue
            b=rng.choice(choices);openings.add(frozenset([a,b]));seen.add(b);stack.append(b)
        for x in range(nx):
            for y in range(ny):
                if x<nx-1 and frozenset([(x,y),(x+1,y)]) not in openings:vs.append([2*x+2,2*y,2*y+2])
                if y<ny-1 and frozenset([(x,y),(x,y+1)]) not in openings:hs.append([2*y+2,2*x,2*x+2])
    elif family=='dead_ends':
        for x in range(5,w-7,8):
            bottom=rng.randrange(3,h//2);top=min(h-3,bottom+h//2)
            vs.extend([[x,bottom,top],[x+5,bottom,top]])
            hs.append([bottom if x%2 else top,x,x+5])
    elif family=='enclosed':
        x,y=w//2,h//2;vs.extend([[x-3,y-3,y+3],[x+3,y-3,y+3]])
        hs.extend([[y-3,x-3,x+3],[y+3,x-3,x+3]])
    elif family=='disconnected':vs.append([w//2,0,h])
    return {'range_x':[0,w+1],'range_y':[0,h+1],'horizontal_barriers':hs,'vertical_barriers':vs}


def generate(split,maps_per_family=4,queries_per_map=2):
    base={'development':110000,'validation':220000,'test':330000}[split]
    cases=[]
    for fi,family in enumerate(FAMILIES):
        for mi in range(maps_per_family):
            seed=base+fi*1000+mi;rng=random.Random(seed);q=make_map(family,seed)
            graph=GridGraph(q);free=[p for p,edges in graph.adj.items() if edges]
            for qi in range(queries_per_map):
                path=None
                for attempt in range(100):
                    start,goal=rng.sample(free,2)
                    if math.dist(start,goal)<min(graph.x1,graph.y1)/3:continue
                    if family=='disconnected' and (start[0]<graph.x1//2)==(goal[0]<graph.x1//2):continue
                    query=dict(q,start=list(start),goal=list(goal))
                    optimum=WaypointSearch(SearchConfig(alpha=0,goal_weight=1)).search(query,[start,goal],graph)
                    if family=='disconnected' or optimum['valid']:
                        path=optimum['path'];break
                if path is None:raise RuntimeError('Could not generate query')
                useful=[start]+([path[len(path)//3],path[2*len(path)//3]] if len(path)>4 else [])+[goal]
                far=max(free,key=lambda p:math.dist(start,p)+math.dist(p,goal))
                walls=q['horizontal_barriers']+q['vertical_barriers']
                blocked=None
                if q['horizontal_barriers']:
                    y,a,b=q['horizontal_barriers'][0];blocked=((a+b)//2,y)
                elif q['vertical_barriers']:
                    x,a,b=q['vertical_barriers'][0];blocked=(x,(a+b)//2)
                else:blocked=(0,graph.y1//2)
                if family=='enclosed':blocked=(graph.x1//2,graph.y1//2)
                for quality,pts in [('useful',useful),('misleading',[start,far,goal]),
                                    ('blocked_or_unreachable',[start,blocked,goal]),('none',[start,goal])]:
                    import json
                    cases.append({'id':f'synthetic_{seed}_{qi}_{quality}','map_id':f'synthetic_{seed}',
                                  'split':split,'family':family,'source':'deterministic_fixture_'+quality,
                                  'query':query,'points':pts,'response':'Generated Path: '+json.dumps(pts),'parse_fallback':False})
    return cases
