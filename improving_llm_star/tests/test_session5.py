import importlib.util,json,sys,math
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('session5_budget',ROOT/'experiments/research/session5/api_budget.py');budget=importlib.util.module_from_spec(spec);spec.loader.exec_module(budget)


def test_persistent_budget_cache_and_reasoning_accounting(tmp_path):
    ledger=budget.Ledger(tmp_path/'ledger.sqlite3');calls=[]
    def transport(payload):
        calls.append(payload)
        return {'model':budget.MODEL,'choices':[{'message':{'content':'OK'}}],'usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':40},'completion_tokens_details':{'reasoning_tokens':12}}}
    client=budget.BudgetClient(ledger,transport)
    for _ in range(2):client.chat([{'role':'user','content':'hello'}],{'case':'one'},max_tokens=32)
    assert len(calls)==1
    assert ledger.summary()['accounted_usd']==(60*150+40*75+20*600)/1e9
    assert ledger.summary()['reasoning_tokens']==12
    reopened=budget.Ledger(tmp_path/'ledger.sqlite3')
    assert reopened.summary()['successes']==1
    assert (tmp_path/'api_export.json').is_file()


def test_failed_unknown_cost_stays_reserved_and_no_retry(tmp_path):
    ledger=budget.Ledger(tmp_path/'ledger.sqlite3')
    def fail(payload):raise TimeoutError('must not persist raw exception details')
    client=budget.BudgetClient(ledger,fail)
    with pytest.raises(budget.RequestUnavailable):client.chat([{'role':'user','content':'x'}],{'case':'fail'},max_tokens=8)
    with pytest.raises(budget.RequestUnavailable):client.chat([{'role':'user','content':'x'}],{'case':'fail'},max_tokens=8)
    assert ledger.summary()['attempts']==1 and ledger.summary()['held_worst_case_usd']>0
    assert 'must not persist' not in (tmp_path/'api_export.json').read_text()


def test_strict_cap_blocks_before_transport(tmp_path,monkeypatch):
    ledger=budget.Ledger(tmp_path/'ledger.sqlite3');monkeypatch.setattr(budget,'CAP',100)
    def must_not_run(payload):raise AssertionError('transport must not be reached')
    with pytest.raises(budget.BudgetExceeded):budget.BudgetClient(ledger,must_not_run).chat([{'role':'user','content':'x'}],{})
    assert ledger.summary()['attempts']==0


def test_lineage_claims_match_immutable_real_paths():
    from llmastar.research.real_guidance.lineage import PathConsistentSearch
    q={'range_x':[0,24],'range_y':[0,20],'start':[2,6],'goal':[21,6],'vertical_barriers':[[10,2,12]],'horizontal_barriers':[]}
    points=[(8,14),(12,14)]
    r=PathConsistentSearch().search(q,points,record_trace=True)
    assert r['valid'] and r['rebuilds']==0
    for row in r['trace']:
        for target in r['processed_waypoints'][:row['stage']]:assert target in row['ancestry']
        assert abs(row['g']-sum(math.dist(x,y) for x,y in zip(row['ancestry'],row['ancestry'][1:])))<1e-8


def test_bounded_branch_guidance_quality_and_dynamic_rekey():
    import random
    from llmastar.research.real_guidance.lineage import PathConsistentSearch
    from llmastar.research.incumbent import IncumbentSearch
    from llmastar.research.geometry import SegmentGridGraph
    rng=random.Random(20261118)
    for k in range(12):
        q={'range_x':[0,20],'range_y':[0,18],'start':[2,3],'goal':[17,14],'vertical_barriers':[[8,1,10],[13,6,16]],'horizontal_barriers':[]}
        g=SegmentGridGraph(q);ref=IncumbentSearch(use_waypoints=False,visibility_budget=0,goal_weight=1).search(q,[],g)
        hints=[(rng.randrange(1,19),rng.randrange(1,17)) for _ in range(4)]
        for budgeted in [False,True]:
            r=PathConsistentSearch(score='bounded',trust=True,path_budget=budgeted,skip_unverified=True).search(q,hints)
            assert r['valid'] and r['length']<=2*ref['length']+1e-7
    calls=[]
    def revise(context):calls.append(context);return [(9,13),(14,4)]
    r=PathConsistentSearch(score='bounded',intervention_after=2).search(q,[(2,15)],revision=revise)
    assert r['valid'] and len(calls)==1 and r['revision_calls']==1 and r['rebuilds']<=1
    assert r['length']<=2*ref['length']+1e-7


