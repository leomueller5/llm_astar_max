"""Interactive Verified Frontier Selection (IVFS), bounded abstract planning.

The LLM selects only states with physically verified prefixes. Each selected
state reveals its actual geometric visibility. A classical controller has the
identical information and effort budget. Complete cut A* handles every failure.
"""
import argparse
import gzip
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from api import RetryClient,RequestUnavailable
from hybrid import ROOT,portfolio,SYSTEM
from strategic import schema
from llmastar.research.geometry import SegmentGridGraph,expand_lattice_route
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.strategic.cut_search import CutStrategySearch
from llmastar.research.strategic.providers import StaticProvider
from llmastar.research.search import octile


@dataclass(frozen=True,slots=True)
class Prefix:
    identifier:str
    g:float
    parent:object=None


def context_hash(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True).encode()).hexdigest()


def frontier_messages(context):
    instruction=('Select ONE reachable frontier state to expand next. Every '
        'frontier entry has a collision-checked route from the original start '
        'with the stated actual cost. The remaining cost is an admissible '
        'geometric LOWER bound, not a solved route. Expanding a state will check '
        'which other geometric targets are reachable from it. Use the map and '
        'previous visibility feedback to avoid connected walls and dead ends. '
        'Choose the state most likely to complete a SHORT route to the goal '
        'within the remaining strategic expansion budget. Do not invent states '
        'or coordinates.\n')
    fmt=schema('frontier_choice',{'choice':{'type':'string',
        'enum':[r['id'] for r in context['frontier']]}})
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':instruction+json.dumps(context,separators=(',',':'))}],fmt


