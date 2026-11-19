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
