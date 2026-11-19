import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SESSION=ROOT/'experiments/research/session6'
sys.path.insert(0,str(SESSION))
from hybrid import portfolio,decode,messages,assess
from api import CumulativeLedger,RetryClient,RequestUnavailable


def sample():
    return {'range_x':[0,30],'range_y':[0,24],'start':[3,8],'goal':[25,8],
            'horizontal_barriers':[],'vertical_barriers':[[13,3,15]]}


def test_portfolio_solves_simple_wall_without_optimal_reference():
    from llmastar.research.geometry import SegmentGridGraph
    q=sample();g=SegmentGridGraph(q);p=portfolio(q,g,budget=10)
    valid=[r for r in p['candidates'] if r['failed_links']==0]
    assert valid and p['heap_pops']<=10
    for r in valid:
        assert r['route'][0]==tuple(q['start']) and r['route'][-1]==tuple(q['goal'])
        assert all(g.lattice_segment(a,b) for a,b in zip(r['route'],r['route'][1:]))
    prompt=json.dumps(messages(q,'repair',p))
    assert 'optimal_cost' not in prompt and 'optimal_path' not in prompt


def test_hybrid_decoder_rejects_unknown_ids_and_bad_confidence():
    q=sample();p=portfolio(q)
    r,meta=decode('{"targets":["unknown",null],"confidence":"NaN"}',q,'repair',p)
    assert not r and len(meta['unknown_ids'])==2 and meta['confidence']==0
    r,meta=decode('[]',q,'repair',p)
    assert not r and not meta['parsed']
    r,meta=decode('{"policy":"goal","targets":["v0:T"]}',q,'policy',p)
    assert not r


def test_route_selection_preserves_exact_geometric_candidate():
    q=sample();p=portfolio(q)
    row=p['candidates'][0]
    r,meta=decode(json.dumps({'route_id':row['id'],'confidence':1.2}),q,'rank',p)
    assert r==row['route'] and meta['confidence']==1.


def test_retry_reserves_each_attempt_and_retains_failure_hold(tmp_path):
    ledger=CumulativeLedger(tmp_path/'ledger.sqlite3',tmp_path/'portable.json')
    calls=[]
    def transport(payload):
        calls.append(payload)
        if len(calls)==1:
            raise TimeoutError('private diagnostic must not persist')
        return {'model':'gpt-4o-mini-2024-07-18','usage':{'prompt_tokens':10,'completion_tokens':4},
                'choices':[{'message':{'content':'OK'}}]}
    client=RetryClient(ledger,transport,attempts=2,backoff=0)
    client.chat([{'role':'user','content':'x'}],{'case':'retry'},max_tokens=8)
    assert ledger.summary()['attempts']==2 and ledger.summary()['successes']==1
    assert ledger.summary()['held_worst_case_usd']>0
    client.chat([{'role':'user','content':'x'}],{'case':'retry'},max_tokens=8)
    assert len(calls)==2
    assert 'private diagnostic' not in (tmp_path/'portable.json').read_text()


def test_session6_portable_restore_includes_cumulative_exposure(tmp_path):
    archive=tmp_path/'portable.json';ledger=CumulativeLedger(tmp_path/'one.sqlite3',archive)
    def fail(payload):raise TimeoutError()
    with pytest.raises(RequestUnavailable):
        RetryClient(ledger,fail,attempts=1).chat([{'role':'user','content':'x'}],{})
    other=CumulativeLedger(tmp_path/'two.sqlite3',archive)
    assert other.summary()==ledger.summary()


def test_retry_limit_and_circuit_breaker(tmp_path):
    ledger=CumulativeLedger(tmp_path/'ledger.sqlite3',tmp_path/'portable.json');calls=[]
    def fail(payload):calls.append(1);raise TimeoutError()
    client=RetryClient(ledger,fail,attempts=2,backoff=0)
    for i in range(4):
        with pytest.raises(RequestUnavailable):
            client.chat([{'role':'user','content':'x'}],{'query':i})
    assert len(calls)==6 and ledger.summary()['attempts']==6


def test_macro_edges_are_real_grid_walks_and_weight_bound_holds():
    import random
    from llmastar.research.macro_guidance import MacroGuidedSearch
    from llmastar.research.geometry import SegmentGridGraph
    from llmastar.research.incumbent import IncumbentSearch
    rng=random.Random(886123)
    for i in range(12):
        q=sample()
        q['horizontal_barriers']=[[rng.randrange(2,20),rng.randrange(2,10),rng.randrange(13,27)] for _ in range(3)]
        ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[])
        points=[(rng.randrange(1,29),rng.randrange(1,23)) for _ in range(8)]
        for weight in [1.,1.1,2.]:
            r=MacroGuidedSearch(weight=weight,interval=2,initial_chain=True).search(q,points,record_trace=True)
            assert r['valid']==ref['valid']
            if r['valid']:
                g=SegmentGridGraph(q)
                assert r['length']<=weight*ref['length']+1e-7
                assert all(math.isfinite(g.cost(a,b)) for a,b in zip(r['path'],r['path'][1:]))
                assert abs(r['length']-sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:])))<1e-7
            assert r['macro_probes']<=256 and r['rebuilds']==0


