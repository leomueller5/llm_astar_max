"""Bounded search with persistent, untrusted spatial advice.

New Session7 implementation; frozen macro guidance is not modified. Advice never
changes graph costs or removes states. Envelope keys lie in [g+h,w(g+h)]; focal
selection only admits g+h<=w*min_OPEN(g+h). Both retain the optimal frontier bound
with better-cost reopening, even when advice is wrong or revised.
"""
from dataclasses import dataclass
import heapq,math
from time import perf_counter
from .geometry import SegmentGridGraph,expand_lattice_route
from .search import octile

@dataclass(frozen=True,slots=True)
class SpatialLabel:
    node:tuple
    g:float
    parent:object=None
    piece:object=None
    sequence:int=0

class RegionField:
    def __init__(self,query,side=4,graph=None,values=None):
        if type(side) is not int or not 1<=side<=16:raise ValueError('Region side must be 1..16')
        self.side=side;self.query=query;self.graph=graph or SegmentGridGraph(query)
        g=self.graph;self.x0,self.y0=g.x0,g.y0
        self.width=max(1,g.x1-g.x0-1);self.height=max(1,g.y1-g.y0-1)
        self.regions=[];self.values={};self.rejections=0
        for y in range(side):
            for x in range(side):
                lo=(g.x0+1+math.ceil(x*self.width/side),g.y0+1+math.ceil(y*self.height/side))
                hi=(g.x0+math.ceil((x+1)*self.width/side),g.y0+math.ceil((y+1)*self.height/side))
                center=(round((lo[0]+hi[0])/2),round((lo[1]+hi[1])/2));sample=None
                if lo[0]<=hi[0] and lo[1]<=hi[1]:
                    if g.valid_point(center):sample=center
                    else:
                        candidates=((xx,yy) for yy in range(lo[1],hi[1]+1) for xx in range(lo[0],hi[0]+1))
                        sample=min((p for p in candidates if g.valid_point(p)),key=lambda p:math.dist(p,center),default=None)
                self.regions.append({'id':f'R{y*side+x}','bounds':[list(lo),list(hi)],'sample':list(sample) if sample else None})
        if values is not None:self.update(values)
    def identifier(self,p):
        x=min(self.side-1,max(0,int((p[0]-self.x0-1)*self.side/self.width)))
        y=min(self.side-1,max(0,int((p[1]-self.y0-1)*self.side/self.height)))
        return f'R{y*self.side+x}'
    def update(self,values):
        if isinstance(values,dict):values=values.get('predictions',[])
        if not isinstance(values,list):raise ValueError('Expected regional prediction list')
        allowed={r['id'] for r in self.regions};parsed={};seen=set()
        for raw in values:
            if not isinstance(raw,dict):self.rejections+=1;continue
            identifier=raw.get('region_id');delta=raw.get('detour',0.);priority=raw.get('priority',.5);confidence=raw.get('confidence',1.)
            if (identifier not in allowed or identifier in seen or any(type(v) not in [int,float] or not math.isfinite(v) for v in [delta,priority,confidence]) or delta<0 or not 0<=priority<=1 or not 0<=confidence<=1):self.rejections+=1;continue
            seen.add(identifier);parsed[identifier]=(delta,priority,confidence)
        self.values=parsed
    def value(self,p):return self.values.get(self.identifier(p),(0.,.5,0.))

