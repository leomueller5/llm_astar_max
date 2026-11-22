"""Effort-bounded local refinement of structured strategy alternatives.

A route proposal only becomes an incumbent after every local link is constructed.
Local repair is deliberately bounded; complete global fallback belongs to the
caller. Expanded states/heap work are retained rather than hidden as preprocessing.
"""
import heapq,math
from time import perf_counter
from .schema import StrategicGuidance,Strategy
from ..geometry import SegmentGridGraph,expand_lattice_route
from ..search import octile
from ..efficient import compress_collinear


def bounded_link(graph,start,goal,budget,expanded_states):
    g={start:0.};parents={};closed={};queue=[(octile(start,goal),start,0.)];pops=expanded=0
    while queue and expanded<budget:
        _,node,old=heapq.heappop(queue);pops+=1
        if old!=g[node] or old>=closed.get(node,math.inf):continue
        closed[node]=old;expanded+=1;expanded_states.add(node)
        if node==goal:
            path=[node]
            while path[-1]!=start:path.append(parents[path[-1]])
            return list(reversed(path)),pops,expanded
        for other,cost in graph.adj.get(node,[]):
            new=old+cost
            if new<g.get(other,math.inf)-1e-12:
                g[other]=new;parents[other]=node;heapq.heappush(queue,(new+octile(other,goal),other,new))
    return [],pops,expanded


def bypass_targets(query,strategy):
    """Ordered obstacle IDs avoid asking a model to calculate endpoint offsets."""
    points=[]
    for b in strategy.bypasses:
        kind=b.obstacle_id[0];i=int(b.obstacle_id[1:]);walls=query['vertical_barriers'] if kind=='v' else query['horizontal_barriers']
        if i>=len(walls):continue
        fixed,lo,hi=walls[i]
        if kind=='v' and b.side in ['above','below']:points.append((fixed,hi+1 if b.side=='above' else lo-1))
        elif kind=='h' and b.side in ['left','right']:points.append((hi+1 if b.side=='right' else lo-1,fixed))
    return points


class LocalRouteProvider:
    def __init__(self,underlying,graph=None,total_expansions=128,per_link=32,lookahead=8,shortcut=True):
        if total_expansions<0 or per_link<0 or lookahead<1:raise ValueError('Invalid local route budget')
        self.underlying=underlying;self.graph=graph;self.total_expansions=total_expansions;self.per_link=per_link;self.lookahead=lookahead;self.shortcut=shortcut
        self.expanded_states=set();self.local_expanded=self.local_pops=self.local_links=self.segment_probes=0
        self.processing_seconds=0.;self.calls=0;self.events=[];self.source='local_refinement_'+underlying.source;self.can_revise=underlying.can_revise
        self.actual_api_calls=0;self.actual_tokens=None;self.actual_cost=0.;self.simulated_latency_seconds=0.;self.candidate_log=[]

    def propose(self,context):
        began=perf_counter();advice=self.underlying.propose(context);self.calls+=1;query=context.query;graph=self.graph or SegmentGridGraph(query)
        start,goal=tuple(query['start']),tuple(query['goal']);result=[]
        for strategy in advice.strategies:
            raw=strategy.waypoints or bypass_targets(query,strategy)
            targets=compress_collinear([start]+[tuple(p) for p in raw if graph.valid_point(p)]+[goal])
            path=[start];index=0;ok=True
            while index<len(targets)-1:
                chosen=None;piece=None
                # Geometric shortcuts are actual checked links, not line distances.
                last=min(len(targets)-1,index+self.lookahead) if self.shortcut else index+1
                for j in range(last,index,-1):
                    self.segment_probes+=1;piece=graph.lattice_segment(path[-1],targets[j])
                    if piece:chosen=j;break
                if chosen is not None:
                    path.extend(expand_lattice_route(piece)[1:]);index=chosen;continue
                remaining=self.total_expansions-self.local_expanded
                if remaining<=0:ok=False;break
                self.local_links+=1
                link,pops,expanded=bounded_link(graph,path[-1],targets[index+1],min(self.per_link,remaining),self.expanded_states)
                self.local_pops+=pops;self.local_expanded+=expanded
                if not link:ok=False;break
                path.extend(link[1:]);index+=1
            self.candidate_log.append({'id':strategy.identifier,'valid':ok,'length':sum(math.dist(a,b) for a,b in zip(path,path[1:])) if ok else None,'steps':len(path)-1})
            if ok:result.append(Strategy(strategy.identifier+'_locally_verified',strategy.confidence,tuple(compress_collinear(path))))
        self.events.append({'event':context.event,'input_candidates':len(advice.strategies),'valid_candidates':len(result),'expanded':self.local_expanded})
        self.actual_api_calls=self.underlying.actual_api_calls;self.simulated_latency_seconds=self.underlying.simulated_latency_seconds
        self.processing_seconds+=perf_counter()-began
        return StrategicGuidance(tuple(result),self.source,not result,advice.warnings)