def plan(query,proposal,graph,potential,controller,budget=4,frontier_limit=48):
    points=dict(proposal['points']);points['S']=tuple(query['start']);points['G']=tuple(query['goal'])
    best={'S':Prefix('S',0.)};closed={};edges={};status={};events=[];probes=0
    current=best['S'];selections=expanded=0;goal=tuple(query['goal'])

    def chain(label):
        ids=[]
        while label is not None:ids.append(label.identifier);label=label.parent
        return [points[i] for i in reversed(ids)]

    def expand(label):
        nonlocal probes,expanded
        a=label.identifier;closed[a]=label.g;expanded+=1
        visible=[];blocked=[]
        for b,p in points.items():
            if b==a or p==points[a]:continue
            key=tuple(sorted((a,b)))
            if key not in status:
                probes+=1;piece=graph.lattice_segment(points[a],p);status[key]=bool(piece)
                if piece:edges[a,b]=tuple(piece)
            if not status[key]:blocked.append(b);continue
            visible.append(b);new=label.g+octile(points[a],p)
            if new<getattr(best.get(b),'g',math.inf)-1e-12:best[b]=Prefix(b,new,label)
        return visible,blocked

    for step in range(budget+1):
        visible,blocked=expand(current)
        incumbent=best.get('G')
        if incumbent and incumbent.g<=1.05*potential.value(tuple(query['start']))+1e-9:break
        available=[label for key,label in best.items() if key!='G' and label.g<closed.get(key,math.inf)-1e-12]
        available.sort(key=lambda label:(label.g+2*potential.value(points[label.identifier]),label.identifier))
        if not available or step>=budget:break
        menu=[{'id':label.identifier,'point':points[label.identifier],'verified_prefix_cost':label.g,
               'remaining_cost_lower_bound':potential.value(points[label.identifier])} for label in available[:frontier_limit]]
        context={'map':query,'event':'verified_frontier_expansion','step':step,
            'remaining_expansions':budget-step,'last_expanded':current.identifier,
            'last_visible_targets':visible,'last_blocked_links':blocked,
            'current_valid_upper_bound':incumbent.g if incumbent else None,
            'start_lower_bound':potential.value(tuple(query['start'])),'frontier':menu}
        choice=controller(context);selections+=1
        events.append({'context':context,'choice':choice,'context_hash':context_hash(context)})
        current=next((label for label in available[:frontier_limit] if label.identifier==choice),None)
        if current is None:break
    incumbent=best.get('G')
    if incumbent:route=chain(incumbent);complete=True;cost=incumbent.g
    else:
        target=min(best.values(),key=lambda label:(potential.value(points[label.identifier]),label.g,label.identifier))
        route=chain(target);complete=False;cost=None
    return {'route':route,'complete':complete,'cost':cost,'abstract_expanded':expanded,
            'abstract_selections':selections,'abstract_unique':len(closed),'visibility_probes':probes,
            'events':events,'known_states':len(best)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--online',action='store_true')
    p.add_argument('--cache',type=Path);p.add_argument('--budget',type=int,default=4);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases=json.load(gzip.open(a.cases,'rt'));client=RetryClient() if a.online else None
    cache={}
    if a.cache:
        archive=json.load(gzip.open(a.cache,'rt'))
        cache={(r['case_id'],r['context_hash']):r for r in archive['requests']}
    rows=[];requests=[]
    for case in cases:
        q=case['query']
        for method in ['llm','classic','random']:
            began=perf_counter();graph=SegmentGridGraph(q);proposal=portfolio(q,graph)
            potential=CutPotential(q,tuple(q['goal']));lower=potential.value(tuple(q['start']))
            gate=proposal['candidates'][0]['failed_links']==0
            api_seconds=0.;actual_calls=0;metadata=[]
            def choose(context):
                nonlocal api_seconds,actual_calls
                if method=='classic':return context['frontier'][0]['id']
                if method=='random':return random.Random('s6frontier'+case['id']+str(context['step'])).choice(context['frontier'])['id']
                h=context_hash(context);cached=cache.get((case['id'],h))
                if cached:
                    requests.append(cached);return cached['choice']
                if not a.online:raise RuntimeError('Missing exact frontier-context cache; no implicit API request')
                msgs,fmt=frontier_messages(context);tick=perf_counter()
                try:
                    answer,rid,hit=client.chat(msgs,{'phase':'frontier_'+case['split'],
                        'prompt_version':'s6_frontier_v1','case_id':case['id'],
                        'context_hash':h},max_tokens=64,response_format=fmt)
                    choice=json.loads(answer['choices'][0]['message'].get('content') or '{}').get('choice')
                    latency=perf_counter()-tick;api_seconds+=latency;actual_calls+=not hit
                    request={'case_id':case['id'],'context_hash':h,'context':context,
                        'choice':choice,'response':answer,'request_id':rid,'cached':hit,
                        'collection_seconds':latency};requests.append(request)
                    return choice
                except (RequestUnavailable,ValueError):
                    api_seconds+=perf_counter()-tick;return None
            if gate:
                guidance={'route':proposal['geometry_best'],'complete':True,
                    'cost':proposal['candidates'][0]['octile_chain_cost'],'abstract_expanded':0,
                    'abstract_selections':0,'abstract_unique':0,'visibility_probes':0,'events':[],'known_states':0}
            else:guidance=plan(q,proposal,graph,potential,choose,a.budget)
            prefix=[tuple(x) for x in guidance['route']]
            provider=StaticProvider({'strategies':[{'id':'verified_frontier_route','waypoints':prefix}]},'frontier') if prefix else None
            if guidance['complete'] and guidance['cost']<=1.05*lower+1e-9:
                r={'valid':True,'length':guidance['cost'],'unique':0,'operation':0,'expanded':0,'path':[]}
                path=[tuple(q['start'])]
                for x,y in zip(prefix,prefix[1:]):path.extend(expand_lattice_route(graph.lattice_segment(x,y))[1:])
                r['path']=path
            else:r=CutStrategySearch(bound=1.05).search(q,provider,graph)
            elapsed=perf_counter()-began;path=r.pop('path',[])
            if r['valid']:
                assert r['length']<=1.05*case['optimal_cost']+1e-7
                assert abs(r['length']-sum(math.dist(x,y) for x,y in zip(path,path[1:])))<1e-7
                assert all(math.isfinite(graph.cost(x,y)) for x,y in zip(path,path[1:]))
            r.pop('events',None)
            rows.append(dict(r,case_id=case['id'],map_id=case['map_id'],family=case['family'],
                method=method,geometry_gate=gate,guidance=guidance,actual_api_calls=actual_calls,
                api_seconds=api_seconds,full_seconds=elapsed,offline_compute_seconds=elapsed-api_seconds,
                cost_ratio=r['length']/case['optimal_cost'] if r['valid'] else None))
            tmp=a.output/'checkpoint.tmp'
            with gzip.open(tmp,'wt') as f:json.dump({'runs':rows,'requests':requests},f)
            tmp.replace(a.output/'checkpoint.json.gz')
        print(case['id'],'completed',flush=True)
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'runs':rows,'requests':requests},f)
    print('Verified-frontier requests:',len(requests))


if __name__=='__main__':main()
