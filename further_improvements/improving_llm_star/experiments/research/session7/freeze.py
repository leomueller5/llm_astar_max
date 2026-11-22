"""Freeze selected spatial method BEFORE new held-out map generation."""
import json,hashlib,subprocess
from datetime import datetime,timezone
from common import ROOT,WORKSPACE,RESULTS,read_cases,dump

def main():
    path=RESULTS/'frozen_manifest.json'
    if path.exists():raise FileExistsError(path)
    coefficient=read_cases(RESULTS/'cost_controls.json.gz')['full_development_alpha']['image']
    files=['llmastar/research/spatial_guidance.py','llmastar/research/spatial_calibration.py','llmastar/research/spatial_planner.py','llmastar/research/geometry.py','llmastar/research/strategic/cuts.py','llmastar/research/hybrid_guidance.py','llmastar/research/macro_guidance.py','experiments/research/session7/prompts_spatial.py','experiments/research/session7/prompts_grounded.py','experiments/research/session7/common.py','experiments/research/session6/strategic.py']
    sources={str(ROOT.name+'/'+f):hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    for f in ['llm-astar/llmastar/pather/llm_a_star/llm_a_star.py','llm-astar/llmastar/pather/a_star/a_star.py']:sources[f]=hashlib.sha256((WORKSPACE/f).read_bytes()).hexdigest()
    dump(path,{'status':'frozen','utc':datetime.now(timezone.utc).isoformat(),'branch':subprocess.check_output(['git','branch','--show-current']).decode().strip(),'pre_test_head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
        'primary':{'name':'LLM-RH*','class':'llmastar.research.spatial_planner.SpatialResidualAStar','bound':1.05,'alpha':coefficient,'side':4,'base_weight':1.,'source':'model','macros':False},
        'secondary_profile':{'bound':2.,'other_parameters':'same as primary'},
        'selection_rationale':'The tight1.05 profile improves validation total queue work and unique expansions relative to our looser2 profile, with a stronger theoretical bound. It does NOT beat the strongest uniform1.05 control in total queue work; no general LLM superiority claimed. Simpler calibrated residual retained over extra verified-interval preprocessing, after mixed dev/validation VRC results.',
        'coefficient_training':'One nonnegative scalar minimizes normalized residual MSE on20development map instances. The language model is unchanged; no model fine-tuning. Scalar is not tuned on validation or final work results.',
        'model':{'name':'gpt-4o-mini-2024-07-18','temperature':0,'seed':20261119,'prompt_version':'s7_cost_image_s4_grounded_v2','max_completion_tokens':1400,'original_max_completion_tokens':1000},
        'heldout':{'primary_maps_per_family':4,'primary_queries_per_map':2,'primary_generator_sizes':[97,131,163,197],'primary_seed_base':15310000,'families':10,'extra_queries':'third query/map reserved only for live latency calibration','large_maps_per_family':2,'large_queries_per_map':1,'large_generator_sizes':[227,263],'large_seed_base':16410000},
        'ablations':['same engine zero residual','same engine fixed1.05 and2inflation','same images rawalpha1','same input structured text calibratedalpha.07056526284991615','five region-shuffle seeds','same-query scalar mean residual','verified geometry-only residual midpoint','same frozen development ICL examples and primaryalpha','same-cost field with geometric macros','frozenSession6 genuinehybrid versus geometricmacro controls','frozenoriginal and robust original with same waypoint response'],
        'sources':sources,'policy':'No changes to selected algorithm, prompt, model parameters or calibration after opening heldout. Any correctness repair must be explicitly documented and previous runs preserved. All future decisions remain descriptive; no test-guided model selection.'})
    print(path)
if __name__=='__main__':main()
