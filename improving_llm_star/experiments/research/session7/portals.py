"""Persistent obstacle-side predictions, independent of waypoint switching."""
import math
from common import ROOT
from oracle import anchor
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.search import octile

def candidates(query,limit=3):
    graph=SegmentGridGraph(query);s,t=tuple(query['start']),tuple(query['goal']);h=anchor(query,'cut');rows=[]
    for axis,barriers,kind in [(0,query['vertical_barriers'],'V'),(1,query['horizontal_barriers'],'H')]:
        for i,(v,lo,hi) in enumerate(barriers):
            if not min(s[axis],t[axis])<v<max(s[axis],t[axis]):continue
            points={};lower={}
            for side,other in [('low',lo-1),('high',hi+1)]:
                p=(v,other) if axis==0 else (other,v)
                if not graph.valid_point(p):continue
                points[side]=p;lower[side]=octile(s,p)+h(p)
            if len(points)<2:continue
            relevance=min(octile(s,p)+octile(p,t) for p in points.values())-octile(s,t)
            rows.append({'id':kind+str(i),'axis':axis,'coordinate':v,'interval':[lo,hi],'start_side':-1 if s[axis]<v else 1,'portals':points,'estimated_via_costs':lower,'relevance':relevance})
    return sorted(rows,key=lambda r:(-r['relevance'],r['id']))[:limit]

class PortalField:
    def __init__(self,query,choices,rows=None):
        self.rows=rows if rows is not None else candidates(query);self.h=anchor(query,'cut');self.choices=choices
    def value(self,n):
        base=self.h(n);extra=0.
        for r in self.rows:
            choice=self.choices.get(r['id'])
            if choice is None:continue
            side,confidence=choice
            if side not in r['portals'] or not 0<=confidence<=1:continue
            if (n[r['axis']]-r['coordinate'])*r['start_side']<=0:continue
            p=tuple(r['portals'][side]);extra=max(extra,confidence*max(0.,octile(n,p)+self.h(p)-base))
        return extra,.5,1.

def geometric_choices(rows):return {r['id']:(min(r['estimated_via_costs'],key=r['estimated_via_costs'].get),1.) for r in rows}
def oracle_choices(rows,path):
    choices={}
    for r in rows:
        crossing=next((n for n in path if n[r['axis']]==r['coordinate']),None)
        if crossing is not None:choices[r['id']]=('low' if crossing[1-r['axis']]<r['interval'][0] else 'high',1.)
    return choices
