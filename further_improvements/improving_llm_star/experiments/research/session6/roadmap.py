"""Sparse verified geometric roadmaps and LLM-proposed missing connections.

No grid reference solution is used. Graph-optimal does not mean grid-optimal.
Unrestricted cut search remains the complete bounded-quality fallback.
"""
import heapq
import json
import math
from time import perf_counter
from hybrid import endpoints,SYSTEM,clean
from strategic import schema
from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route
from llmastar.research.search import octile


class Roadmap:
    def __init__(self,query,graph=None,k=4):
        if k is not None and (type(k) is not int or k<1):raise ValueError('Positive k or full graph')
        tick=perf_counter();self.query=query;self.grid=graph or SegmentGridGraph(query)
        self.points={'S':tuple(query['start']),'G':tuple(query['goal'])}
        for identifier,p in endpoints(query).items():
            if p not in self.points.values():self.points[identifier]=p
        self.adj={i:{} for i in self.points};self.status={};self.pieces={};self.probes=0;self.extra_probes=0
        self.expanded_points=set()
        pairs=set()
        for a,p in self.points.items():
            neighbors=sorted((i for i in self.points if i!=a),key=lambda b:(octile(p,self.points[b]),b))
            for b in neighbors[:k] if k else neighbors:
                pairs.add(tuple(sorted((a,b))))
        for a,b in sorted(pairs):self.verify(a,b)
        self.preprocess_seconds=perf_counter()-tick

    def verify(self,a,b):
        key=tuple(sorted((a,b)))
        if key in self.status:return self.status[key]
        self.probes+=1
        p,q=self.points[a],self.points[b]
        piece=self.grid.lattice_segment(p,q)
        self.status[key]=bool(piece)
        if piece:
            value=octile(p,q)
            self.adj[a][b]=value;self.adj[b][a]=value
            self.pieces[a,b]=tuple(piece)
        return bool(piece)

    def shortest(self):
        g={'S':0.};parent={};queue=[(0.,'S')];push=1;pop=expanded=0
        while queue:
            old,node=heapq.heappop(queue);pop+=1
            if old!=g[node]:continue
            expanded+=1;self.expanded_points.add(self.points[node])
            if node=='G':
                ids=['G']
                while ids[-1]!='S':ids.append(parent[ids[-1]])
                return list(reversed(ids)),old,{'pushes':push,'pops':pop,'expanded':expanded}
            for other,cost in self.adj[node].items():
                value=old+cost
                if value<g.get(other,math.inf)-1e-12:
                    g[other]=value;parent[other]=node;heapq.heappush(queue,(value,other));push+=1
        return [],math.inf,{'pushes':push,'pops':pop,'expanded':expanded}

    def proposal(self,result=None):
        ids,cost,work=result or self.shortest()
        return {'node_positions':self.points,
            'verified_neighbors':{i:{j:round(c,3) for j,c in edges.items()} for i,edges in self.adj.items()},
            'verified_blocked_links':[list(k) for k,v in self.status.items() if not v],
            'geometric_route':ids,'geometric_route_cost':cost if math.isfinite(cost) else None,
            'geometric_search_work':work,'visibility_probes':self.probes,
            'preprocess_seconds':self.preprocess_seconds}

    def dense_path(self,ids):
        if not ids:return []
        path=[self.points[ids[0]]]
        for a,b in zip(ids,ids[1:]):
            piece=self.pieces.get((a,b))
            if piece is None:piece=tuple(reversed(self.pieces[b,a]))
            path.extend(expand_lattice_route(piece)[1:])
        return path

    def lazy_augment(self,budget):
        """LazySP-style optimistic complete roadmap, with a hard probe budget.

        Its optimistic graph cost is NOT used as a grid lower bound.
        """
        began=self.probes
        while self.probes-began<budget:
            costs={'S':0.};parents={};queue=[(0.,'S')];route=[]
            while queue:
                old,node=heapq.heappop(queue)
                if old!=costs[node]:continue
                self.expanded_points.add(self.points[node])
                if node=='G':
                    route=['G']
                    while route[-1]!='S':route.append(parents[route[-1]])
                    route.reverse();break
                for other in self.points:
                    if other==node or self.status.get(tuple(sorted((node,other)))) is False:continue
                    new=old+octile(self.points[node],self.points[other])
                    if new<costs.get(other,math.inf)-1e-12:
                        costs[other]=new;parents[other]=node;heapq.heappush(queue,(new,other))
            if not route:break
            missing=next(((a,b) for a,b in zip(route,route[1:]) if tuple(sorted((a,b))) not in self.status),None)
            if missing is None:break
            self.verify(*missing)
        return self.shortest()


def roadmap_messages(query,proposal,version='complete'):
    payload={'roadmap':{k:v for k,v in proposal.items() if k!='preprocess_seconds'}}
    if version=='complete':payload['map']=query
    instruction=('Plan from node S to node G using the geometric candidate IDs. '
        'Every supplied neighbor link is a physically verified shortest lattice '
        'walk; explicitly blocked links must never be used. Missing links are '
        'UNKNOWN, not necessarily blocked. Propose up to TWO short coherent '
        'routes. You may connect currently non-neighbor nodes if the wall map '
        'suggests the connection is clear; geometry will check it. Improve the '
        'sparse geometric route or connect its missing passages. Do not return '
        'coordinates. Include S and G in each route. No optimal reference path '
        'has been supplied.\n')
    if version=='graph_only':
        instruction=('Find up to TWO short S-to-G routes using ONLY the explicitly '
            'verified neighbor links. If no connection exists, abstain with an '
            'empty route list. Include S and G. No prose.\n')
    fmt=schema('roadmap_completion',{'routes':{'type':'array','maxItems':2,
        'items':{'type':'array','maxItems':16,'items':{'type':'string','enum':list(proposal['node_positions'])}}}})
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction+json.dumps(payload,separators=(',',':'))}],fmt


def complete_routes(roadmap,routes):
    """Verify proposed edges once; return factual route costs and added edges."""
    candidates=[];before=roadmap.probes
    for raw in routes[:2]:
        if not isinstance(raw,list):continue
        ids=[i for i in raw[:16] if isinstance(i,str) and i in roadmap.points]
        if not ids or ids[0]!='S':ids.insert(0,'S')
        if ids[-1]!='G':ids.append('G')
        ids=[x for i,x in enumerate(ids) if not i or x!=ids[i-1]]
        valid=True;novel=0
        for a,b in zip(ids,ids[1:]):
            novel+=tuple(sorted((a,b))) not in roadmap.status
            valid=roadmap.verify(a,b) and valid
        cost=sum(octile(roadmap.points[a],roadmap.points[b]) for a,b in zip(ids,ids[1:]))
        candidates.append({'ids':ids,'points':[roadmap.points[i] for i in ids],
            'valid':valid,'cost':cost if valid else None,'proposed_unknown_edges':novel})
    return candidates,roadmap.probes-before