def test_macro_unreachable_trivial_and_probe_disabled():
    from llmastar.research.macro_guidance import MacroGuidedSearch
    q=sample();blocked=dict(q,vertical_barriers=[[13,0,24]])
    r=MacroGuidedSearch().search(blocked,[(12,20)])
    assert not r['valid'] and r['path']==[]
    trivial=dict(q,goal=q['start'])
    r=MacroGuidedSearch(initial_chain=True).search(trivial,[])
    assert r['valid'] and r['length']==0 and r['path']==[tuple(q['start'])]
    r=MacroGuidedSearch(probe_budget=0).search(q,[(13,16)])
    assert r['valid'] and r['macro_probes']==0


def test_direct_original_macro_keeps_baseline_score_and_dense_output():
    import contextlib,io
    sys.path.insert(0,str(ROOT/'experiments'))
    import measure_waypoint_progress as replay
    from direct import macro_class
    from llmastar.research.geometry import SegmentGridGraph
    replay.BACKEND='installed'
    Original=replay.load_planner(ROOT.parent/'llm-astar',response='')
    q=sample();p=macro_class(Original)();p.set_macro(SegmentGridGraph(q),interval=1)
    p.model=replay.OfflineModel('Generated Path: [[3,8],[12,16],[14,16],[25,8]]')
    with contextlib.redirect_stdout(io.StringIO()):
        r=p.searching(json.loads(json.dumps(q)))
    assert p.macro_accepted>0
    assert abs(r['length']-sum(math.dist(a,b) for a,b in zip(p.plot.path,p.plot.path[1:])))<1e-7
    assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 for a,b in zip(p.plot.path,p.plot.path[1:]))
    for node in [(4,9),(20,15)]:
        assert abs(p.heuristic(node)-math.dist(node,p.s_goal)-math.dist(node,p.s_target))<1e-8


def test_structured_schema_is_cached_in_exact_reserved_payload(tmp_path):
    from strategic import schema
    ledger=CumulativeLedger(tmp_path/'ledger.sqlite3',tmp_path/'portable.json');calls=[]
    fmt=schema('choice',{'choice':{'type':'string','enum':['A','B']}})
    def transport(payload):
        calls.append(payload)
        assert payload['response_format']==fmt
        return {'model':'gpt-4o-mini-2024-07-18','choices':[{'message':{'content':'{"choice":"A"}'}}],
                'usage':{'prompt_tokens':30,'completion_tokens':5}}
    client=RetryClient(ledger,transport)
    for _ in range(2):
        client.chat([{'role':'user','content':'choose'}],{},response_format=fmt)
    assert len(calls)==1
    assert json.loads(ledger.db.execute('SELECT payload FROM requests').fetchone()[0])['response_format']==fmt


