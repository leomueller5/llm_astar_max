"""Common grid engine for controlled waypoint-guidance experiments.

All moves and closed barrier endpoints follow the repository's Shapely semantics.
Focal modes separate admissible eligibility from uncertain waypoint ordering.
"""
from dataclasses import dataclass
import heapq
import math
from time import perf_counter

MOTIONS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def octile(a, b):
    dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
    return max(dx, dy) + (math.sqrt(2)-1)*min(dx, dy)


class GridGraph:
    """Precomputed legal unit edges, shared equally across matched variants.

    A zero-length barrier falls back to the actual Shapely predicate because
    degenerate LineStrings do not necessarily behave like mathematical points.
    Preprocessing time and edge count are accounted for outside search time.
    """
    def __init__(self, query):
        started = perf_counter()
        self.x0, self.x1 = query['range_x'][0], query['range_x'][1]-1
        self.y0, self.y1 = query['range_y'][0], query['range_y'][1]-1
        self.horizontal = query['horizontal_barriers']
        self.vertical = query['vertical_barriers']
        self.adj = {}
        self.edge_checks = 0
        self.degenerate = any(lo == hi for _, lo, hi in self.horizontal+self.vertical)
        if self.degenerate:
            from shapely.geometry import LineString
            self._line = LineString
            self._walls = [LineString([(a,y),(b,y)]) for y,a,b in self.horizontal]
            self._walls += [LineString([(x,a),(x,b)]) for x,a,b in self.vertical]
        for x in range(self.x0+1, self.x1):
            for y in range(self.y0+1, self.y1):
                a = x,y
                edges = []
                for dx,dy in MOTIONS:
                    b = x+dx,y+dy
                    if self.inside(b):
                        self.edge_checks += 1
                        if not self.collision(a,b):
                            edges.append((b, math.hypot(dx,dy)))
                self.adj[a] = edges
        self.preprocess_seconds = perf_counter()-started

    def inside(self, p):
        return self.x0 < p[0] < self.x1 and self.y0 < p[1] < self.y1

    def collision(self, a, b):
        if not self.inside(a) or not self.inside(b):
            return True
        if self.degenerate:
            segment = self._line([a,b])
            return any(segment.intersects(w) for w in self._walls)
        x,y = a; u,v = b
        for wy, lo, hi in self.horizontal:
            if min(y,v) <= wy <= max(y,v):
                if y == v:
                    if max(min(x,u),lo) <= min(max(x,u),hi): return True
                else:
                    xx = x+(u-x)*(wy-y)/(v-y)
                    if lo <= xx <= hi: return True
        for wx, lo, hi in self.vertical:
            if min(x,u) <= wx <= max(x,u):
                if x == u:
                    if max(min(y,v),lo) <= min(max(y,v),hi): return True
                else:
                    yy = y+(v-y)*(wx-x)/(u-x)
                    if lo <= yy <= hi: return True
        return False

    def cost(self, a, b):
        for n,c in self.adj.get(a,[]):
            if n == b: return c
        return math.inf

    def valid_point(self, p):
        return (len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) and v==int(v) for v in p)
                and self.inside(p) and bool(self.adj.get(tuple(p))))

    def shortcut(self, a, b):
        """Certify an actual shortest lattice walk, not a continuous shortcut."""
        for diagonal_first in [True,False]:
            p = a; path = [a]
            while p != b:
                dx = (b[0]>p[0])-(b[0]<p[0]); dy = (b[1]>p[1])-(b[1]<p[1])
                if not diagonal_first and dx and dy:
                    if abs(b[0]-p[0]) > abs(b[1]-p[1]): dy=0
                    elif abs(b[1]-p[1]) > abs(b[0]-p[0]): dx=0
                q=p[0]+dx,p[1]+dy
                if not math.isfinite(self.cost(p,q)): break
                path.append(q);p=q
            if p==b: return path
        return None


@dataclass(frozen=True)
class SearchConfig:
    method: str = 'weighted'       # weighted or focal
    alpha: float = 1.0
    goal_weight: float = 2.0
    switch: str = 'neighbor'       # neighbor, pop, budget
    budget_scale: float = 1.5
    confidence: bool = False
    filter_points: bool = False
    simplify: bool = False
    focal_weight: float = 1.1
    focal_guide: str = 'original'  # original, route, goal
    heuristic: str = 'euclidean'
    bounded_bonus: bool = False


