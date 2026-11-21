"""Resumable, sequential final audits. Offline only: does not instantiate API client.

Run only after final_native completion. Different timing blocks never run
concurrently. Existing completed artifacts are reused, never overwritten.
"""
import sys,subprocess,json
from pathlib import Path
from common import HERE,RESULTS,read_cases,dump
PYTHON=sys.executable

def run(script,args,completion):
 if Path(completion).is_file():print('REUSE',completion,flush=True);return
 cmd=[PYTHON,str(HERE/script)]+[str(x) for x in args];print('RUN',script,flush=True);subprocess.run(cmd,check=True)

def main():
 r=RESULTS;assert (r/'final_native/completion.json').is_file(),'Finish main timings first'
 cases=r/'heldout_all.json.gz';base=r/'heldout_baselines/responses.json.gz';cost=r/'heldout_cost/responses.json.gz';icl=r/'heldout_icl/responses.json.gz';common=['--cases',cases,'--baselines',base,'--costs',cost,'--icl',icl,'--timeout',5]
 subprocess.run([PYTHON,'-m','pytest','improving_llm_star/tests','-q'],check=True)
 for split,responses in [('development','cost_pilot'),('validation','validation_cost')]:
  for script in ['discrepancy_pilot.py','pathmax_pilot.py']:
   output=r/((script[:-3] if script!='pathmax_pilot.py' else 'pathmax_v2')+'_'+split+'.json.gz');run(script,['--cases',r/(split+'.json.gz'),'--responses',r/responses/'responses.json.gz','--output',output],output)
 run('envelope_ceiling.py',['--cases',r/'validation.json.gz','--responses',r/'validation_cost/responses.json.gz','--output',r/'envelope_ceiling_validation.json.gz'],r/'envelope_ceiling_validation.json.gz')
 run('independent_reference.py',['--maps',100,'--output',r/'independent_reference.json.gz'],r/'independent_reference.json.gz')
 run('native_benchmark.py',common+['--methods','matched_uniform2','rh_macro_zero105','rh_macro_uniform105','--repeats',5,'--output',r/'aux_native'],r/'aux_native/completion.json')
 run('native_benchmark.py',common+['--methods','original_goal_only','robust_goal_only','--repeats',0,'--skip-warmup','--output',r/'goal_only_counts'],r/'goal_only_counts/completion.json')
 run('native_benchmark.py',common+['--methods','paper_astar','--repeats',0,'--skip-warmup','--output',r/'paper_denominator'],r/'paper_denominator/completion.json')
 merged=r/'bounds_baselines.json.gz'
 if not merged.exists():dump(merged,{'runs':read_cases(base)['runs']+read_cases(r/'heldout_bounds/responses.json.gz')['runs']})
 run('native_benchmark.py',['--cases',r/'bounds_control_cases.json.gz','--baselines',merged,'--costs',cost,'--icl',icl,'--methods','original','original_bounds','robust_original','rh_image105','matched_uniform105','vm_geo105','--repeats',3,'--output',r/'bounds_native'],r/'bounds_native/completion.json')
 run('correct_paper_orientation.py',['--output',r/'paper_denominator_corrected'],r/'paper_denominator_corrected/CORRECTION.json')
 combined=r/'combined_results.json.gz';run('combine_runs.py',['--inputs',r/'final_native/results.json.gz',r/'aux_native/results.json.gz',r/'goal_only_counts/results.json.gz','--output',combined],combined)
 run('analyze_native.py',['--results',combined,'--cases',cases,'--paper',r/'paper_denominator_corrected/results.json.gz','--output',r/'final_analysis_corrected'],r/'final_analysis_corrected/analysis.json')
 run('analyze_native.py',['--results',r/'bounds_native/results.json.gz','--cases',r/'bounds_control_cases.json.gz','--output',r/'bounds_analysis'],r/'bounds_analysis/analysis.json')
 for folder in ['final_native','aux_native','goal_only_counts','bounds_native','paper_denominator_corrected']:
  run('audit_paths.py',['--cases',cases,'--paths',r/folder/'paths.json.gz','--output',r/folder/'independent_paths.json'],r/folder/'independent_paths.json')
 run('prediction_audit.py',['--cases',cases,'--traces',r/'final_native/traces.json.gz','--output',r/'prediction_audit.json.gz'],r/'prediction_audit.json.gz')
 run('tradeoffs.py',['--case-level',r/'final_analysis_corrected/case_level.json.gz','--output',r/'tradeoffs.json'],r/'tradeoffs.json')
 run('guidance_audit.py',['--output',r/'guidance_audit'],r/'guidance_audit/seed_search.json.gz')
 run('resource_audit.py',['--cases',cases,'--output',r/'resources'],r/'resources/results.json.gz')
 run('figures.py',['--analysis',r/'final_analysis_corrected/analysis.json','--predictions',r/'prediction_audit.json.gz','--output',r/'figures'],r/'figures/prediction_accuracy.pdf')
 dump(r/'offline_complete.json',{'status':'All sequential timing/control/correctness/analysis steps completed. No paid calls. Inspect reports, complete live-latency audit separately if desired, then final documentation/secret/commit checks.'})
if __name__=='__main__':main()
