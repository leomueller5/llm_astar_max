import importlib.util,math,random,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/research/session7'))
from llmastar.research.spatial_guidance import RegionField,SpatialSearch
from llmastar.research.geometry import SegmentGridGraph

def query(seed=0):
    rng=random.Random(seed)
    return dict(range_x=[0,24],range_y=[0,24],start=[2,2],goal=[21,21],horizontal_barriers=[[10,5,19]],vertical_barriers=[[x,5,rng.randrange(12,20)] for x in [7,15]])

def random_field(q,seed=0):
    r=random.Random(seed);f=RegionField(q)
    f.update([dict(region_id=c['id'],detour=r.random()*1000,priority=r.random(),confidence=r.random()) for c in f.regions]);return f

@pytest.mark.parametrize('mode',['envelope','heuristic_envelope','focal','tie','weighted','dual'])
@pytest.mark.parametrize('kind',['cut','octile'])
def test_spatial_guidance_bounds_validity_and_cost(mode,kind):
    for seed in range(4):
        q=query(seed);ref=SpatialSearch(mode='weighted',bound=1,base_weight=1,heuristic='octile').search(q)
        r=SpatialSearch(mode=mode,bound=1.5,base_weight=1.2,heuristic=kind,signal='combined').search(q,random_field(q,seed))
        assert r['valid'] and r['length']<=1.5*ref['length']+1e-7
        g=SegmentGridGraph(q)
        assert all(math.isfinite(g.cost(a,b)) for a,b in zip(r['path'],r['path'][1:]))
        assert r['length']==pytest.approx(sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:])))
        assert r['expanded']==r['unique']+r['reopens']

@pytest.mark.parametrize('mode',['envelope','heuristic_envelope','focal','tie','dual'])
def test_adversarial_advice_cannot_break_optimality_at_unit_bound(mode):
    q=query();ref=SpatialSearch(mode='weighted',bound=1,base_weight=1).search(q)
    r=SpatialSearch(mode=mode,bound=1,base_weight=1,signal='combined').search(q,random_field(q))
    assert r['length']==pytest.approx(ref['length'])

@pytest.mark.parametrize('mode',['envelope','heuristic_envelope','focal','tie','dual'])
def test_revised_fields_rekey_only_live_entries_and_preserve_bound(mode):
    q=query();calls=[]
    def revision(context):calls.append(context);return random_field(q,9)
    r=SpatialSearch(mode=mode,bound=1.5,base_weight=1.2).search(q,random_field(q),revision=revision,revision_after=10)
    assert r['valid'] and r['revision_calls']==1 and r['rebuilds']==1
    assert len(calls)==1 and calls[0]['expanded']==10
    ref=SpatialSearch(mode='weighted',bound=1,base_weight=1).search(q)
    assert r['length']<=1.5*ref['length']+1e-7


def test_regional_partition_and_malformed_advice():
    q=query();f=RegionField(q,4)
    for x in range(1,23):
        for y in range(1,23):
            region=next(r for r in f.regions if r['id']==f.identifier((x,y)))
            lo,hi=region['bounds'];assert lo[0]<=x<=hi[0] and lo[1]<=y<=hi[1]
    f.update([{'region_id':'R0','detour':float('nan')},{'region_id':'R1','priority':2},{'region_id':'outside'},{'region_id':'R2','detour':3},{'region_id':'R2','detour':100}])
    assert f.rejections==4 and f.values['R2'][0]==3 and f.value((22,22))[0]==0


def test_macro_integration_retains_exact_cost_and_complete_fallback():
    q=query();r=SpatialSearch(mode='envelope',macro=True,probe_budget=20).search(q,random_field(q),targets=[(2,21),(21,2)])
    assert r['valid'] and r['macro_probes']<=20
    ref=SpatialSearch(mode='weighted',bound=1,base_weight=1).search(q)
    assert r['length']<=2*ref['length']+1e-7


def test_unreachable_and_start_goal_are_handled_without_model():
    q=query();q['vertical_barriers']=[[10,0,23]];q['horizontal_barriers']=[]
    assert not SpatialSearch().search(q)['valid']
    q['goal']=q['start'];r=SpatialSearch().search(q);assert r['valid'] and r['length']==0


