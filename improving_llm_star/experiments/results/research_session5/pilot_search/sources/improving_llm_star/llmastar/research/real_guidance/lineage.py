"""Path-consistent adaptive guidance: target progress belongs to a real path.

Immutable parent labels keep stage claims valid even when another branch improves
an ancestor. No global rekey occurs for branch-local stage changes. The bounded
score is between h_goal and 2*h_goal; better-g reopenings retain factor2 search.
"""
from dataclasses import dataclass
from time import perf_counter
import math,heapq,itertools
from ..geometry import SegmentGridGraph
from ..search import MOTIONS,octile


@dataclass(frozen=True,slots=True)
class Label:
    node:tuple
    g:float
    stage:int
    anchor:tuple
    anchor_g:float
    parent:object=None


class PathConsistentSearch:
    def __init__(self,progress='lineage',score='original',trust=False,path_budget=False,
                 budget_scale=2.,minimum_budget=8.,guidance=True,skip_unverified=False,
                 intervention_after=None):
        if progress not in ['lineage','global_pop','global_neighbor'] or score not in ['original','normalized','bounded']:raise ValueError('Unknown guidance mode')
        if budget_scale<=0 or minimum_budget<=0:raise ValueError('Positive guidance budgets required')
        self.progress=progress;self.score=score;self.trust=trust;self.path_budget=path_budget;self.scale=budget_scale;self.minimum=minimum_budget;self.guidance=guidance;self.skip_unverified=skip_unverified;self.intervention_after=intervention_after

    def search(self,query,waypoints=(),graph=None,revision=None,record_trace=False):
        began=perf_counter();graph=graph or SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal']);events=[];trace=[]
        validations=0;targets=[];weights=[];global_stage=0
        def prepare(points):
            nonlocal targets,weights,validations
            clean=[]
            for raw in points:
                if not isinstance(raw,(list,tuple)) or len(raw)!=2:continue
                p=tuple(raw)
                if p in [start,goal] or not graph.valid_point(p):continue
                if not clean or p!=clean[-1]:clean.append(p)
            targets=clean if self.guidance else [];weights=[]
            chain=[start]+targets+[goal]
            for i,t in enumerate(targets):
                if not self.trust:weights.append(1.);continue
                a,b=chain[i],chain[i+2];validations+=2
                reliability=(int(graph.lattice_segment(a,t) is not None)+int(graph.lattice_segment(t,b) is not None))/2
                excess=max(0,octile(a,t)+octile(t,b)-octile(a,b))
                weights.append(reliability/(1+excess/max(1,octile(a,b))))
        prepare(waypoints);initial_targets=list(targets);initial_weights=list(weights)
        sequence=itertools.count();queue=[];best={};live={};closed={};pushes=pops=expanded=stale=reopens=rebuilds=labels_created=0;peak_open=0;revision_calls=0;revision_seconds=0.
        def priority(label):
            h=math.dist(label.node,goal);i=label.stage if self.progress=='lineage' else global_stage
            if i>=len(targets):return label.g+2*h
            d=math.dist(label.node,targets[i]);alpha=weights[i]
            if self.score=='original':return label.g+h+alpha*d
            if self.score=='normalized':return label.g+(2-alpha)*h+alpha*d
            return label.g+2*h-alpha*max(0,h-d)
        def resolve(node,cost,stage,anchor,anchor_g):
            resolved=[]
            while stage<len(targets):
                reason=None
                if node==targets[stage]:reason='reached_on_path'
                elif self.skip_unverified and weights[stage]==0:reason='unverified_skipped'
                elif self.path_budget and cost-anchor_g>max(self.minimum,self.scale*octile(anchor,targets[stage])):reason='path_cost_budget'
                if reason is None:break
                resolved.append({'expansion':expanded,'node':node,'target':targets[stage],'stage':stage,'reason':reason,'path_cost_since_activation':cost-anchor_g})
                stage+=1;anchor=node;anchor_g=cost
            return stage,anchor,anchor_g,resolved
        def put(label):
            nonlocal pushes,peak_open
            live[label.node]=label;heapq.heappush(queue,(priority(label),label.node,next(sequence),label));pushes+=1;peak_open=max(peak_open,len(queue))
        valid_endpoints=graph.valid_point(start) and graph.valid_point(goal)
        first_stage,anchor,anchor_g,initial_events=resolve(start,0.,0,start,0.) if self.progress=='lineage' else (0,start,0.,[])
        events.extend(initial_events)
        first=Label(start,0.,first_stage,anchor,anchor_g);best[start]=first;labels_created+=1
        if valid_endpoints:put(first)
        prep=perf_counter()-began;found=None
        while queue:
            _,node,_,label=heapq.heappop(queue);pops+=1
            if best.get(node) is not label or live.get(node) is not label:stale+=1;continue
            del live[node];prior=closed.get(node)
            if prior and (label.g>prior[0]+1e-12 or abs(label.g-prior[0])<=1e-12 and label.stage<=prior[1]):stale+=1;continue
            reopens+=int(prior is not None);closed[node]=(label.g,label.stage);expanded+=1
            if record_trace:
                prefix=[];cur=label
                while cur is not None:prefix.append(cur.node);cur=cur.parent
                trace.append({'node':node,'g':label.g,'stage':label.stage,'priority':priority(label),'ancestry':list(reversed(prefix))})
            if node==goal:found=label;break
            changed=False
            if self.progress!='lineage':
                if self.progress=='global_pop' and global_stage<len(targets) and node==targets[global_stage]:
                    events.append({'expansion':expanded,'node':node,'target':targets[global_stage],'stage':global_stage,'reason':'global_pop'});global_stage+=1;changed=True
                elif self.progress=='global_neighbor':
                    for dx,dy in MOTIONS:
                        if global_stage<len(targets) and (node[0]+dx,node[1]+dy)==targets[global_stage]:
                            events.append({'expansion':expanded,'node':node,'target':targets[global_stage],'stage':global_stage,'reason':'global_neighbor'});global_stage+=1;changed=True
                if changed and live:
                    queue[:]=[(priority(x),x.node,next(sequence),x) for x in live.values()];heapq.heapify(queue);rebuilds+=1
            for other,edge in graph.adj.get(node,[]):
                cost=label.g+edge
                if self.progress=='lineage':i,a,ag,resolved=resolve(other,cost,label.stage,label.anchor,label.anchor_g)
                else:i,a,ag,resolved=0,start,0.,[]
                old=best.get(other)
                if old is not None and not (cost<old.g-1e-12 or abs(cost-old.g)<=1e-12 and i>old.stage):continue
                events.extend(resolved)
                nxt=Label(other,cost,i,a,ag,label);labels_created+=1;best[other]=nxt;put(nxt)
            if revision is not None and not revision_calls and self.intervention_after and expanded>=self.intervention_after:
                tick=perf_counter();new=revision({'query':query,'event':'excess_guidance_effort','expanded':expanded,'current_node':node,'active_target':targets[label.stage if self.progress=='lineage' else global_stage] if (label.stage if self.progress=='lineage' else global_stage)<len(targets) else goal,'remaining_open':len(live)})
                revision_seconds+=perf_counter()-tick;revision_calls+=1
                if new is not None:
                    prepare(new);global_stage=0
                    # Reinterpret only live records with conservative progress0;
                    # actual immutable prefixes stay valid. No target is falsely
                    # claimed reached on an old unrelated branch.
                    for n,old in list(live.items()):
                        i,a,ag,resolved=resolve(n,old.g,0,n,old.g) if self.progress=='lineage' else (0,n,old.g,[])
                        events.extend(resolved)
                        fresh=Label(n,old.g,i,a,ag,old.parent);best[n]=fresh;live[n]=fresh;labels_created+=1
                    queue[:]=[(priority(x),x.node,next(sequence),x) for x in live.values()];heapq.heapify(queue);rebuilds+=int(bool(live))
                    events.append({'expansion':expanded,'reason':'external_revision','new_targets':targets})
        path=[]
        if found:
            cursor=found
            while cursor is not None:path.append(cursor.node);cursor=cursor.parent
            path.reverse()
        valid=bool(path) and path[0]==start and path[-1]==goal and all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
        cost=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if valid else None
        if found and valid:assert abs(cost-found.g)<1e-7
        return dict(path=path if valid else [],valid=valid,length=cost,operation=pops,heap_pops=pops,heap_pushes=pushes,expanded=expanded,unique=len(closed),stale=stale,reopens=reopens,rebuilds=rebuilds,storage=len(best),labels_created=labels_created,peak_open_entries=peak_open,events=events,trace=trace,processed_waypoints=initial_targets,waypoint_weights=initial_weights,segment_validations=validations,preprocess_seconds=prep,search_seconds=perf_counter()-began-prep-revision_seconds,total_seconds=perf_counter()-began,revision_seconds=revision_seconds,revision_calls=revision_calls)
