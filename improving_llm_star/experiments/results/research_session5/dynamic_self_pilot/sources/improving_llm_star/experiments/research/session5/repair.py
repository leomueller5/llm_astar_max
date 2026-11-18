"""Evidence-gated online repair directly extends the frozen LLMAStar class.

The original heuristic, OPEN/CLOSED algorithm and waypoint switching remain
unchanged. Only a bounded external guidance intervention and queue rekey are
added. No claim of optimality or new invention of feedback planning is made.
"""
import math,sys,json
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prompts import feedback_for
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.search import octile


def quality(query,points):
    graph=SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal']);invalid=sum(not graph.valid_point(tuple(p)) for p in points)
    route=[start]+[tuple(p) for p in points if tuple(p) not in [start,goal]]+[goal]
    failed=sum(graph.lattice_segment(a,b) is None for a,b in zip(route,route[1:]));links=max(1,len(route)-1)
    length=sum(octile(a,b) for a,b in zip(route,route[1:]))
    # Empirical evidence score, NOT an admissible bound or proof of usefulness.
    return invalid,failed/links,length


def repaired_class(Original):
    class Repaired(Original):
        def set_repair(self,query,points,callback,threshold=16,gated=True):
            self.repair_query=query;self.repair_points=points;self.repair_callback=callback;self.repair_threshold=threshold;self.repair_gated=gated
            self.repair_attempts=0;self.repair_accepted=0;self.repair_seconds=0.;self.repair_events=[];self.contradiction=feedback_for(query,points)
        def get_neighbor(self,node):
            if self.contradiction is not None and not self.repair_attempts and len(self.CLOSED)>=self.repair_threshold:
                self.repair_attempts+=1;tick=perf_counter()
                context={'query':self.repair_query,'event':'contradicted_guidance_still_searching','expanded':len(self.CLOSED),'current_node':node,'current_g':self.g[node],'active_target':self.s_target,'open_entries':len(self.OPEN),'contradiction':self.contradiction}
                new=self.repair_callback(context)
                self.repair_seconds+=perf_counter()-tick
                oldscore=quality(self.repair_query,self.repair_points);newscore=quality(self.repair_query,new) if new is not None else None
                accept=new is not None and (not self.repair_gated or newscore<oldscore)
                if accept:
                    targets=self._filter_valid_nodes(new)
                    if not targets or targets[0]!=self.s_start:targets.insert(0,self.s_start)
                    if not targets or targets[-1]!=self.s_goal:targets.append(self.s_goal)
                    if targets!=self.target_list:
                        self.target_list=targets;self.i=1;self.s_target=self.target_list[1];self._update_queue();self.repair_accepted+=1
                self.repair_events.append({'expanded':len(self.CLOSED),'node':node,'accepted':bool(accept),'old_evidence':oldscore,'new_evidence':newscore,'changed_queue':bool(self.repair_accepted)})
            return super().get_neighbor(node)
    return Repaired