class SpatialSearch:
    def __init__(self,mode='envelope',bound=2.,base_weight=1.5,heuristic='cut',signal='detour',alpha=1.,
                 macro=False,interval=8,probe_budget=256,target_order='given'):
        if mode not in ['weighted','envelope','heuristic_envelope','focal','tie','dual']:raise ValueError('Unknown search mode')
        if signal not in ['detour','priority','combined']:raise ValueError('Unknown signal')
        if heuristic not in ['cut','octile','euclidean']:raise ValueError('Unknown anchor')
        if not all(math.isfinite(v) for v in [bound,base_weight,alpha]) or bound<1 or base_weight<1 or base_weight>bound or alpha<0:raise ValueError('Invalid weights')
        if type(interval) is not int or interval<1 or type(probe_budget) is not int or probe_budget<0:raise ValueError('Invalid macro budget')
        self.mode=mode;self.bound=bound;self.base_weight=base_weight;self.heuristic=heuristic;self.signal=signal;self.alpha=alpha
        if target_order not in ['given','cost']:raise ValueError('Unknown macro target ordering')
        self.target_order=target_order
        self.macro=macro;self.interval=interval;self.probe_budget=probe_budget
    def search(self,query,field=None,graph=None,targets=(),record_trace=False,revision=None,revision_after=128):
        began=perf_counter();graph=graph or SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal'])
        targets=list(dict.fromkeys(tuple(p) for p in targets if isinstance(p,(list,tuple)) and len(p)==2 and tuple(p) not in [start,goal] and graph.valid_point(tuple(p))))
        potential=None
        if self.heuristic=='cut':
            from .strategic.cuts import CutPotential
            try:potential=CutPotential(query,goal)
            except ValueError:pass
        cache={};advice_cache={};heuristic_seconds=0.;guidance_seconds=0.
        def h(n):
            nonlocal heuristic_seconds
            if n not in cache:
                tick=perf_counter();cache[n]=potential.value(n) if potential else math.dist(n,goal) if self.heuristic=='euclidean' else octile(n,goal);heuristic_seconds+=perf_counter()-tick
            return cache[n]
        scale=math.hypot(graph.x1-graph.x0,graph.y1-graph.y0)
        def advice(n):
            nonlocal guidance_seconds
            if n in advice_cache:return advice_cache[n]
            tick=perf_counter()
            delta,priority,confidence=field.value(n) if field is not None else (0.,.5,0.)
            v=delta if self.signal=='detour' else (1-2*priority)*scale*.25 if self.signal=='priority' else delta+(1-2*priority)*scale*.25
            guidance_seconds+=perf_counter()-tick
            advice_cache[n]=self.alpha*confidence*v
            return advice_cache[n]
        best={};closed={};active={};queue=[];anchor=[];waiting=[];serial=0
        pushes=pops=stale=expanded=reopens=rebuilds=probes=accepted=0;peak=0;trace=[];events=[];found=None;revision_calls=0;revision_seconds=0.
        def score(label):
            n=label.node;lower=label.g+h(n)
            if n==goal:return label.g
            if self.mode=='weighted':return label.g+self.base_weight*h(n)
            upper=label.g+self.bound*h(n) if self.mode=='heuristic_envelope' else self.bound*lower
            return min(upper,max(lower,label.g+self.base_weight*h(n)+advice(n)))
        def entry(label):
            if self.mode=='focal':return (advice(label.node)+h(label.node),h(label.node),label.node,label.sequence,label)
            if self.mode=='dual':return (label.g+self.base_weight*h(label.node)+advice(label.node),0.,label.node,label.sequence,label)
            if self.mode=='tie':return (label.g+self.base_weight*h(label.node),advice(label.node),label.node,label.sequence,label)
            return (score(label),0.,label.node,label.sequence,label)
        def offer(n,cost,parent,piece=None):
            nonlocal serial,pushes,peak
            if n in best and cost>=best[n].g-1e-12:return
            lab=SpatialLabel(n,cost,parent,tuple(piece) if piece else None,serial);serial+=1;best[n]=lab;active[n]=lab
            if self.mode=='focal':
                low=cost+h(n);heapq.heappush(anchor,(low,n,serial,lab));heapq.heappush(waiting,(low,n,serial,lab));pushes+=2
            elif self.mode=='dual':
                heapq.heappush(anchor,(cost+h(n),n,serial,lab));heapq.heappush(queue,entry(lab));pushes+=2
            else:heapq.heappush(queue,entry(lab));pushes+=1
            peak=max(peak,len(active))
        def alive(lab):return active.get(lab.node) is lab and lab.g<closed.get(lab.node,math.inf)-1e-12
        def get_label():
            nonlocal pops,stale,pushes
            if self.mode=='dual':
                while anchor and not alive(anchor[0][-1]):heapq.heappop(anchor);pops+=1;stale+=1
                while queue and not alive(queue[0][-1]):heapq.heappop(queue);pops+=1;stale+=1
                if not anchor:return None
                threshold=self.bound*anchor[0][0]
                if queue and queue[0][-1].g+h(queue[0][-1].node)<=threshold+1e-12:
                    *_,lab=heapq.heappop(queue);pops+=1;return lab
                *_,lab=heapq.heappop(anchor);pops+=1;return lab
            if self.mode!='focal':
                while queue:
                    *_,lab=heapq.heappop(queue);pops+=1
                    if alive(lab):return lab
                    stale+=1
                return None
            while anchor and not alive(anchor[0][-1]):heapq.heappop(anchor);pops+=1;stale+=1
            if not anchor:return None
            threshold=self.bound*anchor[0][0]
            while waiting and waiting[0][0]<=threshold+1e-12:
                *_,lab=heapq.heappop(waiting);pops+=1
                if alive(lab):heapq.heappush(queue,entry(lab));pushes+=1
                else:stale+=1
            while queue:
                *_,lab=heapq.heappop(queue);pops+=1
                if not alive(lab):stale+=1;continue
                if lab.g+h(lab.node)>threshold+1e-12:
                    heapq.heappush(waiting,(lab.g+h(lab.node),lab.node,lab.sequence,lab));pushes+=1;continue
                return lab
            # The anchor's minimum must be eligible; retaining this fallback also
            # tolerates inconsistent anchors and focal-threshold decreases.
            *_,lab=heapq.heappop(anchor);pops+=1
            return lab if alive(lab) else None
        if graph.valid_point(start) and graph.valid_point(goal) and math.isfinite(h(start)):offer(start,0.,None)
        prep=perf_counter()-began
        while active:
            label=get_label()
            if label is None:break
            n=label.node;active.pop(n,None);reopens+=int(n in closed);closed[n]=label.g;expanded+=1
            if record_trace:trace.append({'node':n,'g':label.g,'expanded':expanded,'region':field.identifier(n) if isinstance(field,RegionField) else None})
            if n==goal:found=label;break
            if revision is not None and revision_calls==0 and len(closed)>=revision_after:
                t=perf_counter();revision_calls+=1
                replacement=revision({'query':query,'expanded':expanded,'unique':len(closed),'current':list(n),'g':label.g,'anchor':h(n),'region_expansions':dict(__import__('collections').Counter(field.identifier(p) for p in closed)) if isinstance(field,RegionField) else {},'frontier':[{'node':list(l.node),'g':l.g,'h':h(l.node)} for l in sorted(active.values(),key=lambda l:l.g+h(l.node))[:8]]})
                revision_seconds+=perf_counter()-t
                if replacement is not None:
                    field=replacement;advice_cache.clear()
                    if self.mode=='focal':
                        queue.clear();anchor[:]=[(l.g+h(l.node),l.node,l.sequence,l) for l in active.values()];waiting[:]=list(anchor);heapq.heapify(anchor);heapq.heapify(waiting)
                    else:
                        queue[:]=[entry(l) for l in active.values()];heapq.heapify(queue)
                        if self.mode=='dual':
                            anchor[:]=[(l.g+h(l.node),l.node,l.sequence,l) for l in active.values()];heapq.heapify(anchor)
                    rebuilds+=1;events.append({'expanded':expanded,'event':'field_revision','active':len(active)})
            if self.macro and (expanded==1 or expanded%self.interval==0):
                choices=[p for p in targets if p!=n and label.g+octile(n,p)<getattr(best.get(p),'g',math.inf)-1e-12]
                if self.target_order=='cost':choices.sort(key=lambda p:octile(n,p)+h(p)+advice(p))
                for target in [goal]+choices[:3]:
                    if probes>=self.probe_budget:break
                    cost=label.g+octile(n,target)
                    if target==n or cost>=getattr(best.get(target),'g',math.inf)-1e-12:continue
                    probes+=1;piece=graph.lattice_segment(n,target)
                    if piece:offer(target,cost,label,piece);accepted+=1
            for other,cost in graph.adj.get(n,[]):offer(other,label.g+cost,label)
        path=[]
        if found:
            pieces=[];cur=found
            while cur.parent is not None:
                pieces.append(expand_lattice_route(cur.piece) if cur.piece else [cur.parent.node,cur.node]);cur=cur.parent
            path=[start]
            for piece in reversed(pieces):path.extend(piece[1:])
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        elapsed=perf_counter()-began
        return dict(path=path if valid else [],valid=valid,length=length,operation=pops,storage=len(best),llm_output=[],
            expanded=expanded,unique=len(closed),stale=stale,reopens=reopens,heap_pushes=pushes,heap_pops=pops,
            rebuilds=rebuilds,peak_open_states=peak,macro_probes=probes,macro_accepted=accepted,trace=trace,events=events,
            preprocess_seconds=prep,search_seconds=elapsed-prep-revision_seconds,total_seconds=elapsed,
            heuristic_seconds=heuristic_seconds,guidance_seconds=guidance_seconds,revision_calls=revision_calls,revision_seconds=revision_seconds)
    def searching(self,query,filepath='temp.png',**kwargs):return self.search(query,**kwargs)
