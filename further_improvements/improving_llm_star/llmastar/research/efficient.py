"""Reachability-first, budgeted waypoint certificate evaluation (session 2)."""
import math
from time import perf_counter
from .geometry import IndexedGridGraph,expand_lattice_route
from .incumbent import IncumbentSearch,obstacle_lower_bound
from .search import octile


class EfficientCertificateSearch:
    def __init__(self,visibility_budget=4096,repair_radius=1,use_waypoints=True,
                 gate='none',certificate_ratio=1.0,uncertified='discard',
                 lower_bound=True,ordering='forward',segment_mode='unit',segment_budget=256,compress=False,pivot_only=False,chain_only=False,prepare_only=False,fallback_engine='legacy',reuse_validation=False,witness=False):
        if visibility_budget<0 or repair_radius not in [0,1] or certificate_ratio<1:
            raise ValueError('Invalid certificate settings')
        if gate not in ['none','detour','distance','sparse'] or uncertified not in ['discard','accept_bound','prune','frontier'] or ordering not in ['forward','goal_first']:
            raise ValueError('Unknown experimental mode')
        self.budget=visibility_budget;self.radius=repair_radius;self.use_waypoints=use_waypoints
        self.gate=gate;self.ratio=certificate_ratio;self.uncertified=uncertified
        self.lower_bound=lower_bound;self.ordering=ordering
        if segment_mode not in ['unit','analytic'] or segment_budget<0:raise ValueError('Invalid segment mode/budget')
        self.segment_mode=segment_mode;self.segment_budget=segment_budget
        self.compress=compress;self.pivot_only=pivot_only
        self.chain_only=chain_only;self.prepare_only=prepare_only
        if fallback_engine not in ['legacy','lean']:raise ValueError('Unknown fallback engine')
        self.fallback_engine=fallback_engine;self.reuse_validation=reuse_validation;self.witness=witness

    def search(self,query,waypoints,graph=None):
        graph=graph or IndexedGridGraph(query);began=perf_counter()
        start,goal=tuple(query['start']),tuple(query['goal']);phases={}
        checks=calls=0;candidate_count=link_count=0;gate_skipped=False
        def segment(a,b):
            nonlocal checks,calls
            if self.segment_mode=='analytic':
                if calls>=self.segment_budget:return None
                calls+=1;return graph.lattice_segment(a,b)
            calls+=1
            for diagonal_first in [True,False]:
                p=a;path=[a]
                while p!=b:
                    if checks>=self.budget:return None
                    dx=(b[0]>p[0])-(b[0]<p[0]);dy=(b[1]>p[1])-(b[1]<p[1])
                    if not diagonal_first and dx and dy:
                        if abs(b[0]-p[0])>abs(b[1]-p[1]):dy=0
                        elif abs(b[1]-p[1])>abs(b[0]-p[0]):dx=0
                    n=p[0]+dx,p[1]+dy;checks+=1
                    if not math.isfinite(graph.cost(p,n)):break
                    path.append(n);p=n
                if p==b:return path
            return None
        valid_endpoints=graph.valid_point(start) and graph.valid_point(goal)
        tick=perf_counter();path=segment(start,goal) if valid_endpoints else None
        phases['direct_seconds']=perf_counter()-tick
        source='direct' if path else None;lower=octile(start,goal)
        costs={};parents={};points=[];links={};upper=lower if path else math.inf
        tick=perf_counter()
        if not path and valid_endpoints and self.lower_bound and getattr(graph,'indexed',True):lower=obstacle_lower_bound(graph,start,goal)
        phases['lower_bound_seconds']=perf_counter()-tick
        target=self.ratio*lower
        tick=perf_counter();witness_attempts=0
        if self.witness and not path and valid_endpoints and math.isfinite(lower) and getattr(graph,'indexed',False):
            for point in wall_witnesses(graph,start,goal,lower):
                witness_attempts+=1
                first=segment(start,point)
                if first:
                    second=segment(point,goal)
                    if second:
                        path=first+second[1:];upper=octile(start,point)+octile(point,goal);source='wall_witness';break
        phases['witness_seconds']=perf_counter()-tick
        if not path and valid_endpoints and self.use_waypoints and math.isfinite(lower):
            if self.gate=='detour' and lower<=octile(start,goal)+1e-10:gate_skipped=True
            elif self.gate=='distance' and octile(start,goal)<20:gate_skipped=True
            elif self.gate=='sparse' and len(waypoints)>12:gate_skipped=True
            if not gate_skipped:
                tick=perf_counter();points=[start];layers=[[0]];seen={start,goal}
                if self.compress:waypoints=compress_collinear([start]+list(waypoints)+[goal])
                for p in waypoints:
                    if not isinstance(p,(list,tuple)) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and v==int(v) for v in p):continue
                    t=tuple(p)
                    if t in [start,goal]:continue
                    layer=[]
                    offsets=[(0,0)] if not self.radius else [(0,0),(-1,0),(1,0),(0,-1),(0,1)]
                    for dx,dy in offsets:
                        n=t[0]+dx,t[1]+dy
                        if n in seen:continue
                        if self.uncertified=='discard' and octile(start,n)+octile(n,goal)>target+1e-10:continue
                        if graph.valid_point(n):seen.add(n);layer.append(len(points));points.append(n)
                    if layer:layers.append(layer)
                points.append(goal);last=len(points)-1;layers.append([last]);candidate_count=len(points)-2
                to_goal=[octile(p,goal) for p in points];successors={}
                for left,right in zip(layers,layers[1:]):
                    for i in left:successors[i]=list(right)
                if not self.chain_only:successors[0]=list(range(1,last)) # Direct start-goal was already tried.
                for i in range(1,last):
                    if self.pivot_only:successors[i]=[last]
                    if not self.chain_only and last not in successors[i]:successors[i].append(last)
                    if self.ordering=='goal_first':successors[i].sort(key=lambda j:(j!=last,to_goal[j],j))
                phases['candidate_build_seconds']=perf_counter()-tick
                tick=perf_counter();costs={0:0.}
                for i in range(last):
                    if i not in costs:continue
                    for j in successors[i]:
                        estimate=costs[i]+octile(points[i],points[j])
                        if estimate>=costs.get(j,math.inf)-1e-12:continue
                        if self.uncertified=='discard' and estimate+to_goal[j]>target+1e-10:continue
                        if checks>=self.budget or (self.segment_mode=='analytic' and calls>=self.segment_budget):break
                        link_count+=1;route=segment(points[i],points[j])
                        if not route:continue
                        costs[j]=estimate;parents[j]=i;links[j]=route
                        if j==last and estimate<=target+1e-10:break
                    if costs.get(last,math.inf)<=target+1e-10 or checks>=self.budget or (self.segment_mode=='analytic' and calls>=self.segment_budget):break
                phases['dag_verify_seconds']=perf_counter()-tick
                if last in costs:
                    tick=perf_counter();pieces=[];j=last
                    while j:pieces.append(links[j]);j=parents[j]
                    path=[start]
                    for piece in reversed(pieces):path.extend(piece[1:])
                    upper=costs[last];source='waypoint_dag';phases['route_reconstruct_seconds']=perf_counter()-tick
        if path and self.segment_mode=='analytic':path=expand_lattice_route(path)
        preprocessing=perf_counter()-began
        accepted=bool(path) and upper<=target+1e-10
        certified=bool(path) and upper<=lower+1e-10
        if accepted or (path and self.uncertified=='accept_bound' and upper<=2*lower+1e-10):
            r={'operation':0,'selection_pops':0,'bound_heap_pops':0,'expanded':0,'unique':0,'duplicates':0,'stale':0,'reopens':0,'rebuilds':0,'storage':1,'valid':True,'path':path,'length':upper,'switches':[],'alpha_events':[],'search_seconds':0.}
        else:
            # Shared existing search engine; same fresh graph and same scoring.
            if self.prepare_only:
                r={'operation':0,'expanded':0,'unique':0,'duplicates':0,'stale':0,'reopens':0,'rebuilds':0,'storage':0,'valid':False,'path':[],'length':None,'switches':[],'alpha_events':[],'search_seconds':0.}
            elif path and self.uncertified in ['prune','frontier']:
                r=incumbent_fallback(query,graph,path,weighted_stop=self.uncertified=='frontier')
            elif self.fallback_engine=='lean':
                from .scheduled import ScheduledCertificateSearch
                r=ScheduledCertificateSearch(use_waypoints=False,direct=False).search(query,[],graph)
            else:r=IncumbentSearch(use_waypoints=False,visibility_budget=0,certificate_only=True).search(query,[],graph)
        tick=perf_counter()
        if r['valid'] and (not self.reuse_validation or accepted):
            r['length']=sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:]))
            r['valid']=valid_endpoints and (self.reuse_validation or all(math.isfinite(graph.cost(a,b)) for a,b in zip(r['path'],r['path'][1:])))
        phases['final_validation_seconds']=perf_counter()-tick
        r.update(preprocess_seconds=preprocessing,total_seconds=perf_counter()-began,
          visibility_edge_checks=checks,visibility_calls=calls,candidate_source=source,
          candidate_cost=upper if math.isfinite(upper) else None,start_lower_bound=lower,
          certified_early_return=certified,bounded_early_return=accepted,accepted_source=source if accepted or r.get('incumbent_used',False) else None,phase_seconds=phases,candidate_count=candidate_count,
          attempted_links=link_count,gate_skipped=gate_skipped,witness_attempts=witness_attempts,segment_tests=getattr(graph,'segment_checks',0),wall_tests=getattr(graph,'wall_tests',0))
        return r


