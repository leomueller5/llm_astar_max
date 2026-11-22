"""Query-local integer-grid geometry index; legacy geometry remains available."""
import math
from time import perf_counter
from .search import LazyGridGraph, MOTIONS


class _IndexedAdjacency(dict):
    def __init__(self, graph):
        super().__init__();self.graph=graph

    def get(self, node, default=None):
        cached=super().get(node)
        if cached is not None:return cached
        g=self.graph
        if not g.inside(node) or g.blocked(node):return [] if default is None else default
        x,y=node;edges=[]
        for dx,dy in MOTIONS:
            other=x+dx,y+dy
            if g.inside(other):
                g.edge_checks+=1
                if not g.blocked(other) and not g.degenerate_collision(node,other):
                    edges.append((other,math.hypot(dx,dy)))
        self[node]=edges
        return edges


class IndexedGridGraph(LazyGridGraph):
    """A unit grid edge meets an integer wall only at one of its endpoints.

    Index wall intervals by their row/column and cache point occupancy. Degenerate
    barriers use the installed Shapely predicate, only near their single point.
    Noninteger geometry falls back to the unchanged legacy implementation.
    All indices/caches are constructed afresh and included in query timing.
    """
    def __init__(self, query):
        started=perf_counter()
        walls=query['horizontal_barriers']+query['vertical_barriers']
        self.indexed=all(all(isinstance(v,(int,float)) and math.isfinite(v) and v==int(v) for v in wall) and wall[1]<=wall[2] for wall in walls)
        if not self.indexed:
            super().__init__(query);return
        self.x0,self.x1=query['range_x'][0],query['range_x'][1]-1
        self.y0,self.y1=query['range_y'][0],query['range_y'][1]-1
        self.horizontal=query['horizontal_barriers'];self.vertical=query['vertical_barriers']
        self._rows={};self._columns={};self._occupancy={};self._degenerate={};self._degenerate_cache={}
        self.edge_checks=0;self.occupancy_checks=0;self.degenerate=False
        for axis,barriers in [(self._rows,self.horizontal),(self._columns,self.vertical)]:
            for coordinate,lo,hi in barriers:
                if lo==hi:
                    from shapely.geometry import LineString
                    point=(lo,coordinate) if axis is self._rows else (coordinate,lo)
                    self._degenerate.setdefault(point,[]).append(LineString([point,point]))
                else:axis.setdefault(coordinate,[]).append((lo,hi))
        if self._degenerate:
            from shapely.geometry import LineString
            self._line=LineString
        self.adj=_IndexedAdjacency(self)
        self.preprocess_seconds=perf_counter()-started

    def blocked(self,point):
        value=self._occupancy.get(point)
        if value is None:
            self.occupancy_checks+=1;x,y=point
            value=any(lo<=x<=hi for lo,hi in self._rows.get(y,())) or any(lo<=y<=hi for lo,hi in self._columns.get(x,()))
            self._occupancy[point]=value
        return value

    def degenerate_collision(self,a,b):
        if not self._degenerate or (a not in self._degenerate and b not in self._degenerate):return False
        key=(a,b) if a<b else (b,a)
        result=self._degenerate_cache.get(key)
        if result is None:
            segment=self._line([a,b])
            result=any(segment.intersects(w) for p in (a,b) for w in self._degenerate.get(p,()))
            self._degenerate_cache[key]=result
        return result

    def collision(self,a,b):
        if not self.indexed:return super().collision(a,b)
        if not self.inside(a) or not self.inside(b):return True
        if max(abs(a[0]-b[0]),abs(a[1]-b[1]))!=1:
            # Public predicate also supports arbitrary segments.
            from shapely.geometry import LineString
            segment=LineString([a,b])
            return any(segment.intersects(LineString([(lo,y),(hi,y)])) for y,lo,hi in self.horizontal) or any(segment.intersects(LineString([(x,lo),(x,hi)])) for x,lo,hi in self.vertical)
        return self.blocked(a) or self.blocked(b) or self.degenerate_collision(a,b)

    def cost(self,a,b):
        if not self.indexed:return super().cost(a,b)
        if max(abs(a[0]-b[0]),abs(a[1]-b[1]))!=1:return math.inf
        self.edge_checks+=1
        if self.collision(a,b):return math.inf
        return math.dist(a,b)

    def valid_point(self,p):
        if not self.indexed:return super().valid_point(p)
        return len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) and v==int(v) for v in p) and self.inside(p) and not self.blocked(tuple(p))


