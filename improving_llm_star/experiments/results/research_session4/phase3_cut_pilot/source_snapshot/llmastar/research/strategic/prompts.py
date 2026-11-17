"""Strategic planning prompts only; intentionally no API/client integration."""
import json

SYSTEM_PROMPT='''You advise a grid path planner. Decide route strategy, not individual moves.
Coordinates use x right and y UP. Barriers include their endpoints and may not be
crossed. For a horizontal barrier hN, bypass LEFT (x<lo) or RIGHT (x>hi). For a
vertical barrier vN, bypass BELOW (y<lo) or ABOVE (y>hi). Going "above a horizontal
barrier" does not explain how to get across it. Use only obstacle/region ids supplied.
Propose at most 3 distinct alternatives. Do not output a dense low-level path.
Confidence is an optional estimate, not a proof. Never claim an unchecked route
valid or optimal. Abstain if context is insufficient. Respond ONLY with JSON:
{"version":1,"strategies":[{"id":"option_a","confidence":0.7,
"bypasses":[{"obstacle_id":"h0","side":"right"}],"regions":[],"waypoints":[]}],"abstain":false}.
Each strategy needs at least bypasses, ordered supplied regions, or sparse targets.
The search validates all advice and may reject it. No explanations or hidden reasoning.'''


def build_prompt(query,context=None,event='initial',obstacle_budget=256):
    if obstacle_budget<1:raise ValueError('Positive obstacle budget required')
    walls=[]
    for prefix,key in [('h','horizontal_barriers'),('v','vertical_barriers')]:
        for i,wall in enumerate(query[key]):walls.append({'id':f'{prefix}{i}','geometry':wall})
    payload={'coordinate_frame':'x-right,y-up; integer grid; closed wall endpoints',
      'start':query['start'],'goal':query['goal'],'range_x':query['range_x'],'range_y':query['range_y'],
      'event':event,'obstacles':walls[:obstacle_budget],
      'obstacles_omitted':max(0,len(walls)-obstacle_budget),'strategic_context':context or {}}
    return {'system':SYSTEM_PROMPT,'user':json.dumps(payload,separators=(',',':')),
      'warning':'Context is incomplete if obstacles_omitted>0; no assumption of absent walls is valid.'}
