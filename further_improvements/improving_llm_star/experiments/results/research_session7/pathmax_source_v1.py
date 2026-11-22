"""Isolated bounded pathmax integration for inconsistent regional advice.

Pathmax is established heuristic-search machinery. The additional upper clip
retains the pointwise w*anchor bound; it can prevent full consistency, which is
not claimed. All ordinary edges, best-g labels and reopenings are retained.
"""
import heapq,math
from dataclasses import dataclass
from time import perf_counter
from .geometry import SegmentGridGraph
from .strategic.cuts import CutPotential
from .search import octile

@dataclass(frozen=True)
class Label:
    node:tuple
    g:float
    heuristic:float
    parent:object
    sequence:int

class PathmaxResidualSearch:
    def __init__(self,bound=1.05,alpha=.22640953779865894,pathmax=True,base_weight=1.):
        if not math.isfinite(bound) or bound<1 or not math.isfinite(alpha) or alpha<0 or not 1<=base_weight<=bound:raise ValueError('Invalid configuration')
        self.bound=bound;self.alpha=alpha;self.pathmax=pathmax;self.base_weight=base_weight
    def search(self,query,field=None):
        began=perf_counter();graph=SegmentGridGraph(query);start=tuple(query['start']);goal=tuple(query['goal'])
        try:function=CutPotential(query,goal).value
        except ValueError:function=lambda n:octile(n,goal)
        cache={};raw={}
        def h(n):
            if n not in cache:cache[n]=function(n)
            return cache[n]
        def estimate(n):
            if n not in raw:
                d,priority,c=field.value(n) if field else (0.,.5,0.)
                raw[n]=min(self.bound*h(n),max(h(n),self.base_weight*h(n)+self.alpha*d*c))
            return raw[n]
        best={};closed={};queue=[];serial=pops=pushes=stale=reopens=expanded=raises=clips=0;found=None
        def offer(n,g,parent,edge=0.):
            nonlocal serial,pushes,raises,clips
            if n in best and g>=best[n].g-1e-12:return
            value=estimate(n)
            if parent is not None and self.pathmax:
                candidate=max(value,parent.heuristic-edge);raised=min(self.bound*h(n),candidate);raises+=raised>value+1e-12;clips+=candidate>self.bound*h(n)+1e-12;value=raised
            label=Label(n,g,value,parent,serial);serial+=1;best[n]=label;heapq.heappush(queue,(g+value,0.,n,label.sequence,label));pushes+=1
        if graph.valid_point(start) and graph.valid_point(goal):offer(start,0.,None)
        while queue:
            *_,label=heapq.heappop(queue);pops+=1;n=label.node
            if best.get(n) is not label or label.g>=closed.get(n,math.inf)-1e-12:stale+=1;continue
            reopens+=n in closed;closed[n]=label.g;expanded+=1
            if n==goal:found=label;break
            for other,edge in graph.adj.get(n,[]):offer(other,label.g+edge,label,edge)
        path=[];length=None
        if found:
            length=found.g;label=found
            while label:path.append(label.node);label=label.parent
            path.reverse();assert abs(sum(math.dist(a,b) for a,b in zip(path,path[1:]))-length)<1e-7
        return {'path':path,'length':length,'valid':found is not None,'operation':pops,'storage':len(best),'heap_pops':pops,'heap_pushes':pushes,'unique':len(closed),'expanded':expanded,'stale':stale,'reopens':reopens,'rebuilds':0,'pathmax_raises':raises,'pathmax_clipped':clips,'total_seconds':perf_counter()-began}
