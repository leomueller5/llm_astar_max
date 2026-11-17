"""Labelled synthetic strategy controls; oracle extraction never enters planner."""
import random,math
from llmastar.research.strategic.schema import Strategy,Bypass,StrategicGuidance


def oracle_bypasses(query,path):
    """Encode actual free-end visits, in path order, using obstacle IDs only.

    This is unavailable oracle information. It is intentionally not inferred by
    a deployable planner. The compiler recovers integer endpoint offsets.
    """
    visits=[];seen=set()
    for position,point in enumerate(path):
        x,y=point
        for kind,key in [('v','vertical_barriers'),('h','horizontal_barriers')]:
            for i,(fixed,lo,hi) in enumerate(query[key]):
                if lo==hi:continue
                side=None
                if kind=='v' and x==fixed:
                    if y==lo-1:side='below'
                    elif y==hi+1:side='above'
                elif kind=='h' and y==fixed:
                    if x==lo-1:side='left'
                    elif x==hi+1:side='right'
                label=(kind,i,side)
                if side and (not visits or visits[-1][1:]!=label):visits.append((position,kind,i,side))
    return [dict(obstacle_id=f'{k}{i}',side=side) for _,k,i,side in visits]


def corrupt_bypasses(bypasses,seed,flip=.15,drop=.15):
    rng=random.Random(seed);opposite={'above':'below','below':'above','left':'right','right':'left'};result=[]
    for b in bypasses:
        if rng.random()<drop:continue
        side=opposite[b['side']] if rng.random()<flip else b['side']
        result.append(dict(b,side=side))
    return result


def source_response(case,source,seed=202611174):
    q=case['query'];local=random.Random(seed+sum(map(ord,case['id'])))
    if source=='oracle_gates':return {'strategies':[{'id':source,'bypasses':oracle_bypasses(q,case['oracle_path'])}]}
    if source=='imperfect_gates':return {'strategies':[{'id':source,'bypasses':corrupt_bypasses(oracle_bypasses(q,case['oracle_path']),seed+sum(map(ord,case['id'])))}]}
    if source=='portfolio':
        candidates=[]
        for i in range(3):
            points=[q['start']]+[(x+local.choice([-1,0,1]),y+local.choice([-1,0,1])) for x,y in case['oracle_waypoints'][1:-1]]+[q['goal']]
            candidates.append({'id':f'imperfect_alternative{i}','waypoints':points})
        return {'strategies':candidates}
    raise ValueError(source)
