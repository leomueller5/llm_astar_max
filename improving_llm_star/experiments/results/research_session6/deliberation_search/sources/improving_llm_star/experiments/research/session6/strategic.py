"""Constrained strategic decisions based on factual geometric contradictions."""
import json
import math
from hybrid import SYSTEM,clean,assess,first_conflict
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.search import octile


def schema(name,properties):
    return {'type':'json_schema','json_schema':{'name':name,'strict':True,
        'schema':{'type':'object','additionalProperties':False,
                  'properties':properties,'required':list(properties)}}}


def strict_messages(query,proposal,version):
    lookup=proposal['points'];ids=list(lookup)
    candidates=proposal['candidates'][:6]
    payload={'map':query,'free_targets':lookup,'proposals':candidates}
    if version=='rank_strict':
        instruction=('Select the shortest FULLY VERIFIED route if one exists. '
            'failed_links=0 means all physical links pass collision checks; a '
            'blocked route is not equivalent to a complete route. If all routes '
            'fail, choose the most plausible useful partial plan for A*. '
            'The choice must be an actual proposal ID, not the example ID.\n')
        fmt=schema('route_choice',{'route_id':{'type':'string','enum':[r['id'] for r in candidates]}})
    elif version=='repair_strict':
        instruction=('The geometric module has not completed a route. Repair the '
            'best proposal by passing relevant closed-wall endpoints. Use only '
            'free target IDs and check route order against ALL walls. Return '
            'only necessary targets; avoid guessing coordinates. A* resolves '
            'remaining local movement. An empty sequence means abstain.\n')
        fmt=schema('route_repair',{'targets':{'type':'array','items':{'type':'string','enum':ids},'maxItems':12}})
    elif version in ['multi_strict','deliberate_strict']:
        instruction=('Produce up to THREE genuinely different short bypass '
            'strategies from start to goal using the supplied free endpoint IDs. '
            'Geometry proposals are hints, not mandatory targets. Try opposite '
            'sides of ambiguous obstacles; each sequence should describe a '
            'coherent full route. Do not repeat near-identical candidates.\n')
        properties={}
        if version=='deliberate_strict':
            instruction=('First identify up to FOUR relevant obstacle-bypass '
                'decisions. Reason briefly about connected walls and downstream '
                'dead ends BEFORE constructing the routes. Use the supplied '
                'collision feedback to avoid repeating invalid segments. '+instruction)
            properties['decisions']={'type':'array','maxItems':4,'items':{
                'type':'object','additionalProperties':False,'properties':{
                    'obstacle':{'type':'string'},'side':{'type':'string','enum':['above','below','left','right']},
                    'reason':{'type':'string'}},'required':['obstacle','side','reason']}}
        properties['routes']={'type':'array','maxItems':3,
            'items':{'type':'array','items':{'type':'string','enum':ids},'maxItems':10}}
        fmt=schema('route_portfolio',properties)
    else:
        raise ValueError(version)
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction+json.dumps(payload,separators=(',',':'))}],fmt


def fork_context(query,proposal,graph=None):
    graph=graph or SegmentGridGraph(query)
    best=proposal['candidates'][0]
    if best['failed_links']==0:
        return None
    conflict=best['conflicts'][0]
    a,b=tuple(conflict['from']),tuple(conflict['to'])
    obstacle=next(iter(conflict['obstacles']),None)
    choices=[]
    for identifier,p in proposal['points'].items():
        if identifier.split(':')[0]!=obstacle:
            continue
        route=clean(query,best['route'][:conflict['leg']+1]+[p]+best['route'][conflict['leg']+1:],graph)
        details=assess(query,route,graph)
        choices.append({'id':identifier,'point':p,'route':route,
            'link_from_current_verified':graph.lattice_segment(a,p) is not None,
            'link_to_next_verified':graph.lattice_segment(p,b) is not None,
            'octile_detour':octile(a,p)+octile(p,b)-octile(a,b),
            'remaining_conflicts':details['conflicts'],'failed_links':details['failed_links']})
    if not choices:
        return None
    return {'map':query,'failed_route':best['route'],'first_conflict':conflict,
            'bypass_options':choices,
            'geometry_choice':min(choices,key=lambda c:(c['failed_links'],c['octile_detour'],c['id']))['id']}


def fork_messages(context):
    options=[c['id'] for c in context['bypass_options']]
    payload={k:v for k,v in context.items() if k!='geometry_choice'}
    instruction=('Choose ONE bypass option for the identified obstacle. Local '
        'verified links and exact remaining conflicts are supplied. Think about '
        'global downstream walls and dead ends, rather than only the shortest '
        'local detour. Do not introduce coordinates or unrelated wall IDs. '
        'Return the option ID that gives the most promising route to the goal.\n')
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction+json.dumps(payload,separators=(',',':'))}],schema('obstacle_bypass',{'choice':{'type':'string','enum':options}})


def decode_strict(raw,proposal,version,context=None):
    try:
        obj=json.loads(raw)
    except (TypeError,ValueError):
        return [],{'parsed':False}
    lookup=proposal['points'];rows={r['id']:r for r in proposal['candidates']}
    if version=='fork':
        choice=obj.get('choice')
        selected=next((c for c in context['bypass_options'] if c['id']==choice),None)
        return selected['route'] if selected else [],{'parsed':bool(selected),'choice':choice,
            'geometry_choice':context['geometry_choice'],'agrees_with_geometry':choice==context['geometry_choice']}
    if version=='rank_strict':
        choice=obj.get('route_id');selected=rows.get(choice)
        return selected['route'] if selected else [],{'parsed':bool(selected),'route_id':choice}
    routes=obj.get('routes',[]) if version in ['multi_strict','deliberate_strict'] else [obj.get('targets',[])]
    decoded=[];unknown=[]
    for route in routes[:3]:
        if not isinstance(route,list):
            continue
        decoded.append([lookup[i] for i in route[:12] if isinstance(i,str) and i in lookup])
        unknown.extend(str(i)[:48] for i in route if not isinstance(i,str) or i not in lookup)
    return decoded[0] if decoded else [],{'parsed':not unknown,'unknown_ids':unknown,'routes':decoded}
