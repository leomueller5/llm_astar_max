"""Geometry-supported route decisions; no optimal reference information.

The portfolio is an effort-bounded route-repair tree, not a grid shortest-path
solution. Every link claim is verified by the same lattice geometry as search.
"""
import heapq
import json
import math
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'session5'))
from prompts import endpoints, SYSTEM, messages as old_messages
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.search import octile
from llmastar.research.strategic.cuts import CutPotential


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


def portfolio(query, graph=None, budget=12, include_cuts=True):
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
            potential = CutPotential(query,goal)
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


def messages(query, variant, proposal=None):
    if variant == 'original':
        return old_messages(query,'original')[0]
    if variant == 'endpoints':
        return old_messages(query,'endpoints_v1')[0]
    payload = {'map':query,'candidate_points':proposal['points']}
    if variant in ['repair','rank']:
        payload['geometry_proposals'] = proposal['candidates'][:6]
    elif variant != 'policy':
        raise ValueError('Unknown hybrid prompt')
    if variant == 'repair':
        instruction = ('Improve the geometric route proposals. All supplied conflicts are factual '
            'failed shortest interpolations, NOT unreachable targets. Use the full wall map to '
            'select a coherent short route. Keep useful proposal points, skip redundancies, and '
            'insert free endpoint IDs to repair missing bypasses. You may instead choose one '
            'proposal unchanged. Return JSON {"route_id":"R0", "targets":["v0:T",...],'
            '"confidence":0.8}. If targets is present it REPLACES the whole intermediate '
            'sequence; omit targets to use route_id unchanged. At most 12 targets. No prose.\n')
    elif variant == 'rank':
        instruction = ('Select exactly ONE geometric route proposal to guide A*. '
            'Prefer short globally sensible routes; assess walls beyond each local bypass. '
            'Proposals may contain unverified or blocked links that A* must resolve. '
            'Return JSON {"route_id":"R0", "confidence":0.8}. No prose.\n')
    else:
        instruction = ('Choose a high-level search policy. Is endpoint guidance likely to help '
            'this start-goal query beyond direct goal search? If so provide at most 6 ordered '
            'endpoint IDs that avoid relevant walls. Otherwise abstain. '
            'Return JSON {"policy":"guide" or "goal", "targets":[], "confidence":0.8}. '
            'No prose.\n')
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction + json.dumps(payload,separators=(',',':'))}]


def decode(raw, query, variant, proposal):
    if variant == 'original':
        from llmastar.utils import list_parse
        return list_parse(raw), {'parsed':True}
    try:
        obj = json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
        if not isinstance(obj,dict):
            raise ValueError()
    except (ValueError,TypeError):
        return [], {'parsed':False,'unknown_ids':[],'confidence':0.}
    rows = {r['id']:r for r in proposal['candidates']}
    unknown = []
    if variant == 'rank' or ('targets' not in obj and obj.get('route_id') in rows):
        points = rows.get(obj.get('route_id'),{}).get('route',[])
    else:
        targets = obj.get('targets',[])
        if not isinstance(targets,list):
            targets = []
        points = []
        for identifier in targets[:12]:
            if isinstance(identifier,str) and identifier in proposal['points']:
                points.append(proposal['points'][identifier])
            else:
                unknown.append(str(identifier)[:48])
    if obj.get('policy') == 'goal':
        points = []
    confidence = obj.get('confidence',.5)
    confidence = min(1.,max(0.,float(confidence))) if type(confidence) in [int,float] and math.isfinite(confidence) else 0.
    return points, {'parsed':True,'unknown_ids':unknown,'confidence':confidence,
                    'route_id':obj.get('route_id'),'policy':obj.get('policy')}
