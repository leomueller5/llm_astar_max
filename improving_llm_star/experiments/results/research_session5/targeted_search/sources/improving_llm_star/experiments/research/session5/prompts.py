"""Frozen text/endpoint/ASCII representations from map data, never a solved path."""
import sys,json,runpy,math
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[3];WORKSPACE=ROOT.parent;sys.path.insert(0,str(ROOT))
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.strategic.schema import parse_guidance
ORIGINAL=runpy.run_path(str(WORKSPACE/'llm-astar/llmastar/pather/llm_a_star/prompt.py'))['standard_gpt']
MODEL='gpt-4o-mini-2024-07-18'
SYSTEM='You advise an eight-neighbor grid A* planner. x increases right; y increases UP. Walls are CLOSED segments including endpoints. Only integer cells strictly inside the supplied boundary are allowed. Return compact route guidance, not a dense sequence of unit moves. Do not provide explanations.'


def endpoints(query):
    graph=SegmentGridGraph(query);items={}
    for kind,key in [('h','horizontal_barriers'),('v','vertical_barriers')]:
        for i,(fixed,lo,hi) in enumerate(query[key]):
            if lo==hi:continue
            candidates=[('L',(lo-1,fixed)),('R',(hi+1,fixed))] if kind=='h' else [('B',(fixed,lo-1)),('T',(fixed,hi+1))]
            for side,p in candidates:
                if graph.valid_point(p):items[f'{kind}{i}:{side}']=p
    return items


def messages(query,version='original',feedback=None,previous=None):
    began=perf_counter();lookup=endpoints(query) if version in ['endpoints_v1','ascii_v1'] else {};q={k:query[k] for k in ['start','goal','range_x','range_y','horizontal_barriers','vertical_barriers']}
    if version=='original':result=[{'role':'user','content':ORIGINAL.format(start=query['start'],goal=query['goal'],horizontal_barriers=query['horizontal_barriers'],vertical_barriers=query['vertical_barriers'])}]
    elif version=='coords_v1':
        instruction='Choose a SHORT ordered sequence of at most 12 necessary intermediate integer targets around relevant obstacles. Do not put targets on walls. Sparse strategic turns are sufficient; A* handles local movement. Check proposed crossings against all wall intervals; a wall endpoint itself is blocked. Include start and goal. Respond only: Generated Path: [[x,y],...].\n'
        result=[{'role':'system','content':SYSTEM},{'role':'user','content':instruction+json.dumps(q,separators=(',',':'))}]
    elif version in ['endpoints_v1','ascii_v1']:
        instruction='Choose ordered FREE wall-endpoint target IDs to pass relevant barriers. L/R bypass a horizontal wall left/right; B/T bypass a vertical wall below/above. Coordinates have already been computed; use only supplied IDs. Choose at most 12 IDs, omit irrelevant endpoints. You may omit IDs for a direct route. Check the overall order and every crossing. Return ONLY JSON {"targets":["h0:R","v1:T"]}. No numerical coordinates, no explanation.\n'
        payload={'map':q,'free_endpoint_targets':lookup}
        if version=='ascii_v1':
            g=SegmentGridGraph(query);lines=[]
            for y in range(g.y1-1,g.y0,-1):
                row=''.join('S' if (x,y)==tuple(q['start']) else 'G' if (x,y)==tuple(q['goal']) else '#' if g.blocked((x,y)) else '.' for x in range(g.x0+1,g.x1))
                lines.append(f'{y:3d} '+row)
            payload['ascii_legend']='Rows labelled actual y, descending. First column is x='+str(g.x0+1)+'. # closed wall, . free, S start, G goal.';payload['ascii']='\n'.join(lines)
        result=[{'role':'system','content':SYSTEM},{'role':'user','content':instruction+json.dumps(payload,separators=(',',':'))}]
    else:raise ValueError('Unknown prompt version')
    if previous is not None:
        result.extend([{'role':'assistant','content':previous},{'role':'user','content':('Revise the route using this exact geometric/search feedback. A failed interpolation or exhausted local probe is NOT proof the waypoint is unreachable. '+json.dumps(feedback,separators=(',',':'))) if feedback else 'Review the proposed route against the supplied walls and revise any invalid crossings. Return the same compact output format only.'}])
    return result,lookup,perf_counter()-began


def decode(response,query,version):
    raw=response if isinstance(response,str) else response['choices'][0]['message'].get('content') or ''
    if version in ['endpoints_v1','ascii_v1']:
        try:
            value=json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip());ids=value.get('targets',[])
            if not isinstance(ids,list):ids=[]
        except (ValueError,TypeError,AttributeError):ids=[]
        lookup=endpoints(query);points=[tuple(query['start'])];unknown=[]
        for target in ids[:24]:
            if isinstance(target,str) and target in lookup:points.append(lookup[target])
            else:unknown.append(str(target)[:64])
        points.append(tuple(query['goal']));return points,{'unknown_ids':unknown,'provided_ids':ids[:24],'parse_valid':bool(isinstance(value,dict)) if 'value' in locals() else False}
    guidance=parse_guidance(raw);points=list(guidance.strategies[0].waypoints) if guidance.strategies else []
    return points,{'warnings':list(guidance.warnings),'parse_valid':not guidance.abstain}


def feedback_for(query,points):
    graph=SegmentGridGraph(query);start,goal=tuple(query['start']),tuple(query['goal']);invalid=[p for p in points if not graph.valid_point(p)]
    if invalid:return {'type':'invalid_target','targets':invalid[:3],'fact':'These coordinates are outside the allowed grid or on closed walls.'}
    route=[start]+[tuple(p) for p in points if tuple(p) not in [start,goal]]+[goal]
    for a,b in zip(route,route[1:]):
        if graph.lattice_segment(a,b):continue
        p=a
        for _ in range(int(max(abs(b[0]-a[0]),abs(b[1]-a[1])))):
            n=(p[0]+(b[0]>p[0])-(b[0]<p[0]),p[1]+(b[1]>p[1])-(b[1]<p[1]))
            if not math.isfinite(graph.cost(p,n)):
                walls=[]
                for kind,key in [('h','horizontal_barriers'),('v','vertical_barriers')]:
                    for i,(fixed,lo,hi) in enumerate(query[key]):
                        if any((x[1]==fixed and lo<=x[0]<=hi) if kind=='h' else (x[0]==fixed and lo<=x[1]<=hi) for x in [p,n]):walls.append(kind+str(i))
                return {'type':'blocked_interpolation','from':a,'to':b,'first_invalid_edge':[p,n],'wall_ids':walls,'fact':'This specific diagonal-first shortest interpolation crosses a wall. This does not prove the target unreachable.'}
            p=n
    return None
