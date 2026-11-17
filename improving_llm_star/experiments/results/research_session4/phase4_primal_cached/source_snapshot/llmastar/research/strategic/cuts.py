"""Admissible monotone checkpoint relaxation for integer wall maps.

Any path must visit each separating integer cut line in order (take first hits).
The DP keeps the crossing coordinate, but ignores geometry between cuts. Hence
its value is a LOWER bound even for paths that backtrack. Advice may select cuts
or primal gate preferences, but cannot assert unchecked lower-bound values.
"""
from bisect import bisect_left,bisect_right
import math
from time import perf_counter
import numpy as np

C=math.sqrt(2)-1


def _past_min(values,width):
    n=len(values)
    if width>=n:return np.minimum.accumulate(values)
    count=(n+width-1)//width
    padded=np.full(count*width,np.inf);padded[:n]=values
    blocks=padded.reshape(count,width)
    prefix=np.minimum.accumulate(blocks,axis=1).ravel()[:n]
    suffix=np.minimum.accumulate(blocks[:,::-1],axis=1)[:,::-1].ravel()[:n]
    out=prefix.copy();indices=np.arange(width-1,n)
    out[indices]=np.minimum(prefix[indices],suffix[indices-width+1])
    return out


def octile_transform(values,dx):
    """min_z values[z]+octile((0,z),(dx,y)), for every y, in O(height)."""
    dx=int(abs(dx));n=len(values);y=np.arange(n,dtype=float)
    near_left=dx+C*y+_past_min(values-C*y,dx+1)
    near_right=dx-C*y+_past_min((values+C*y)[::-1],dx+1)[::-1]
    result=np.minimum(near_left,near_right)
    if dx+1<n:
        prefix=np.minimum.accumulate(values-y);suffix=np.minimum.accumulate((values+y)[::-1])[::-1]
        indices=np.arange(dx+1,n);result[indices]=np.minimum(result[indices],C*dx+indices+prefix[indices-dx-1])
        indices=np.arange(0,n-dx-1);result[indices]=np.minimum(result[indices],C*dx-indices+suffix[indices+dx+1])
    return result


class AxisCutPotential:
    def __init__(self,query,goal,cuts,axis='x'):
        if axis not in ['x','y']:raise ValueError('Unknown axis')
        began=perf_counter();self.axis=axis;self.query=query;self.goal=tuple(goal)
        self.coordinate_goal=goal[0] if axis=='x' else goal[1];self.other_goal=goal[1] if axis=='x' else goal[0]
        r=query['range_y'] if axis=='x' else query['range_x'];self.low=r[0]+1;self.high=r[1]-2
        self.ys=np.arange(self.low,self.high+1,dtype=float)
        self.cuts=sorted(set(int(x) for x in cuts if int(x)==x and x!=self.coordinate_goal))
        self.left=[x for x in self.cuts if x<self.coordinate_goal];self.right=[x for x in self.cuts if x>self.coordinate_goal]
        self.tables={};self.at_cut={};self.masks={};self.lazy_seconds=0.;self.transform_count=0
        for coords in [list(reversed(self.left)),self.right]:
            previous=self.coordinate_goal;values=np.abs(self.ys-self.other_goal)
            for coordinate in coords:
                values=octile_transform(values,coordinate-previous);self.transform_count+=1
                mask=self.free_mask(coordinate);values[~mask]=np.inf
                self.at_cut[coordinate]=values;self.tables[coordinate]=values.tolist();self.masks[coordinate]=mask
                previous=coordinate
        self.preprocess_seconds=perf_counter()-began

    def free_mask(self,coordinate):
        mask=np.ones(len(self.ys),dtype=bool)
        parallel=self.query['vertical_barriers'] if self.axis=='x' else self.query['horizontal_barriers']
        perpendicular=self.query['horizontal_barriers'] if self.axis=='x' else self.query['vertical_barriers']
        for fixed,lo,hi in parallel:
            if fixed==coordinate and lo!=hi:
                begin=max(int(lo),int(self.low));end=min(int(hi),int(self.high))
                if begin<=end:mask[begin-int(self.low):end-int(self.low)+1]=False
        for other,lo,hi in perpendicular:
            if lo!=hi and lo<=coordinate<=hi and self.low<=other<=self.high and int(other)==other:mask[int(other-self.low)]=False
        return mask

    def vector(self,coordinate):
        if coordinate in self.tables:return self.tables[coordinate]
        began=perf_counter()
        if coordinate<self.coordinate_goal:
            i=bisect_left(self.left,coordinate);cut=self.left[i] if i<len(self.left) else None
        elif coordinate>self.coordinate_goal:
            i=bisect_right(self.right,coordinate)-1;cut=self.right[i] if i>=0 else None
        else:cut=None
        if cut is None:
            dx=abs(coordinate-self.coordinate_goal);dy=np.abs(self.ys-self.other_goal)
            values=np.maximum(dx,dy)+C*np.minimum(dx,dy)
        else:values=octile_transform(self.at_cut[cut],coordinate-cut);self.transform_count+=1
        result=values.tolist();self.tables[coordinate]=result;self.lazy_seconds+=perf_counter()-began
        return result

    def value(self,point):
        coordinate,other=(point[0],point[1]) if self.axis=='x' else (point[1],point[0])
        return self.vector(coordinate)[int(other-self.low)]

    def gate_route(self,start,preferences=None):
        """Primal relaxation witness; caller must verify every emitted grid edge."""
        a,b=(start[0],start[1]) if self.axis=='x' else (start[1],start[0])
        coords=[x for x in self.cuts if min(a,self.coordinate_goal)<x<max(a,self.coordinate_goal)]
        coords.sort(reverse=a>self.coordinate_goal)
        current=(a,b);route=[tuple(start)]
        # Preferences only mask the PRIMAL guide DP, never the admissible anchor.
        tables=self.at_cut
        if preferences:
            tables={};previous=self.coordinate_goal;values=np.abs(self.ys-self.other_goal)
            for coordinate in reversed(coords):
                values=octile_transform(values,coordinate-previous);mask=self.free_mask(coordinate)
                for side,lo,hi in preferences.get(coordinate,()):
                    if side in ['above','right']:mask &= self.ys>hi
                    elif side in ['below','left']:mask &= self.ys<lo
                values[~mask]=np.inf;tables[coordinate]=values;previous=coordinate
        for coordinate in coords:
            dx=abs(current[0]-coordinate);dy=np.abs(self.ys-current[1]);scores=tables[coordinate]+np.maximum(dx,dy)+C*np.minimum(dx,dy)
            i=int(np.argmin(scores))
            if not math.isfinite(float(scores[i])):return []
            current=coordinate,int(self.ys[i]);route.append(current if self.axis=='x' else (current[1],current[0]))
        route.append(self.goal);return route


