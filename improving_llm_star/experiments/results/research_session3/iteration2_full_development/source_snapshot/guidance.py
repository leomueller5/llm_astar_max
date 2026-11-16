"""Session-3 waypoint selection, bounded potentials, and verified prefix seeding."""
import heapq,math
from time import perf_counter
from .geometry import SegmentGridGraph,expand_lattice_route
from .efficient import EfficientCertificateSearch,compress_collinear
from .search import octile


class WaypointGuidanceSearch:
    def __init__(self,mode='seed',use_waypoints=True,filtering='rank',max_candidates=8,
                 max_seeds=1,potential_weight=1.5,witness=True,seed_source='llm'):
        if mode not in ['seed','chain','potential','tie','attract'] or filtering not in ['none','geometric','rank','visible'] or seed_source not in ['llm','geometry']:
            raise ValueError('Unknown guidance mode')
        if max_candidates<1 or max_seeds<1 or not 1<=potential_weight<=2:raise ValueError('Invalid budget/weight')
        self.mode=mode;self.enabled=use_waypoints;self.filtering=filtering;self.max_candidates=max_candidates
        self.max_seeds=max_seeds;self.potential_weight=potential_weight;self.witness=witness;self.source=seed_source

    def search(self,query,waypoints,graph=None):
        graph=graph or SegmentGridGraph(query);began=perf_counter();start,goal=tuple(query['start']),tuple(query['goal'])
        geom=EfficientCertificateSearch(segment_mode='analytic',use_waypoints=False,witness=self.witness,prepare_only=True,reuse_validation=True).search(query,[],graph) if self.witness else None
        if geom and geom['valid']:
            geom.update(guidance_accepted=0,guidance_rejected=0,guidance_candidates=0,guidance_seconds=0.,fresh_guidance=False)
            return geom
        prep=perf_counter();raw=[];seen={start,goal}
        if self.enabled:
            values=waypoints
            if self.source=='geometry':
                values=[]
                if graph.indexed:
                    for x,lo,hi in graph.vertical:values.extend([(x,lo-1),(x,hi+1)])
                    for y,lo,hi in graph.horizontal:values.extend([(lo-1,y),(hi+1,y)])
                values += [(round(start[0]+(goal[0]-start[0])*q),round(start[1]+(goal[1]-start[1])*q)) for q in [.25,.5,.75]]
            for p in values:
                if not isinstance(p,(tuple,list)) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and v==int(v) for v in p):continue
                p=tuple(p)
                if p not in seen:seen.add(p);raw.append(p)
        candidates=[]
        for t in raw:
            if self.filtering!='none' and not graph.valid_point(t):continue
            if self.filtering in ['rank','visible'] and octile(start,t)+octile(t,goal)>1.5*max(1,octile(start,goal)):continue
            candidates.append(t)
        if self.filtering in ['rank','visible']:
            candidates.sort(key=lambda t:(octile(start,t)+2*math.dist(t,goal),t))
        candidates=candidates[:self.max_candidates]
        accepted=0;seed_paths={};g={start:0.};parents={start:start};closed={};path=[]
        if self.enabled and self.mode in ['seed','chain']:
            proposals=[]
            if self.mode=='chain':
                chain=compress_collinear([start]+raw+[goal]);a=start;corners=[start];cost=0.
                for t in chain[1:self.max_candidates+1]:
                    if t==goal:break
                    if not graph.valid_point(t):continue
                    route=graph.lattice_segment(a,t)
                    if route is None:break
                    cost+=octile(a,t);corners+=route[1:];a=t
                    proposals.append((cost+2*math.dist(t,goal),t,cost,list(corners)))
            else:
                for t in candidates:
                    if not graph.valid_point(t):continue
                    route=graph.lattice_segment(start,t)
                    if route is not None:proposals.append((octile(start,t)+2*math.dist(t,goal),t,octile(start,t),route))
            proposals.sort(key=lambda item:(item[0],item[1]))
            for score,t,cost,route in proposals[:self.max_seeds]:
                # A low score predicts actual progress; retain start OPEN regardless.
                if score>=2*math.dist(start,goal)-1e-10:continue
                g[t]=cost;parents[t]=start;seed_paths[t]=route;accepted+=1
        selected=candidates[:1]
        if self.filtering=='visible' and self.mode not in ['seed','chain']:
            selected=[t for t in candidates if graph.valid_point(t) and graph.lattice_segment(start,t)][:1]
        target=selected[0] if selected and self.enabled else None
        if target and self.mode not in ['seed','chain']:accepted=1
        target_goal=math.dist(target,goal) if target else 0.
        progress=max(0,min(1,(math.dist(start,goal)-target_goal)/max(1,math.dist(start,goal)))) if target else 0.
        confidence=progress/(1+max(0,octile(start,target)+octile(target,goal)-octile(start,goal))/max(1,octile(start,goal))) if target else 0.
        fast=self.mode in ['seed','chain'] or target is None
        def heuristic(n):
            h=math.dist(n,goal)
            if target and self.mode=='potential':return min(2*h,math.dist(n,target)+self.potential_weight*target_goal)
            if target and self.mode=='attract':
                # Bounded immediate confidence, with the final goal retaining 2h.
                return 2*h-confidence*max(0,h-math.dist(n,target))
            return 2*h
        def entry(n):
            tie=math.dist(n,target) if target and self.mode=='tie' else 0.
            return g[n]+heuristic(n),tie,n,g[n]
        queue=[(g[n]+2*math.dist(n,goal),n,g[n]) if fast else entry(n) for n in g];heapq.heapify(queue)
        preprocessing=perf_counter()-began;guidance_time=perf_counter()-prep
        pops=expanded=stale=duplicates=reopens=0
        while queue:
            item=heapq.heappop(queue);pops+=1
            if fast:_,node,old=item
            else:_,_,node,old=item
            if old!=g[node]:stale+=1;duplicates+=int(node in closed);continue
            if node in closed and old>=closed[node]:duplicates+=1;continue
            reopens+=int(node in closed);closed[node]=old;expanded+=1
            if node==goal:
                tail=[];n=node
                while n!=start and n not in seed_paths:tail.append(n);n=parents[n]
                prefix=expand_lattice_route(seed_paths[n]) if n in seed_paths else [start]
                path=prefix+list(reversed(tail));break
            for other,cost in graph.adj.get(node,[]):
                new=old+cost
                if new<g.get(other,math.inf)-1e-12:
                    g[other]=new;parents[other]=node;seed_paths.pop(other,None);heapq.heappush(queue,(new+2*math.dist(other,goal),other,new) if fast else entry(other))
        valid=graph.valid_point(start) and graph.valid_point(goal) and bool(path) and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        if not valid:path=[]
        return dict(path=path,length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None,
           valid=valid,operation=pops,unique=len(closed),expanded=expanded,stale=stale,duplicates=duplicates,reopens=reopens,
           rebuilds=0,storage=len(g),switches=[],alpha_events=[],preprocess_seconds=preprocessing,
           search_seconds=perf_counter()-began-preprocessing,total_seconds=perf_counter()-began,certified_early_return=False,
           guidance_candidates=len(raw),guidance_accepted=accepted,guidance_rejected=len(raw)-accepted,
           guidance_seconds=guidance_time,fresh_guidance=accepted>0,visibility_edge_checks=0)