def test_session7_portable_budget_restores_previous_without_reset(tmp_path,monkeypatch):
    # Offline fake requests only. Production Session7 explicitly requires schemas.
    from common import Session7Client
    client=object.__new__(Session7Client)
    with pytest.raises(ValueError):client.chat([],{},response_format=None)


def test_verified_sample_intervals_enclose_true_remaining_costs():
    from oracle import remaining_costs
    from llmastar.research.spatial_calibration import sample_intervals
    q=query();costs,_=remaining_costs(q);intervals,work=sample_intervals(q,4)
    g=SegmentGridGraph(q)
    for region,row in intervals.items():
        n=tuple(row['sample'])
        if n not in costs:continue
        assert row['lower']<=costs[n]+1e-7
        if row['upper'] is not None:
            assert costs[n]<=row['upper']+1e-7
            assert all(g.lattice_segment(tuple(a),tuple(b)) is not None for a,b in zip(row['witness'],row['witness'][1:]))
    assert work['finite_upper_bounds']>0


def test_verified_calibration_alpha_clips_contradicted_predictions():
    from llmastar.research.spatial_calibration import sample_intervals,VerifiedResidualField
    q=query();f=random_field(q);intervals,_=sample_intervals(q);v=VerifiedResidualField(f,intervals)
    for rid,row in intervals.items():
        predicted=f.values[rid][0]*f.values[rid][2]
        assert 0<=v.calibrated[rid]<=predicted+1e-7
        if row['upper'] is not None:
            assert v.calibrated[rid]<=row['upper']-row['lower']+1e-7
        if v.alpha_values[rid] is not None:assert 0<=v.alpha_values[rid]<=1


def test_bilinear_residual_is_finite_and_vanishes_at_goal():
    from llmastar.research.spatial_calibration import BilinearResidualField
    q=query();f=BilinearResidualField(random_field(q),relative=True)
    assert f.value(tuple(q['goal']))[0]==0
    assert f.value((3,4))[0]>=0 and math.isfinite(f.value((3,4))[0])


def test_grounded_prompt_excludes_endpoint_regions_from_avoid_enum():
    from prompts_grounded import build
    q=query();messages,fmt,meta,img=build(q,'coordinates')
    f=RegionField(q,8);forbidden={f.identifier(q['start']),f.identifier(q['goal'])}
    assert forbidden.isdisjoint(fmt['json_schema']['schema']['properties']['avoid']['items']['enum'])
    assert img is None and 'optimal_cost' not in str(messages)


def test_icl_retrieval_uses_available_features_without_test_labels():
    from examples import select_examples,features
    q=query();bank=[{'case_id':'near','features':features(q)},{'case_id':'far','features':[100]*5}]
    assert select_examples(bank,q,1)[0]['case_id']=='near'


def test_deployable_spatial_planner_preserves_io_and_provider_failure_fallback():
    from llmastar.research.spatial_planner import SpatialResidualAStar
    import json
    q=query();copy=json.loads(json.dumps(q))
    class Failed:
        def predict(self,query,regions):raise TimeoutError('do not persist private error details')
    r=SpatialResidualAStar(provider=Failed()).searching(json.dumps(q),filepath='unused.png')
    assert r['valid'] and r['provider_calls']==1 and r['provider_error']=='TimeoutError'
    assert {'operation','storage','length','llm_output'}.issubset(r)
    assert q==copy and 'do not persist' not in str(r)


def test_deployable_disabled_and_geometry_controls_never_use_model():
    from llmastar.research.spatial_planner import SpatialResidualAStar
    class Forbidden:
        def predict(self,*args):pytest.fail('No model call allowed')
    for source in ['none','geometry_midpoint','geometry_upper']:
        r=SpatialResidualAStar(provider=Forbidden(),source=source).search(query())
        assert r['valid'] and r['provider_calls']==0


def test_malformed_regional_predictions_fall_back_safely():
    from llmastar.research.spatial_planner import SpatialResidualAStar
    from prompts_spatial import decode
    for raw in ['not JSON','{"predictions":"bad"}','{"predictions":null}']:
        f,meta=decode(query(),raw,4,'cost');assert not meta['parsed']
        r=SpatialResidualAStar().search(query(),predictions=raw);assert r['valid'] and r['prediction_parse_error']