class SegmentGridGraph(IndexedGridGraph):
    """Validate shortest lattice walks as at most two continuous straight pieces.

    This is exact because each piece is a union of the emitted unit grid edges.
    Failed links need no path allocation; only the accepted route is expanded.
    """
    def __init__(self,query):
        super().__init__(query)
        from bisect import bisect_left,bisect_right
        self._bisect_left=bisect_left;self._bisect_right=bisect_right
        if self.indexed:
            self._row_keys=sorted(self._rows);self._column_keys=sorted(self._columns)
        self.segment_checks=0;self.wall_tests=0

    def clear_piece(self,a,b):
        if a==b:return self.valid_point(a)
        self.segment_checks+=1
        if not self.indexed:
            # Preserve even degenerate/noninteger predicate details at unit resolution.
            p=a
            while p!=b:
                n=(p[0]+(b[0]>p[0])-(b[0]<p[0]),p[1]+(b[1]>p[1])-(b[1]<p[1]))
                if not math.isfinite(self.cost(p,n)):return False
                p=n
            return True
        if not self.inside(a) or not self.inside(b):return False
        x,y=a;u,v=b
        left,right=min(x,u),max(x,u);bottom,top=min(y,v),max(y,v)
        for wy in self._row_keys[self._bisect_left(self._row_keys,bottom):self._bisect_right(self._row_keys,top)]:
            for lo,hi in self._rows[wy]:
                self.wall_tests+=1
                if y==v:
                    if max(left,lo)<=min(right,hi):return False
                elif lo<=x+(u-x)*(wy-y)/(v-y)<=hi:return False
        for wx in self._column_keys[self._bisect_left(self._column_keys,left):self._bisect_right(self._column_keys,right)]:
            for lo,hi in self._columns[wx]:
                self.wall_tests+=1
                if x==u:
                    if max(bottom,lo)<=min(top,hi):return False
                elif lo<=y+(v-y)*(wx-x)/(u-x)<=hi:return False
        for point,walls in self._degenerate.items():
            if left<=point[0]<=right and bottom<=point[1]<=top:
                if (u-x)*(point[1]-y)!=(v-y)*(point[0]-x):continue
                sx=(u>x)-(u<x);sy=(v>y)-(v<y)
                for neighbor in [(point[0]-sx,point[1]-sy),(point[0]+sx,point[1]+sy)]:
                    if left<=neighbor[0]<=right and bottom<=neighbor[1]<=top and self.degenerate_collision(point,neighbor):return False
        return True

    def lattice_segment(self,a,b):
        dx=b[0]-a[0];dy=b[1]-a[1];sx=(dx>0)-(dx<0);sy=(dy>0)-(dy<0)
        n=min(abs(dx),abs(dy))
        diagonal_corner=a[0]+sx*n,a[1]+sy*n
        axial_corner=b[0]-sx*n,b[1]-sy*n
        for corner in dict.fromkeys([diagonal_corner,axial_corner]):
            if self.clear_piece(a,corner) and self.clear_piece(corner,b):
                return [a]+([corner] if corner not in [a,b] else [])+([b] if a!=b else [])
        return None


def expand_lattice_route(corners):
    if not corners:return []
    route=[corners[0]]
    for end in corners[1:]:
        p=route[-1]
        while p!=end:
            p=(p[0]+(end[0]>p[0])-(end[0]<p[0]),p[1]+(end[1]>p[1])-(end[1]<p[1]))
            route.append(p)
    return route