class WaypointSearch:
    def __init__(self, config=SearchConfig()):
        if config.method not in ['weighted','focal'] or config.switch not in ['neighbor','pop','budget']:
            raise ValueError('Unknown search method or switching policy')
        if config.focal_weight < 1 or config.alpha < 0 or config.goal_weight < 1:
            raise ValueError('Weights must be nonnegative; goal/focal weight >=1')
        self.config = config

    def search(self, query, waypoints, graph=None):
        c=self.config; graph = graph or GridGraph(query)
        started=perf_counter(); prestarted=started
        start,goal=tuple(query['start']),tuple(query['goal'])
        distance = octile if c.heuristic=='octile' else math.dist
        points=[tuple(p) for p in waypoints]
        if c.filter_points:
            points=[p for p in points if graph.valid_point(p)]
        if not points or points[0]!=start: points.insert(0,start)
        if points[-1]!=goal: points.append(goal)
        if len(points)==1: points.append(goal)
        if c.simplify:
            clean=[start]
            for p in points[1:]:
                if p!=clean[-1]:clean.append(p)
            points=clean
            if len(points)==1:points.append(goal)
            k=0
            while k<len(points)-2:
                far=next((j for j in range(len(points)-1,k+1,-1) if graph.shortcut(points[k],points[j])),k+1)
                if far>k+1:points[k+1:far]=[]
                k+=1
        preprocess=perf_counter()-prestarted
        idx=1;target=points[idx];alpha=c.alpha;activation=0;best=math.inf
        g={start:0.0};parents={start:start};closed={};live={}
        open_heap=[];waiting=[];focal=[]
        expansions=pops=duplicates=stale=reopens=rebuilds=maintenance_pops=0
        switches=[];events=[];trace=[];threshold=-math.inf
        def h(n):return distance(n,goal)
        def base(n):return g[n]+h(n)
        def score(n):
            if target==goal:return g[n]+c.goal_weight*h(n)
            if c.bounded_bonus:
                return g[n]+c.goal_weight*h(n)-alpha*max(0,h(n)-distance(n,target))
            return g[n]+h(n)+alpha*distance(n,target)
        def guide(n):
            if c.focal_guide=='goal' or target==goal:return h(n)
            if c.focal_guide=='route':return g[n]+distance(n,target)
            return score(n)
        def good(entry):
            _,n,old=entry
            return n in live and old==g[n] and live[n]==old
        def push(n):
            live[n]=g[n]
            if c.method=='weighted': heapq.heappush(open_heap,(score(n),n,g[n]))
            else:
                heapq.heappush(open_heap,(base(n),n,g[n]))
                if base(n)<=threshold+1e-10:heapq.heappush(focal,(guide(n),n,g[n]))
                else:heapq.heappush(waiting,(base(n),n,g[n]))
        def refresh():
            nonlocal rebuilds
            if not live:return
            rebuilds+=1
            if c.method=='weighted':
                open_heap[:]=[(score(n),n,g[n]) for n in live];heapq.heapify(open_heap)
            else:
                focal[:]=[(guide(n),n,g[n]) for n in live if base(n)<=threshold+1e-10]
                heapq.heapify(focal)
        def activate(anchor):
            nonlocal alpha,best
            best=math.inf;alpha=c.alpha
            if c.confidence and target!=goal:
                excess=max(0,distance(anchor,target)+distance(target,goal)-distance(anchor,goal))
                alpha=c.alpha/(1+2*excess/max(1,distance(anchor,goal)))
            events.append({'expansion':expansions,'target':target,'alpha':alpha})
        def advance(reason,anchor):
            nonlocal idx,target,activation
            if target==goal:return
            switches.append({'expansion':expansions,'target':target,'active_expansions':expansions-activation,
                             'reason':reason,'anchor':anchor,'reached_distance':math.dist(anchor,target),'best_distance':best})
            idx+=1;target=points[idx];activation=expansions
            activate(anchor);refresh()
        activate(start);push(start);path=[]
        while live:
            if c.method=='focal':
                while open_heap and not good(open_heap[0]):heapq.heappop(open_heap);pops+=1;stale+=1
                if not open_heap:break
                threshold=c.focal_weight*open_heap[0][0]
                while waiting and waiting[0][0]<=threshold+1e-10:
                    e=heapq.heappop(waiting);maintenance_pops+=1
                    if good(e):heapq.heappush(focal,(guide(e[1]),e[1],e[2]))
                if not focal:raise AssertionError('Eligible set cannot be empty')
                entry=heapq.heappop(focal)
            else: entry=heapq.heappop(open_heap)
            pops+=1
            if not good(entry):stale+=1;duplicates+=int(entry[1] in closed);continue
            _,s,old=entry;del live[s]
            if s in closed and old>=closed[s]:duplicates+=1;continue
            reopens+=int(s in closed);closed[s]=old;expansions+=1
            best=min(best,math.dist(s,target))
            trace.append((s,target,alpha))
            if s==goal:
                path=[s]
                while path[-1]!=start:path.append(parents[path[-1]])
                path.reverse();break
            if c.switch in ['pop','budget'] and s==target:advance('popped',s)
            if c.switch=='neighbor':
                # Match original switching, including before edge validity checks.
                for dx,dy in MOTIONS:
                    if (s[0]+dx,s[1]+dy)==target and target!=goal:advance('neighbor',s)
            for n,cost in graph.adj.get(s,[]):
                tentative=old+cost
                if tentative<g.get(n,math.inf)-1e-12:
                    g[n]=tentative;parents[n]=s;push(n)
            if c.switch=='budget' and target!=goal:
                origin=start if not switches else switches[-1].get('anchor',start)
                budget=max(8,math.ceil(c.budget_scale*distance(origin,target)))
                if expansions-activation>=budget:advance('budget',s)
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if path else None
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        return {'operation':pops+maintenance_pops,'selection_pops':pops,'maintenance_pops':maintenance_pops,'expanded':expansions,'unique':len(closed),'duplicates':duplicates,
                'stale':stale,'reopens':reopens,'rebuilds':rebuilds,'storage':len(g),
                'length':length,'valid':valid,'path':path,'switches':switches,'alpha_events':events,
                'preprocess_seconds':preprocess,'search_seconds':perf_counter()-started-preprocess,
                'total_seconds':perf_counter()-started,'processed_waypoints':points,
                'trace':trace}
