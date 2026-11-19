"""Direct frozen-LLM-A* extension: verified advisory macro neighbors.

Original scoring, unit neighbors, switching and duplicate behavior are preserved.
Long neighbors carry exactly verified grid-walk costs. The returned path is dense.
This variant inherits the original lack of an optimality/suboptimality guarantee.
"""
import math
from time import perf_counter
from llmastar.research.geometry import expand_lattice_route
from llmastar.research.search import octile


def macro_class(Original):
    class MacroOriginal(Original):
        def set_macro(self,graph,interval=8,budget=256,lookahead=3,enabled=True,confidence=None):
            if interval<1 or budget<0 or lookahead<1:
                raise ValueError('Invalid macro settings')
            self.macro_graph=graph;self.macro_interval=interval;self.macro_budget=budget
            self.macro_lookahead=lookahead;self.macro_enabled=enabled
            self.macro_edges={};self.macro_probes=0;self.macro_accepted=0;self.macro_seconds=0.
            self.macro_confidence=confidence

        def get_neighbor(self,node):
            neighbors=super().get_neighbor(node)
            if not self.macro_enabled or self.macro_probes>=self.macro_budget:
                return neighbors
            if len(self.CLOSED)!=1 and len(self.CLOSED)%self.macro_interval:
                return neighbors
            targets=[self.s_goal]+self.target_list[self.i:self.i+self.macro_lookahead]
            tick=perf_counter()
            for target in dict.fromkeys(targets):
                if self.macro_probes>=self.macro_budget:
                    break
                if target==node or target in neighbors or target in self.CLOSED:
                    continue
                if self.g[node]+octile(node,target)>=self.g.get(target,math.inf)-1e-12:
                    continue
                self.macro_probes+=1
                piece=self.macro_graph.lattice_segment(node,target)
                if piece:
                    self.macro_edges[node,target]=tuple(piece)
                    neighbors.append(target);self.macro_accepted+=1
            self.macro_seconds+=perf_counter()-tick
            return neighbors

        def cost(self,a,b):
            if (a,b) in self.macro_edges:
                return octile(a,b)
            return self.macro_graph.cost(a,b)

        def extract_path(self,parent):
            coarse=super().extract_path(parent)
            path=[coarse[0]]
            for a,b in zip(coarse,coarse[1:]):
                corners=self.macro_edges.get((a,b))
                if corners:
                    path.extend(expand_lattice_route(corners)[1:])
                else:
                    path.append(b)
            return path

        def heuristic(self,node):
            if self.macro_confidence is None or self.s_target==self.s_goal:
                return super().heuristic(node)
            # Explicit optional normalization: alpha=0 retains original final
            # goal weight 2; alpha=1 is exactly original intermediate scoring.
            h=math.dist(node,self.s_goal);d=math.dist(node,self.s_target)
            return (2-self.macro_confidence)*h+self.macro_confidence*d

    return MacroOriginal
