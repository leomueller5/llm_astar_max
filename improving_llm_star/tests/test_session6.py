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
