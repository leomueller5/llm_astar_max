"""One optional correction from actual legal frontier transitions, never a path oracle."""
import math
from common import ROOT
from oracle import anchor
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.spatial_guidance import RegionField

class GeometricBoost:
    def __init__(self,query,amount=.05):self.h=anchor(query,'cut');self.amount=amount
    def value(self,n):return self.amount*self.h(n),.5,1.

def evidence(query,field,context,threshold=2.):
    graph=SegmentGridGraph(query);h=anchor(query,'cut');points=[tuple(context['current'])]+[tuple(r['node']) for r in context['frontier']];pairs=[];seen=set()
    def prediction(n):
        d,p,c=field.value(n);return h(n)+c*d
    for a in points:
        for b,cost in graph.adj.get(a,[]):
            key=tuple(sorted([a,b]))
            if key in seen:continue
            seen.add(key);pa,pb=prediction(a),prediction(b);gap=abs(pa-pb)-cost;base_violation=max(0.,abs(h(a)-h(b))-cost)
            if gap-base_violation>threshold:
                pairs.append({'a':list(a),'b':list(b),'legal_edge_cost':cost,'predicted_remaining_a':pa,'predicted_remaining_b':pb,'triangle_violation':gap,'geometric_violation':base_violation,'model_excess_violation':gap-base_violation})
    return sorted(pairs,key=lambda p:-p['triangle_violation'])[:8]

def damp_from_evidence(query,field,pairs):
    # Simple deterministic corrective control; no claim that coarse-field
    # inconsistency proves the corresponding sample itself is wrong.
    f=RegionField(query,field.field.side if hasattr(field,'field') else field.side)
    source=field.field if hasattr(field,'field') else field
    values={}
    for region in source.regions:
        if region['sample'] is None:continue
        d,p,c=field.value(tuple(region['sample']));values[region['id']]=[d*c,.5,1.]
    for pair in pairs:
        a,b=pair['a'],pair['b'];high=a if pair['predicted_remaining_a']>pair['predicted_remaining_b'] else b;rid=f.identifier(high)
        if rid in values:values[rid][0]*=.5
    f.update([{'region_id':k,'detour':v[0],'priority':v[1],'confidence':v[2]} for k,v in values.items()]);return f
