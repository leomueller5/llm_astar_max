"""One evidence-triggered choice among reachable geometric alternatives.

The model cannot inject costs, collisions or node priorities. Its single target
choice only changes future optional macro-edge tests; OPEN needs no rekey.
"""
import argparse
import contextlib
import gzip
import importlib.util
import json
import math
import random
import sys
from pathlib import Path
from time import perf_counter

from api import RetryClient,RequestUnavailable
from hybrid import ROOT,portfolio,SYSTEM
from strategic import schema
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.macro_guidance import MacroGuidedSearch
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile


def alternatives(context,proposal,graph,potential,limit=8):
    node=tuple(context['current_node']);options=[]
    for identifier,p in proposal['points'].items():
        p=tuple(p)
        if p==node or graph.lattice_segment(node,p) is None:continue
        options.append({'id':identifier,'point':p,'verified_link_cost':octile(node,p),
                        'remaining_cost_lower_bound':potential.value(p),
                        'goal_link_verified':graph.lattice_segment(p,tuple(context['query']['goal'])) is not None})
    options.sort(key=lambda c:(c['verified_link_cost']+c['remaining_cost_lower_bound'],c['id']))
    return options[:limit]


def feedback_messages(context,options):
    payload={'map':context['query'],'search_state':{k:v for k,v in context.items() if k!='query'},
             'reachable_alternatives':options}
    instruction=('A* has repeatedly failed to connect to its previous LLM targets '
        'using shortest local paths. This does NOT prove the targets unreachable. '
        'Choose one new strategic bypass from the physically verified reachable '
        'alternatives. Consider downstream obstacles rather than only local '
        'distance. You may abstain if no choice is useful. A* retains a complete '
        'classical fallback and checks every move.\n')
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction+json.dumps(payload,separators=(',',':'))}],schema(
        'search_correction',{'choice':{'type':'string','enum':[c['id'] for c in options]+['abstain']}})


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--online',action='store_true');a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    inputs=json.load(gzip.open(a.responses,'rt'))['runs'];client=RetryClient() if a.online else None
    rows=[];requests=[]
    for response in inputs:
        case=cases[response['case_id']];q=case['query'];cached_request=None
        # First collect the real online event, then replay all controls at exactly
        # the same deterministic trigger; never regenerate the initial advice.
        methods=['llm','none','classic','clear','random'] if a.online else ['none','classic','clear','random']
        for method in methods:
            graph=SegmentGridGraph(q);proposal=portfolio(q,graph)
            potential=CutPotential(q,tuple(q['goal']));event=[]
            def correction(context):
                nonlocal cached_request
                tick=perf_counter();options=alternatives(context,proposal,graph,potential)
                if not options:
                    event.append({'context':context,'options':[],'choice':None,'seconds':perf_counter()-tick});return None
                choice=None
                if method=='classic':choice=options[0]['id']
                elif method=='random':choice=random.Random('s6_dynamic_'+case['id']).choice(options)['id']
                elif method=='llm':
                    messages,fmt=feedback_messages(context,options)
                    try:
                        answer,rid,hit=client.chat(messages,{'phase':'macro_dynamic_'+case['split'],
                            'prompt_version':'s6_macro_correction_v1','case_id':case['id']},max_tokens=96,response_format=fmt)
                        choice=json.loads(answer['choices'][0]['message'].get('content') or '{}').get('choice')
                        cached_request={'case_id':case['id'],'request_id':rid,'response':answer,
                            'context':context,'options':options,'choice':choice,'cached':hit}
                        requests.append(cached_request)
                    except (RequestUnavailable,ValueError):choice=None
                event.append({'context':context,'options':options,'choice':choice,'seconds':perf_counter()-tick})
                if method=='clear' or choice=='abstain':return []
                selected=next((c for c in options if c['id']==choice),None)
                return [selected['point']] if selected else None
            began=perf_counter()
            result=MacroGuidedSearch(heuristic='cut').search(q,response['points'],graph,
                revision=correction if method!='none' else None,record_trace=False)
            elapsed=perf_counter()-began;path=result.pop('path',[])
            if result['valid']:
                assert result['length']<=2*case['optimal_cost']+1e-7
                assert all(math.isfinite(graph.cost(a,b)) for a,b in zip(path,path[1:]))
            result.pop('trace',None)
            rows.append(dict(result,case_id=case['id'],map_id=case['map_id'],method=method,
                cost_ratio=result['length']/case['optimal_cost'] if result['valid'] else None,
                seconds=elapsed,geometry_seconds=proposal['seconds'],intervention=event,
                initial_geometry_gate=response['meta'].get('api_skipped',False)))
            with gzip.open(a.output/'checkpoint.json.gz','wt') as f:
                json.dump({'runs':rows,'requests':requests},f)
        print(case['id'],'completed',flush=True)
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'runs':rows,'requests':requests},f)
    print('Online corrections:',len(requests),'cached initial advice reused')


if __name__=='__main__':main()
