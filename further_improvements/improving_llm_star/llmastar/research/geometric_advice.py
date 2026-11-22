"""Geometry-only route proposals used by HybridWaypointPlanner.

Preserves the research prototype's deterministic candidate order and costs.
No reference solution or model output is used by the candidate generator.
"""
import heapq,json,math
from time import perf_counter
from .geometry import SegmentGridGraph
from .search import octile
from .strategic.cuts import CutPotential


def endpoints(query):
    graph=SegmentGridGraph(query);items={}
    for kind,key in [('h','horizontal_barriers'),('v','vertical_barriers')]:
        for i,(fixed,lo,hi) in enumerate(query[key]):
            if lo==hi:continue
            candidates=[('L',(lo-1,fixed)),('R',(hi+1,fixed))] if kind=='h' else [('B',(fixed,lo-1)),('T',(fixed,hi+1))]
            for side,p in candidates:
                if graph.valid_point(p):items[f'{kind}{i}:{side}']=p
    return items


def clean(query, points, graph):
    start, goal = tuple(query['start']), tuple(query['goal'])
    out = [start]
    for raw in points:
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            continue
        p = tuple(raw)
        if p not in [start, goal] and graph.valid_point(p) and p != out[-1]:
            out.append(p)
    out.append(goal)
    return out


def first_conflict(query, a, b, graph):
    """Report a factual failed diagonal-first interpolation, not unreachability."""
    p = a
    while p != b:
        n = (p[0] + (b[0] > p[0]) - (b[0] < p[0]),
             p[1] + (b[1] > p[1]) - (b[1] < p[1]))
        if not math.isfinite(graph.cost(p, n)):
            hits = []
            for kind, key in [('h','horizontal_barriers'),('v','vertical_barriers')]:
                for i, (fixed, lo, hi) in enumerate(query[key]):
                    if lo == hi:
                        continue
                    if any((x[1] == fixed and lo <= x[0] <= hi) if kind == 'h'
                           else (x[0] == fixed and lo <= x[1] <= hi) for x in [p, n]):
                        hits.append(kind + str(i))
            return {'from':a, 'to':b, 'failed_edge':[p,n], 'obstacles':hits}
        p = n
    return {'from':a, 'to':b, 'obstacles':[]}


def assess(query, route, graph):
    conflicts = []
    prefix = 0
    for i, (a,b) in enumerate(zip(route,route[1:])):
        if graph.lattice_segment(a,b) is None:
            conflicts.append(dict(first_conflict(query,a,b,graph), leg=i))
        elif not conflicts:
            prefix += 1
    return {'route':route, 'failed_links':len(conflicts), 'conflicts':conflicts,
            'verified_prefix_links':prefix,
            'octile_chain_cost':sum(octile(a,b) for a,b in zip(route,route[1:]))}


def portfolio(query, graph=None, budget=12, include_cuts=True, anchor=None):
    tick = perf_counter()
    graph = graph or SegmentGridGraph(query)
    lookup = endpoints(query)
    start, goal = tuple(query['start']), tuple(query['goal'])
    queue = []
    seen = set()
    rows = []
    pushes = pops = 0
    sequence = 0

    def offer(points, source):
        nonlocal pushes,sequence
        route = clean(query,points,graph)
        key = tuple(route)
        if key in seen or len(route) > 12:
            return
        seen.add(key)
        row = assess(query,route,graph)
        row['source'] = source
        # Fewer contradictions is only an empirical priority, never a bound.
        score = row['octile_chain_cost'] + row['failed_links'] * octile(start,goal)
        heapq.heappush(queue,(score,sequence,row))
        sequence += 1
        pushes += 1

    offer([], 'direct')
    if include_cuts:
        try:
            potential = anchor if anchor is not None else CutPotential(query,goal)
            for axis in [potential.x,potential.y]:
                route = axis.gate_route(start)
                if route:
                    offer(route,'cut_' + axis.axis)
        except ValueError:
            pass
    for _ in range(budget):
        if not queue:
            break
        _,_,row = heapq.heappop(queue)
        pops += 1
        row['id'] = 'R' + str(len(rows))
        rows.append(row)
        if not row['conflicts']:
            continue
        conflict = row['conflicts'][0]
        leg = conflict['leg']
        for obstacle in conflict['obstacles'][:2]:
            for identifier,p in lookup.items():
                if identifier.split(':')[0] != obstacle or p in row['route']:
                    continue
                offer(row['route'][:leg+1] + [p] + row['route'][leg+1:],
                      row['id'] + '+' + identifier)
    rows.sort(key=lambda r:(r['failed_links'],r['octile_chain_cost'],r['id']))
    best = rows[0]['route'] if rows else [start,goal]
    return {'candidates':rows, 'points':lookup, 'geometry_best':best,
            'seconds':perf_counter()-tick,'heap_pushes':pushes,'heap_pops':pops,
            'segment_checks':graph.segment_checks, 'budget':budget}