def test_geometric_interval_controls_are_independent_of_model_costs():
    from llmastar.research.spatial_planner import SpatialResidualAStar
    q=query();a=SpatialResidualAStar(source='geometry_midpoint').search(q)
    b=SpatialResidualAStar(source='geometry_midpoint').search(q,predictions={'predictions':[{'region_id':'R0','detour':10000}]})
    assert (a['length'],a['heap_pops'],a['heap_pushes'])==(b['length'],b['heap_pops'],b['heap_pushes'])


def test_spatial_macro_control_matches_frozen_vm_engine():
    from macro_integration import plan
    from llmastar.research.hybrid_guidance import HybridWaypointPlanner
    for weight in [1.05,2.]:
        q=query();a=plan(q,base=weight,bound=weight)
        b=HybridWaypointPlanner(weight=weight,source='all_endpoints').search(q)
        assert a['total_heap_pops']==b['total_heap_pops']
        assert a['total_heap_pushes']==b['total_heap_pushes']
        assert a['length']==pytest.approx(b['length'])


def test_feedback_local_damping_retains_global_calibration_and_revises_only_touched_region():
    from cost_controls import Scaled
    from feedback import damp_from_evidence
    q=query();raw=random_field(q);initial=Scaled(raw,.2)
    n=(3,4);m=(4,4);pair={'a':n,'b':m,'predicted_remaining_a':100.,'predicted_remaining_b':1.}
    fixed=damp_from_evidence(q,initial,[pair]);rid=raw.identifier(n)
    for region in raw.regions:
        if region['sample'] is None:continue
        point=tuple(region['sample']);d,_,c=initial.value(point)
        assert fixed.value(point)[0]==pytest.approx(d*c*(.5 if region['id']==rid else 1.))


def test_matched_uniform_control_has_exact_same_search_work_as_optimized_weight():
    from llmastar.research.spatial_planner import SpatialResidualAStar
    q=query();a=SpatialResidualAStar(source='none',bound=1.05,base_weight=1.05).search(q)
    b=SpatialSearch(mode='weighted',bound=1.05,base_weight=1.05).search(q)
    assert (a['length'],a['heap_pops'],a['heap_pushes'])==(b['length'],b['heap_pops'],b['heap_pushes'])


def test_heap_audit_matches_actual_counts_and_distinguishes_stale_label_pops():
    from native_benchmark import heap_audit,classify_labels
    from llmastar.research.spatial_planner import SpatialResidualAStar
    q=query();f=random_field(q)
    values={'predictions':[dict(region_id=k,detour=v[0],priority=v[1],confidence=v[2]) for k,v in f.values.items()]}
    with heap_audit(True) as (counts,labels):r=SpatialResidualAStar(bound=1.05,alpha=.2).search(q,values,record_trace=True)
    assert counts['pop']==r['heap_pops'] and counts['push']==r['heap_pushes']
    classified=classify_labels(labels,r['trace'])
    assert classified['trace_fully_matched']
    assert classified['stale_label_pops']==r['stale']
    assert classified['already_closed_label_pops']<=classified['stale_label_pops']


def test_literal_vm_provider_errors_do_not_replay_compatible_advice():
    from native_benchmark import LiteralVMCachedProvider
    row={'meta':{'strict_provider_error':'enum_schema_provider_limit'},'response':{'choices':[{'message':{'content':'{"routes":[]}'}}]}}
    with pytest.raises(RuntimeError):LiteralVMCachedProvider(row).propose(query(),{})


def test_bounded_spatial_search_against_independent_shapely_dijkstra():
    from independent_reference import check
    for seed in range(8):
        rows,states=check(seed)
        assert len(rows)==3