def incumbent_fallback(query,graph,incumbent,weighted_stop=False):
    """Weighted fallback with a valid incumbent upper bound (independent experiment)."""
    import heapq
    began=perf_counter();start,goal=tuple(query['start']),tuple(query['goal'])
    upper=sum(math.dist(a,b) for a,b in zip(incumbent,incumbent[1:]));path=incumbent
    queue=[(2*math.dist(start,goal),start,0.)];g={start:0.};closed={};parent={start:start}
    pops=expanded=stale=duplicates=reopens=0
    while queue:
        priority,node,old=heapq.heappop(queue);pops+=1
        if old!=g[node]:stale+=1;duplicates+=int(node in closed);continue
        if node in closed and old>=closed[node]:duplicates+=1;continue
        if weighted_stop and upper<=priority+1e-12:break
        if old+math.dist(node,goal)>=upper-1e-12:continue
        reopens+=int(node in closed);closed[node]=old;expanded+=1
        if node==goal:
            path=[node]
            while path[-1]!=start:path.append(parent[path[-1]])
            path.reverse();break
        for other,edge in graph.adj.get(node,[]):
            new=old+edge
            if new+math.dist(other,goal)>=upper-1e-12:continue
            if new<g.get(other,math.inf)-1e-12:
                g[other]=new;parent[other]=node;heapq.heappush(queue,(new+2*math.dist(other,goal),other,new))
    length=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    return dict(incumbent_used=path is incumbent,operation=pops,expanded=expanded,unique=len(closed),duplicates=duplicates,stale=stale,reopens=reopens,rebuilds=0,storage=len(g),valid=True,path=path,length=length,switches=[],alpha_events=[],search_seconds=perf_counter()-began)


