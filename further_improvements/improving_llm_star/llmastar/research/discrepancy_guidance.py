"""Experimental policy-discrepancy Focal Search with a retained admissible anchor.

Adaptation of learned-policy/discrepancy search, not a new focal-search theorem.
Frozen Session7 residual and Session6 implementations are untouched. Guidance
orders legal successors; it never removes one. The accumulated discrepancy
counts deviations from the locally preferred one-step remaining-cost prediction.
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
    discrepancy:int
    parent:object
    sequence:int

class DiscrepancyGuidedSearch:
    def __init__(self,bound=1.05,alpha=.22640953779865894):
        if not math.isfinite(bound) or bound<1 or not math.isfinite(alpha) or alpha<0:raise ValueError('Invalid search configuration')
        self.bound=bound;self.alpha=alpha
    def search(self,query,field=None):
        began=perf_counter();graph=SegmentGridGraph(query);goal=tuple(query['goal']);start=tuple(query['start'])
        try:potential=CutPotential(query,goal);function=potential.value
        except ValueError:function=lambda n:octile(n,goal)
        hc={};pc={}
        def h(n):
            if n not in hc:hc[n]=function(n)
            return hc[n]
        def prediction(n):
            if n not in pc:
                d,priority,c=field.value(n) if field is not None else (0.,.5,0.)
                pc[n]=h(n)+self.alpha*c*d
            return pc[n]
        anchor=[];waiting=[];focal=[];best={};active={};closed={};serial=pushes=pops=expanded=stale=reopens=0;found=None
        def alive(lab):return active.get(lab.node) is lab and lab.g<closed.get(lab.node,math.inf)-1e-12
        def offer(n,g,discrepancy,parent):
            nonlocal serial,pushes
            if n in best and g>=best[n].g-1e-12:return
            label=Label(n,g,discrepancy,parent,serial);serial+=1;best[n]=label;active[n]=label;entry=(g+h(n),n,label.sequence,label)
            heapq.heappush(anchor,entry);heapq.heappush(waiting,entry);pushes+=2
        if graph.valid_point(start) and graph.valid_point(goal):offer(start,0.,0,None)
        while anchor:
            while anchor and not alive(anchor[0][-1]):heapq.heappop(anchor);pops+=1;stale+=1
            if not anchor:break
            threshold=self.bound*anchor[0][0]
            while waiting and waiting[0][0]<=threshold+1e-12:
                *_,label=heapq.heappop(waiting);pops+=1
                if alive(label):heapq.heappush(focal,(label.discrepancy,label.g+h(label.node),h(label.node),label.node,label.sequence,label));pushes+=1
                else:stale+=1
            current=None
            while focal:
                *_,label=heapq.heappop(focal);pops+=1
                if not alive(label):stale+=1;continue
                if label.g+h(label.node)>threshold+1e-12:
                    heapq.heappush(waiting,(label.g+h(label.node),label.node,label.sequence,label));pushes+=1;continue
                current=label;break
            if current is None:continue
            n=current.node;active.pop(n,None);reopens+=n in closed;closed[n]=current.g;expanded+=1
            if n==goal:found=current;break
            neighbours=graph.adj.get(n,[])
            if not neighbours:continue
            scores={m:edge+prediction(m) for m,edge in neighbours};preferred=min(scores.values())
            for m,edge in neighbours:offer(m,current.g+edge,current.discrepancy+int(scores[m]>preferred+1e-9),current)
        path=[];length=None
        if found:
            length=found.g;label=found
            while label:path.append(label.node);label=label.parent
            path.reverse();assert abs(sum(math.dist(a,b) for a,b in zip(path,path[1:]))-length)<1e-7
        return {'path':path,'length':length,'valid':found is not None,'operation':pops,'storage':len(best),'heap_pops':pops,'heap_pushes':pushes,'unique':len(closed),'expanded':expanded,'stale':stale,'reopens':reopens,'rebuilds':0,'total_seconds':perf_counter()-began}
