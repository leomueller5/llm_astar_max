"""A* with advice-selected, physically verified macro edges.

An LLM proposes targets, not costs or collision claims. Sparse opportunities
connect an expanded cell to a target using a verified shortest lattice walk.
All original unit edges remain available. Reopenings and immutable parent labels
preserve correctness. With admissible Euclidean/octile h and weight w>=1, the
usual Weighted-A* w-bound applies: added edges are real paths in the same grid.
"""
from dataclasses import dataclass
import heapq
import math
from time import perf_counter

from .geometry import SegmentGridGraph,expand_lattice_route
from .search import octile


@dataclass(frozen=True,slots=True)
class MacroLabel:
    node:tuple
    g:float
    parent:object=None
    piece:object=None


class MacroGuidedSearch:
    def __init__(self,weight=2.,interval=8,probes_per_event=3,
                 probe_budget=256,initial_chain=False,dynamic=True,
                 goal_probes=True,heuristic='euclidean',target_order='given',
                 require_descent=False,trust_cell_size=8):
        if (not math.isfinite(weight) or weight<1 or
            any(type(v) is not int for v in [interval,probes_per_event,probe_budget]) or
            interval<1 or probes_per_event<1 or probe_budget<0):
            raise ValueError('Invalid macro-guidance configuration')
        if heuristic not in ['euclidean','octile','cut']:
            raise ValueError('Unknown anchor heuristic')
        if target_order not in ['given','regret','priority','adaptive']:
            raise ValueError('Unknown target ordering')
        if type(trust_cell_size) is not int or trust_cell_size<1:
            raise ValueError('Positive integer trust cell size required')
        self.weight=weight;self.interval=interval;self.per_event=probes_per_event
        self.budget=probe_budget;self.initial_chain=initial_chain;self.dynamic=dynamic
        self.goal_probes=goal_probes;self.heuristic=heuristic
        self.target_order=target_order
        self.require_descent=require_descent;self.trust_cell_size=trust_cell_size

    def search(self,query,waypoints=(),graph=None,record_trace=False,revision=None,
               intervention_after=32,failure_window=6):
        if type(intervention_after) is not int or intervention_after<1 or type(failure_window) is not int or failure_window<1:
            raise ValueError('Positive intervention thresholds required')
        tick=perf_counter();graph=graph or SegmentGridGraph(query)
        start,goal=tuple(query['start']),tuple(query['goal'])
        targets=[]
        for raw in waypoints:
            if not isinstance(raw,(list,tuple)) or len(raw)!=2:
                continue
            p=tuple(raw)
            if p not in [start,goal] and p not in targets and graph.valid_point(p):
                targets.append(p)
        potential=None
        if self.heuristic=='cut':
            from .strategic.cuts import CutPotential
            try:
                potential=CutPotential(query,goal)
            except ValueError:
                potential=None
        cache={}
        def h(n):
            if n not in cache:
                cache[n]=potential.value(n) if potential is not None else math.dist(n,goal) if self.heuristic=='euclidean' else octile(n,goal)
            return cache[n]
        queue=[];best={};closed={};sequence=0
        probes=accepted=pushes=pops=stale=expanded=reopens=peak=0
        macro_seconds=0.;trace=[];events=[];found=None
        recent=[];revision_calls=0;revision_seconds=0.
        trust={};trust_updates=0

        def trust_key(node,target):
            return node[0]//self.trust_cell_size,node[1]//self.trust_cell_size,target

        def offer(node,cost,parent,piece=None):
            nonlocal sequence,pushes,peak
            old=best.get(node)
            if old is not None and cost>=old.g-1e-12:
                return None
            label=MacroLabel(node,cost,parent,tuple(piece) if piece else None)
            best[node]=label
            heapq.heappush(queue,(cost+self.weight*h(node),node,sequence,label))
            sequence+=1;pushes+=1;peak=max(peak,len(queue))
            return label

        def connect(label,target,kind):
            nonlocal probes,accepted,macro_seconds,trust_updates
            if probes>=self.budget or target==label.node:
                return None
            cost=label.g+octile(label.node,target)
            if target in best and cost>=best[target].g-1e-12:
                return None
            if self.require_descent and cost+self.weight*h(target)>label.g+self.weight*h(label.node)+1e-12:
                return None
            began=perf_counter();probes+=1
            corners=graph.lattice_segment(label.node,target)
            result=None
            if corners:
                result=offer(target,cost,label,corners)
                accepted+=int(result is not None)
            if kind=='advice':
                recent.append({'from':label.node,'target':target,'verified':bool(corners)})
                del recent[:-32]
                if self.target_order=='adaptive':
                    key=trust_key(label.node,target);success,failed=trust.get(key,(0,0))
                    trust[key]=(success+int(bool(corners)),failed+int(not corners));trust_updates+=1
            macro_seconds+=perf_counter()-began
            if record_trace:
                events.append({'expanded':expanded,'from':label.node,'target':target,
                               'kind':kind,'valid':bool(corners),'offered':result is not None})
            return result

        valid_endpoints=graph.valid_point(start) and graph.valid_point(goal)
        if valid_endpoints:
            first=offer(start,0.,None)
            if self.initial_chain:
                cursor=first
                for target in targets+[goal]:
                    cursor=connect(cursor,target,'initial_chain')
                    if cursor is None:
                        break
        prep=perf_counter()-tick
        while queue:
            _,node,_,label=heapq.heappop(queue);pops+=1
            if best.get(node) is not label or label.g>=closed.get(node,math.inf)-1e-12:
                stale+=1;continue
            reopens+=int(node in closed);closed[node]=label.g;expanded+=1
            if record_trace:
                trace.append({'node':node,'g':label.g,'expanded':expanded})
            if node==goal:
                found=label;break
            if (revision is not None and revision_calls==0 and len(closed)>=intervention_after
                and self.budget-probes>=self.per_event
                and len(recent)>=failure_window and sum(r['verified'] for r in recent[-failure_window:])<=1):
                began=perf_counter();revision_calls+=1
                revised=revision({'query':query,'event':'repeated_failed_macro_links',
                    'expanded':expanded,'unique':len(closed),'current_node':node,'current_g':label.g,
                    'anchor_value':h(node),'open_entries':len(queue),
                    'failed_macro_links':list(recent[-failure_window:]),'previous_targets':list(targets)})
                revision_seconds+=perf_counter()-began
                if revised is not None:
                    replacement=[]
                    for raw in revised[:32]:
                        if not isinstance(raw,(list,tuple)) or len(raw)!=2:continue
                        p=tuple(raw)
                        if p not in [start,goal] and p not in replacement and graph.valid_point(p):replacement.append(p)
                    targets=replacement
                events.append({'event':'macro_revision','expanded':expanded,'unique':len(closed),
                               'new_targets':list(targets),'changed':revised is not None})
            if self.dynamic and (expanded==1 or expanded%self.interval==0) and probes<self.budget:
                if self.goal_probes:
                    connect(label,goal,'goal')
                choices=[p for p in targets if p!=node and label.g+octile(node,p)<getattr(best.get(p),'g',math.inf)-1e-12]
                if self.target_order=='regret':
                    choices.sort(key=lambda p:(octile(node,p)+h(p),p))
                elif self.target_order in ['priority','adaptive']:
                    current=self.weight*h(node)
                    def opportunity(p):
                        gain=max(0.,current-octile(node,p)-self.weight*h(p))
                        if self.target_order=='adaptive':
                            success,failed=trust.get(trust_key(node,p),(0,0))
                            gain*=(1+success)/(2+success+failed)
                        return -gain
                    choices.sort(key=opportunity)
                # The advisory list is ordered by its provider. This choice is
                # deliberately independent of any hidden reference trajectory.
                for target in choices[:self.per_event]:
                    connect(label,target,'advice')
            for other,edge in graph.adj.get(node,[]):
                offer(other,label.g+edge,label)
        path=[]
        if found:
            pieces=[];cursor=found
            while cursor.parent is not None:
                piece=expand_lattice_route(cursor.piece) if cursor.piece else [cursor.parent.node,cursor.node]
                pieces.append(piece);cursor=cursor.parent
            path=[start]
            for piece in reversed(pieces):
                path.extend(piece[1:])
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        length=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        if valid:
            assert abs(length-found.g)<1e-7
        elapsed=perf_counter()-tick
        return {'path':path if valid else [],'valid':valid,'length':length,'operation':pops,
                'expanded':expanded,'unique':len(closed),'stale':stale,'duplicates':0,
                'reopens':reopens,'heap_pops':pops,'heap_pushes':pushes,'rebuilds':0,
                'storage':len(best),'peak_open_entries':peak,'macro_probes':probes,
                'macro_accepted':accepted,'macro_seconds':macro_seconds,
                'preprocess_seconds':prep,'search_seconds':elapsed-prep-revision_seconds,
                'revision_calls':revision_calls,'revision_seconds':revision_seconds,
                'trust_updates':trust_updates,'trust_contexts':len(trust),
                'total_seconds':elapsed,'events':events,'trace':trace,'processed_waypoints':targets}
