"""Post-unblinding robustness control; no change to candidate, no new model call."""
import argparse,json
from pathlib import Path
from common import read_cases,dump,RESULTS
from analyze_native import collapse,summarize,paired

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);cases={c['id']:c for c in read_cases(RESULTS/'heldout_all.json.gz')};rows=collapse(read_cases(out/'results.json.gz')['runs'],cases);report={}
 for name in ['primary','large','all']:
  rr=[r for r in rows if name=='all' or r['stratum']==name];block=summarize(rr,{})['summary'];report[name]={'summary':block,'paired_hybrid_over_control':{control:{metric:paired(rr,control,metric,primary='vm_hybrid2',geometric=metric=='cost_ratio') for metric in ['queue_operations','seconds','unique','cost_ratio']} for control in ['vm_geo2','vm_consensus2','vm_abstain2','vm_shuffled2']}}
 dump(out/'analysis.json',{'scope':'Post-unblinding explanatory robustness check, not a new selected algorithm. All search/portfolio/weights frozen. Shuffled candidate-coordinate mapping is bijective, preserving route overlap/consensus and candidate cardinality; start/goal fixed. Thus useful spatial selection is separated from merely having fewer macro targets. Three shuffle seeds averaged within query, whole-map paired intervals. No paid calls or test-data parameter tuning.','strata':report});dump(out/'case_level.json.gz',rows);print(out/'analysis.json')
if __name__=='__main__':main()