def test_disabled_guidance_keeps_final_goal_weight_and_duplicates_stale():
    from llmastar.research.real_guidance.lineage import PathConsistentSearch
    q={'range_x':[0,20],'range_y':[0,18],'start':[2,3],'goal':[17,14],'vertical_barriers':[],'horizontal_barriers':[]}
    r=PathConsistentSearch(guidance=False,score='bounded').search(q,[(1,16)],record_trace=True)
    assert r['valid'] and not r['processed_waypoints']
    for row in r['trace']:assert abs(row['priority']-(row['g']+2*math.dist(row['node'],tuple(q['goal']))))<1e-8


def test_verified_seed_really_resolves_waypoint_without_global_rekey():
    from llmastar.research.real_guidance.lineage import PathConsistentSearch
    from llmastar.research.geometry import SegmentGridGraph
    q={'range_x':[0,30],'range_y':[0,20],'start':[2,5],'goal':[26,5],'vertical_barriers':[[14,1,12]],'horizontal_barriers':[]}
    r=PathConsistentSearch(score='bounded',seed_prefix=True).search(q,[(13,13)],record_trace=True)
    assert r['valid'] and r['seeded_targets']==1 and r['seed_edges']>0 and r['rebuilds']==0
    for row in r['trace']:
        for target in r['processed_waypoints'][:row['stage']]:assert target in row['ancestry']
    g=SegmentGridGraph(q)
    assert all(math.isfinite(g.cost(a,b)) for a,b in zip(r['path'],r['path'][1:]))


def test_budget_restores_from_committed_response_export(tmp_path):
    first=budget.Ledger(tmp_path/'original.sqlite3')
    response={'model':budget.MODEL,'usage':{'prompt_tokens':12,'completion_tokens':8},'choices':[{'message':{'content':'OK'}}]}
    budget.BudgetClient(first,lambda p:response).chat([{'role':'user','content':'x'}],{'case':'restore'},max_tokens=8)
    restored=budget.Ledger(tmp_path/'new.sqlite3')
    assert restored.summary()['attempts']==1
    assert restored.summary()['accounted_usd']==first.summary()['accounted_usd']


def test_direct_original_repair_is_once_and_falls_back_on_unreachable():
    import sys,importlib.util,contextlib,io
    experiment=ROOT/'experiments';sys.path.insert(0,str(experiment));sys.path.insert(0,str(experiment/'research/session5'))
    import measure_waypoint_progress as replay
    import repair
    replay.BACKEND='installed';Original=replay.load_planner(ROOT.parent/'llm-astar',response='');Variant=repair.repaired_class(Original)
    q={'range_x':[0,22],'range_y':[0,18],'start':[2,4],'goal':[18,4],'horizontal_barriers':[],'vertical_barriers':[[10,1,10]]}
    calls=[]
    def correction(ctx):calls.append(ctx);return [q['start'],[9,12],[11,12],q['goal']]
    p=Variant();p.model=replay.OfflineModel('Generated Path: [[2,4],[10,5],[18,4]]');p.set_repair(q,[(2,4),(10,5),(18,4)],correction,threshold=2,gated=True)
    from llmastar.research.geometry import SegmentGridGraph
    g=SegmentGridGraph(q);p.cost=g.cost;p.is_collision=lambda a,b:not math.isfinite(g.cost(a,b))
    with contextlib.redirect_stdout(io.StringIO()):r=p.searching(json.loads(json.dumps(q)))
    assert len(calls)==1 and p.repair_attempts==1 and p.repair_accepted==1 and r['length']>0
    assert all(math.isfinite(g.cost(a,b)) for a,b in zip(p.plot.path,p.plot.path[1:]))
    blocked=dict(q,vertical_barriers=[[10,0,18]])
    p=Variant();p.model=replay.OfflineModel('Generated Path: [[2,4],[18,4]]');p.set_repair(blocked,[(2,4),(18,4)],lambda c:None,threshold=100000)
    g=SegmentGridGraph(blocked);p.cost=g.cost;p.is_collision=lambda a,b:not math.isfinite(g.cost(a,b))
    with contextlib.redirect_stdout(io.StringIO()):r=p.searching(json.loads(json.dumps(blocked)))
    assert not r['valid'] and p.plot.path==[] and p.classical_fallback_result['valid'] is False
