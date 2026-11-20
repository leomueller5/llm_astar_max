"""Sparse landmark cost predictions, a different representation from cell masks."""
import math
from common import ROOT
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile

def choose_landmarks(query,limit=16):
    g=SegmentGridGraph(query);s,t=tuple(query['start']),tuple(query['goal']);points={}
    for axis,barriers,prefix in [(0,query['vertical_barriers'],'V'),(1,query['horizontal_barriers'],'H')]:
        for i,(coordinate,lo,hi) in enumerate(barriers):
            for side,v in [('low',lo-1),('high',hi+1)]:
                p=(coordinate,v) if axis==0 else (v,coordinate)
                if g.valid_point(p) and p not in [s,t] and p not in points.values():points[f'{prefix}{i}_{side}']=p
    items=sorted(points.items(),key=lambda kv:(octile(s,kv[1])+octile(kv[1],t),kv[0]));chosen=items[:min(4,limit)]
    remaining=[kv for kv in items if kv not in chosen]
    while remaining and len(chosen)<limit:
        kv=max(remaining,key=lambda kv:min(octile(kv[1],p) for _,p in chosen) if chosen else octile(s,kv[1]));chosen.append(kv);remaining.remove(kv)
    return dict(chosen)

class LandmarkCostField:
    """Untrusted hhat=min checked-local-cost+predicted landmark remaining cost.

Only a bounded priority envelope/anchor supplies solution-quality guarantees.
No reference/oracle values are used unless explicitly supplied by a diagnostic.
"""
    def __init__(self,query,points,costs,visibility=False,nearest=4,extension="via"):
        if extension not in ["via","difference"]:raise ValueError("Unknown landmark extension")
        self.extension=extension
        self.graph=SegmentGridGraph(query);self.query=query;self.goal=tuple(query['goal']);self.points={k:tuple(p) for k,p in points.items()};self.costs=costs;self.visibility=visibility;self.nearest=nearest;self.cache={};self.probes=0
        try:self.h=CutPotential(query,self.goal).value
        except ValueError:self.h=lambda p:octile(p,self.goal)
    def value(self,n):
        if n in self.cache:return self.cache[n]
        base=self.h(n);options=[]
        if n==self.goal:return (0.,.5,1.)
        if self.visibility:
            self.probes+=1
            if self.graph.lattice_segment(n,self.goal):
                if self.extension=="difference":self.cache[n]=(0.,.5,1.);return self.cache[n]
                options.append(octile(n,self.goal))
        ordered=sorted(self.points,key=lambda k:octile(n,self.points[k]))[:self.nearest] if self.visibility else self.points
        for key in ordered:
            p=self.points[key]
            if key not in self.costs or not math.isfinite(self.costs[key]):continue
            if self.visibility:
                self.probes+=1
                if not self.graph.lattice_segment(n,p):continue
            estimate=max(self.h(p),self.costs[key])
            options.append(estimate-octile(n,p) if self.extension=="difference" else octile(n,p)+estimate)
        value=max(0.,(max(options) if self.extension=="difference" else min(options))-base) if options else 0.
        result=value,.5,1.;self.cache[n]=result;return result
