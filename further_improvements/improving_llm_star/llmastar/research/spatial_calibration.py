"""Verified residual intervals calibrate spatial LLM trust without reference costs."""
import math
from time import perf_counter
from .geometry import SegmentGridGraph
from .strategic.cuts import CutPotential
from .search import octile
from .spatial_guidance import RegionField

def sample_intervals(query,side=4,attempts=4):
    began=perf_counter();graph=SegmentGridGraph(query);field=RegionField(query,side,graph);goal=tuple(query['goal'])
    try:potential=CutPotential(query,goal);h=potential.value
    except ValueError:h=lambda p:octile(p,goal)
    endpoints=[]
    for axis,barriers in [(0,query['vertical_barriers']),(1,query['horizontal_barriers'])]:
        for coordinate,lo,hi in barriers:
            for other in [lo-1,hi+1]:
                p=(coordinate,other) if axis==0 else (other,coordinate)
                if p not in endpoints and graph.valid_point(p):endpoints.append(p)
    rows={};certified=0
    for r in field.regions:
        n=tuple(r['sample']) if r['sample'] else None
        if n is None:continue
        lower=h(n);upper=None;witness=None
        if graph.lattice_segment(n,goal):upper=octile(n,goal);witness=[n,goal]
        else:
            candidates=sorted(endpoints,key=lambda p:octile(n,p)+octile(p,goal))[:attempts]
            for p in candidates:
                length=octile(n,p)+octile(p,goal)
                if upper is not None and length>=upper-1e-12:continue
                if graph.lattice_segment(n,p) and graph.lattice_segment(p,goal):
                    upper=length;witness=[n,p,goal]
                    if upper<=lower+1e-10:break
        if upper is not None:
            if upper<lower-1e-7:raise AssertionError('Verified upper bound contradicts anchor')
            certified+=upper<=lower+1e-10
        rows[r['id']]={'sample':n,'lower':lower if math.isfinite(lower) else None,'upper':upper,'witness':witness}
    return rows,{'seconds':perf_counter()-began,'segment_checks':graph.segment_checks,'wall_tests':graph.wall_tests,'sample_count':len(rows),'finite_upper_bounds':sum(r['upper'] is not None for r in rows.values()),'exact_certificates':certified,'endpoint_count':len(endpoints)}

class VerifiedResidualField:
    """Sample-level [L,U] clamps do NOT make a whole coarse region admissible.

The independent envelope/anchor search, not this interpolation, proves quality.
When no upper witness is found, keep the untrusted model residual. Midpoint and
upper controls use the identical computed intervals without model information.
"""
    def __init__(self,field,intervals,source='model',alpha=1.,relative=False):
        if source not in ['model','midpoint','upper','zero']:raise ValueError('Invalid calibration source')
        if not math.isfinite(alpha) or not 0<=alpha<=1:raise ValueError('Invalid calibrated alpha')
        self.field=field;self.intervals=intervals;self.source=source;self.relative=relative;self.calibrated={};self.alpha_values={}
        goal=tuple(field.query['goal'])
        try:self.h=CutPotential(field.query,goal).value
        except ValueError:self.h=lambda p:octile(p,goal)
        scale=math.hypot(field.width,field.height)
        for region in field.regions:
            identifier=region['id'];row=intervals.get(identifier,{});lower=row.get('lower');upper=row.get('upper')
            gap=max(0.,upper-lower) if lower is not None and upper is not None else None
            raw=field.values.get(identifier,(0.,.5,0.));predicted=raw[0]*raw[2]
            if source=='model':delta=min(alpha*predicted,gap) if gap is not None else alpha*predicted
            elif source=='zero':delta=0.
            else:delta=(gap*(.5 if source=='midpoint' else 1.)) if gap is not None else .1*scale
            self.calibrated[identifier]=delta;self.alpha_values[identifier]=delta/predicted if predicted>0 and source=='model' else None
    def value(self,n):
        identifier=self.field.identifier(n);value=self.calibrated.get(identifier,0.)
        if self.relative:
            lower=self.intervals.get(identifier,{}).get('lower');value*=self.h(n)/max(1.,lower) if lower is not None else 1.
        return value,.5,1.

class BilinearResidualField:
    """O(1) interpolation of compact region predictions, not a dense LLM map.

Confidence-weighted predictions are treated as regular cell-center samples;
blocked centers may have nudged free representatives. This is an approximation,
not a lower bound. A positive taper makes the residual vanish at the goal.
"""
    def __init__(self,field,alpha=1.,relative=False,taper=True):
        if not math.isfinite(alpha) or alpha<0:raise ValueError('Nonnegative finite alpha required')
        self.field=field;self.alpha=alpha;self.relative=relative;self.taper=taper;self.goal=tuple(field.query['goal']);self.cache={}
        try:self.h=CutPotential(field.query,self.goal).value
        except ValueError:self.h=lambda p:octile(p,self.goal)
        self.samples=[]
        for r in field.regions:
            d,p,c=field.values.get(r['id'],(0.,.5,0.));n=tuple(r['sample']) if r['sample'] else None
            value=d*c
            if relative:value=value/max(1.,self.h(n)) if n is not None and math.isfinite(self.h(n)) else 0.
            self.samples.append(value)
    def value(self,n):
        if n in self.cache:return self.cache[n]
        f=self.field;side=f.side
        x=max(0.,min(side-1.,(n[0]-f.x0-.5)*side/f.width-.5));y=max(0.,min(side-1.,(n[1]-f.y0-.5)*side/f.height-.5))
        x0,y0=math.floor(x),math.floor(y);x1,y1=min(side-1,x0+1),min(side-1,y0+1);tx,ty=x-x0,y-y0
        z=(1-tx)*(1-ty)*self.samples[y0*side+x0]+tx*(1-ty)*self.samples[y0*side+x1]+(1-tx)*ty*self.samples[y1*side+x0]+tx*ty*self.samples[y1*side+x1]
        if self.relative:z*=self.h(n)
        if self.taper:z*=min(1.,octile(n,self.goal)/max(f.width/side,f.height/side))
        result=(self.alpha*z,.5,1.);self.cache[n]=result;return result