class CutPotential:
    def __init__(self,query,goal,selection='all',limit=8,waypoints=()):
        began=perf_counter()
        bounds=query['range_x']+query['range_y']
        if not all(type(v) in [int,float] and math.isfinite(v) and int(v)==v for v in bounds) or limit<1:raise ValueError('Integer bounds and positive cut budget required')
        walls=query['horizontal_barriers']+query['vertical_barriers']
        if not all(all(type(v) in [int,float] and math.isfinite(v) and int(v)==v for v in wall) and wall[1]<=wall[2] for wall in walls):
            raise ValueError('Cut relaxation supports integer wall maps')
        if selection not in ['all','longest','uniform','waypoints','none']:raise ValueError('Unknown cut selection')
        self.query=query;self.goal=tuple(goal);self.selection=selection
        def select(walls,axis):
            entries={}
            if selection=='none':return []
            low,high=query['range_x' if axis=='x' else 'range_y'];low+=1;high-=2
            for coordinate,lo,hi in walls:
                if low<=coordinate<=high and lo!=hi:entries[coordinate]=max(entries.get(coordinate,0),hi-lo)
            coords=sorted(entries)
            if selection=='all' or len(coords)<=limit:return coords
            if selection=='longest':return sorted(sorted(coords,key=lambda x:(-entries[x],x))[:limit])
            if selection=='uniform':return sorted(set(coords[round(i*(len(coords)-1)/max(1,limit-1))] for i in range(limit)))
            values=[p[0] if axis=='x' else p[1] for p in waypoints if isinstance(p,(list,tuple)) and len(p)==2 and all(type(v) in [int,float] and math.isfinite(v) for v in p)]
            if not values:return sorted(sorted(coords,key=lambda x:(-entries[x],x))[:limit])
            return sorted(sorted(coords,key=lambda x:(min(abs(x-y) for y in values),-entries[x],x))[:limit])
        xs=select(query['vertical_barriers'],'x');ys=select(query['horizontal_barriers'],'y')
        self.x=AxisCutPotential(query,goal,xs,'x');self.y=AxisCutPotential(query,goal,ys,'y')
        self.preprocess_seconds=perf_counter()-began;self.cut_count=len(xs)+len(ys)

    def value(self,point):return max(self.x.value(point),self.y.value(point))
    @property
    def lazy_seconds(self):return self.x.lazy_seconds+self.y.lazy_seconds
    @property
    def cache_bytes(self):return sum(8*len(v) for axis in [self.x,self.y] for v in axis.tables.values())