def compress_collinear(points):
    """Remove duplicate and forward-collinear raw hints in linear time."""
    result=[]
    for p in points:
        if not isinstance(p,(list,tuple)) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p):continue
        p=tuple(p)
        if result and p==result[-1]:continue
        while len(result)>1:
            a,b=result[-2:];u=(b[0]-a[0],b[1]-a[1]);v=(p[0]-b[0],p[1]-b[1])
            if u[0]*v[1]!=u[1]*v[0] or u[0]*v[0]+u[1]*v[1]<0:break
            result.pop()
        result.append(p)
    return result


def wall_witnesses(graph,start,goal,lower):
    """Integer crossing candidates; accepted only after exact route verification."""
    points=set()
    for swap,walls in [(False,graph.vertical),(True,graph.horizontal)]:
        a=(start[1],start[0]) if swap else start;b=(goal[1],goal[0]) if swap else goal
        for coordinate,lo,hi in walls:
            if lo==hi or not min(a[0],b[0])<coordinate<max(a[0],b[0]):continue
            for z in [lo-1,hi+1]:
                p=(z,coordinate) if swap else (coordinate,z)
                if graph.valid_point(p) and octile(start,p)+octile(p,goal)<=lower+1e-10:points.add(p)
    return sorted(points,key=lambda p:(octile(start,p)+octile(p,goal),p))