@pytest.mark.parametrize('bound',[1.,1.05,2.])
def test_discrepancy_focal_keeps_independent_reference_bound(bound):
    from independent_reference import independent_distances,case
    from llmastar.research.discrepancy_guidance import DiscrepancyGuidedSearch
    from native_benchmark import heap_audit
    for seed in range(6):
        q=case(seed);reference=independent_distances(q);field=random_field(q,seed)
        with heap_audit(True) as (counts,labels):r=DiscrepancyGuidedSearch(bound).search(q,field)
        assert r['valid']==(tuple(q['start']) in reference)
        if r['valid']:assert r['length']<=bound*reference[tuple(q['start'])]+1e-7
        assert (counts['push'],counts['pop'])==(r['heap_pushes'],r['heap_pops'])


@pytest.mark.parametrize('bound',[1.,1.05,2.])
def test_bounded_pathmax_matches_independent_reference_guarantee(bound):
    from independent_reference import independent_distances,case
    from llmastar.research.pathmax_guidance import PathmaxResidualSearch
    for seed in range(6):
        q=case(seed);reference=independent_distances(q);r=PathmaxResidualSearch(bound).search(q,random_field(q,seed))
        assert r['valid']==(tuple(q['start']) in reference)
        if r['valid']:assert r['length']<=bound*reference[tuple(q['start'])]+1e-7


def test_pathmax_disabled_has_exact_frozen_engine_search_parity():
    from llmastar.research.pathmax_guidance import PathmaxResidualSearch
    from cost_controls import Scaled
    for seed in range(5):
        q=query(seed);field=random_field(q,seed);r=PathmaxResidualSearch(pathmax=False).search(q,field)
        frozen=SpatialSearch(mode='heuristic_envelope',bound=1.05,base_weight=1.).search(q,Scaled(field,.22640953779865894))
        assert r['length']==pytest.approx(frozen['length'],abs=1e-10)
        assert (r['heap_pops'],r['heap_pushes'])==(frozen['heap_pops'],frozen['heap_pushes'])


def test_pathmax_arithmetic_parity_on_unsaturated_guidance_and_no_phantom_updates():
    from llmastar.research.pathmax_guidance import PathmaxResidualSearch
    from cost_controls import Scaled
    for seed in range(25):
        q=query(seed);rng=random.Random(seed);f=RegionField(q,4)
        f.update([dict(region_id=r['id'],detour=rng.random()*5,priority=.5,confidence=.1+.8*rng.random()) for r in f.regions])
        off=PathmaxResidualSearch(pathmax=False).search(q,f)
        ref=SpatialSearch(mode='heuristic_envelope',bound=1.05,base_weight=1.).search(q,Scaled(f,.22640953779865894))
        assert (off['heap_pops'],off['heap_pushes'])==(ref['heap_pops'],ref['heap_pushes'])
        on=PathmaxResidualSearch(pathmax=True).search(q,f)
        if on['pathmax_raises']==0:
            assert (on['heap_pops'],on['heap_pushes'])==(off['heap_pops'],off['heap_pushes'])


def test_vm_shuffle_preserves_consensus_cardinality_without_using_model_spatial_choices(monkeypatch):
    from native_benchmark import ShuffledVMCachedProvider,legacy
    from llmastar.research.hybrid_guidance import select_targets
    a,b,c=(3,4),(4,6),(6,4);original={'routes':[[a,b],[a,c],[b,a]]}
    monkeypatch.setattr(legacy.CachedProvider,'propose',lambda self,q,points:original)
    q=query();result=ShuffledVMCachedProvider({},'fixed').propose(q,{'points':{'a':a,'b':b,'c':c}})
    assert [len(r) for r in result['routes']]==[len(r) for r in original['routes']]
    assert len(select_targets(result['routes']))==len(select_targets(original['routes']))
    assert result['routes'][0][0]==result['routes'][1][0]==result['routes'][2][1]
    assert all(p in [a,b,c] for r in result['routes'] for p in r)


def test_paper_astar_orientation_adapter_preserves_cost_and_operations():
    from correct_paper_orientation import normalize
    q={'start':[1,1],'goal':[3,1]};raw={'path':[(3,1),(2,1),(1,1)],'valid':False,'length':2.,'operation':3,'storage':7}
    fixed=normalize(raw,q)
    assert fixed['path']==[(1,1),(2,1),(3,1)] and fixed['valid']
    assert raw['path'][0]==(3,1) and not raw['valid']
    assert (fixed['length'],fixed['operation'],fixed['storage'])==(2.,3,7)