def test_only_embedded_local_images_are_allowed_before_reserving(tmp_path):
    from strategic import schema
    ledger=CumulativeLedger(tmp_path/'ledger.sqlite3',tmp_path/'portable.json')
    client=RetryClient(ledger,lambda payload:pytest.fail('must not send'))
    with pytest.raises(ValueError):
        client.chat([{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://unapproved.example/pic.png'}}]}],{},response_format=schema('empty',{}))
    assert ledger.summary()['attempts']==0


def test_cut_anchor_and_regret_order_remain_bounded_with_bad_advice():
    from llmastar.research.macro_guidance import MacroGuidedSearch
    from llmastar.research.incumbent import IncumbentSearch
    q=sample();q['horizontal_barriers']=[[12,8,26],[18,2,20]]
    ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[])
    for initial in [False,True]:
        r=MacroGuidedSearch(weight=1.05,heuristic='cut',target_order='regret',initial_chain=initial).search(q,[(2,21),(27,21),(13,2),(14,16)])
        assert r['valid'] and r['length']<=1.05*ref['length']+1e-7
    with pytest.raises(ValueError):MacroGuidedSearch(interval=1.5)


def test_geometry_and_disabled_controls_cannot_inherit_llm_route_metadata():
    spec=importlib.util.spec_from_file_location('session6_eval_regression',SESSION/'evaluate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    q=sample();case={'query':q,'optimal_cost':100.}
    for method in ['macro_portfolio_geometry','macro_portfolio_none']:
        a=module.execute(case,[(2,20)],method,None,{'routes':[[(27,20),(2,21)]]},'multi_strict')
        b=module.execute(case,[(25,4)],method,None,{'routes':[[(13,16)]]},'multi_strict')
        assert a['operation']==b['operation'] and a['length']==b['length']
        assert a['processed_waypoints']==b['processed_waypoints']


def test_evidence_triggered_revision_is_once_without_queue_rekey():
    from llmastar.research.macro_guidance import MacroGuidedSearch
    from llmastar.research.incumbent import IncumbentSearch
    q=sample();calls=[]
    def revise(context):
        calls.append(context)
        assert len(context['failed_macro_links'])==2
        assert sum(x['verified'] for x in context['failed_macro_links'])<=1
        return [(13,16)]
    r=MacroGuidedSearch(interval=1,heuristic='cut').search(q,[(25,5)],revision=revise,
        intervention_after=2,failure_window=2)
    ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[])
    assert len(calls)==r['revision_calls']==1 and r['rebuilds']==0
    assert r['valid'] and r['length']<=2*ref['length']+1e-7
    calls.clear()
    MacroGuidedSearch(probe_budget=0).search(q,[(25,5)],revision=revise)
    assert not calls


def test_easy_case_geometry_gate_is_identical_across_advisory_sources():
    spec=importlib.util.spec_from_file_location('session6_opportunity_regression',SESSION/'opportunity_study.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    q=sample();case={'query':q,'optimal_cost':100.}
    response={'points':[(2,20)],'meta':{'routes':[[(26,20)],[(2,3)]]}}
    for config in module.CONFIGS:
        rr=[module.run(case,response,config,source) for source in ['llm','geometry','all']]
        assert all(r['geometry_gate'] for r in rr)
        assert len({(r['heap_pops'],r['length'],tuple(r['processed_waypoints'])) for r in rr})==1


def test_adaptive_macro_confidence_updates_from_actual_edge_checks():
    from llmastar.research.macro_guidance import MacroGuidedSearch
    from llmastar.research.incumbent import IncumbentSearch
    q=sample();points=[(25,5),(12,16),(14,16),(3,20)]
    r=MacroGuidedSearch(heuristic='cut',target_order='adaptive',require_descent=True,interval=1).search(q,points)
    ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[])
    assert r['valid'] and r['length']<=2*ref['length']+1e-7
    assert r['trust_updates']>0 and 0<r['trust_contexts']<=r['trust_updates']
    assert r['rebuilds']==0 and r['macro_probes']<=256


def test_roadmap_complete_and_lazy_paths_have_exact_grid_costs():
    from roadmap import Roadmap
    from llmastar.research.geometry import SegmentGridGraph
    q=sample();full=Roadmap(q,k=None);ids,cost,_=full.shortest()
    assert ids and math.isfinite(cost)
    dense=full.dense_path(ids);g=SegmentGridGraph(q)
    assert abs(cost-sum(math.dist(a,b) for a,b in zip(dense,dense[1:])))<1e-8
    assert all(math.isfinite(g.cost(a,b)) for a,b in zip(dense,dense[1:]))
    lazy=Roadmap(q,k=1);_,lazy_cost,_=lazy.lazy_augment(len(lazy.points)**2)
    assert abs(lazy_cost-cost)<1e-8


def test_roadmap_verification_is_cached_and_blocked_links_never_trusted():
    from roadmap import Roadmap,complete_routes
    q=sample();roadmap=Roadmap(q,k=1)
    before=roadmap.probes
    for _ in range(3):assert not roadmap.verify('S','G')
    assert roadmap.probes<=before+1
    rows,_=complete_routes(roadmap,[['S','G']])
    assert not rows[0]['valid'] and rows[0]['cost'] is None


def test_interactive_frontier_uses_only_verified_prefixes_and_hard_budget():
    from frontier import plan
    from llmastar.research.geometry import SegmentGridGraph
    from llmastar.research.strategic.cuts import CutPotential
    q=sample();g=SegmentGridGraph(q);p=portfolio(q,g);potential=CutPotential(q,tuple(q['goal']))
    contexts=[]
    def controller(context):
        contexts.append(context)
        assert all(r['verified_prefix_cost']>=0 for r in context['frontier'])
        return context['frontier'][0]['id']
    result=plan(q,p,g,potential,controller,budget=2)
    assert result['abstract_expanded']<=3 and result['abstract_selections']<=2
    for a,b in zip(result['route'],result['route'][1:]):assert g.lattice_segment(a,b)
    if result['complete']:
        assert result['route'][0]==tuple(q['start']) and result['route'][-1]==tuple(q['goal'])
        assert abs(result['cost']-sum(max(abs(a[0]-b[0]),abs(a[1]-b[1]))+(math.sqrt(2)-1)*min(abs(a[0]-b[0]),abs(a[1]-b[1])) for a,b in zip(result['route'],result['route'][1:])))<1e-8


def test_deployable_planner_preserves_query_and_baseline_result_keys():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    q=sample();before=json.dumps(q,sort_keys=True)
    r=HybridWaypointPlanner().searching(q)
    assert r['valid'] and {'operation','storage','length','llm_output'}<=set(r)
    assert json.dumps(q,sort_keys=True)==before
    assert r['total_heap_pops']>=r['operation'] and r['provider_calls']==0


def test_consensus_votes_are_per_route_not_repeated_points():
    from llmastar.research.hybrid_guidance import select_targets
    routes=[[(2,3),(2,3),(4,5)],[(4,5),(8,9)],[(7,9)]]
    assert select_targets(routes)==[(4,5)]
    assert select_targets(routes[:1])==[(2,3),(4,5)]


def test_deployable_geometry_gate_never_calls_provider_and_handles_no_path():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    class Forbidden:
        def propose(self,q,c):pytest.fail('Model must not be invoked')
    open_q=dict(sample(),vertical_barriers=[])
    r=HybridWaypointPlanner(provider=Forbidden()).search(open_q)
    assert r['valid'] and r['geometry_gate'] and r['provider_calls']==0
    blocked=dict(sample(),vertical_barriers=[[13,0,24]])
    r=HybridWaypointPlanner(provider=Forbidden()).search(blocked)
    assert not r['valid'] and r['proof_unreachable'] and r['operation']==0


def test_shared_anchor_matches_unshared_search_and_rejects_wrong_goal():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    from llmastar.research.macro_guidance import MacroGuidedSearch
    from llmastar.research.strategic.cuts import CutPotential
    q=sample()
    a=HybridWaypointPlanner(share_anchor=True).search(q)
    b=HybridWaypointPlanner(share_anchor=False).search(q)
    assert a['operation']==b['operation'] and a['length']==b['length']
    wrong=CutPotential(q,(24,8))
    with pytest.raises(ValueError):MacroGuidedSearch(heuristic='cut').search(q,[],anchor=wrong)


def test_production_geometry_candidates_match_preserved_prototype():
    from llmastar.research.geometric_advice import portfolio as production
    q=sample();a=portfolio(q);b=production(q)
    assert a['candidates']==b['candidates'] and a['geometry_best']==b['geometry_best']
    assert a['heap_pops']==b['heap_pops'] and a['heap_pushes']==b['heap_pushes']


def test_original_json_and_natural_language_input_interfaces():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    q=dict(sample(),vertical_barriers=[])
    r=HybridWaypointPlanner().searching(json.dumps(q))
    assert r['valid'] and r['parsing_provider_calls']==0
    class Parser:
        def parse_query(self,text):assert text=='planning input';return q
        def propose(self,q,c):pytest.fail('Open route should not call planner model')
    r=HybridWaypointPlanner(provider=Parser()).searching('planning input')
    assert r['valid'] and r['parsing_provider_calls']==1


def test_failed_provider_retains_complete_classical_fallback():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    class Failed:
        def propose(self,q,c):raise TimeoutError('private details must not be persisted')
    a=HybridWaypointPlanner(provider=Failed(),source='llm_only').search(sample())
    b=HybridWaypointPlanner(source='goal_only').search(sample())
    assert a['valid'] and a['provider_error']=='TimeoutError'
    assert a['operation']==b['operation'] and a['length']==b['length']
    assert 'private details' not in json.dumps(a)


def test_roadmap_prompt_cache_identity_does_not_depend_on_runtime():
    from roadmap import Roadmap,roadmap_messages
    q=sample();p=Roadmap(q).proposal();a=roadmap_messages(q,p)
    p['preprocess_seconds']=1000.
    b=roadmap_messages(q,p)
    assert a==b


def test_probe_disabled_variant_has_no_advisory_effect():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    q=sample()
    a=HybridWaypointPlanner(source='llm_only',probe_budget=0).search(q,routes=[[(2,21),(27,20)]])
    b=HybridWaypointPlanner(source='goal_only',probe_budget=0).search(q)
    assert a['operation']==b['operation'] and a['path']==b['path']


def test_always_guidance_ablation_does_not_silently_use_geometry():
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    class Provider:
        def __init__(self):self.calls=0
        def propose(self,q,c):self.calls+=1;return {'routes':[[(3,20)]]}
    q=dict(sample(),vertical_barriers=[]);provider=Provider()
    r=HybridWaypointPlanner(provider=provider,source='hybrid_always').search(q)
    assert provider.calls==1 and not r['geometry_gate'] and r['geometry_route_available']
    assert (3,20) in r['processed_waypoints']
