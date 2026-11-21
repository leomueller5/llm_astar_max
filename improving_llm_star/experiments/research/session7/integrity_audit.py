"""Verify selected sources and transitive historical research dependencies."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from common import ROOT,WORKSPACE,RESULTS,dump
from native_benchmark import verify_sources

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();manifest=json.loads((RESULTS/'frozen_manifest.json').read_text());verify_sources(manifest);commit=manifest['pre_test_head'];rows=[];late={'improving_llm_star/llmastar/research/discrepancy_guidance.py','improving_llm_star/llmastar/research/pathmax_guidance.py'}
 paths=list((ROOT/'llmastar/research').rglob('*.py'))+list((WORKSPACE/'llm-astar/llmastar').rglob('*.py'))+[ROOT/'experiments/research/session4/maps.py',ROOT/'experiments/research/session6/final_benchmark.py']
 for p in paths:
  name=str(p.relative_to(WORKSPACE));now=hashlib.sha256(p.read_bytes()).hexdigest()
  if name in late:rows.append({'path':name,'status':'New separate late prototype, not used by frozen main benchmark'});continue
  if name in manifest['sources']:expected=manifest['sources'][name];origin='Explicit pre-test manifest'
  else:
   proc=subprocess.run(['git','show',commit+':'+name],cwd=WORKSPACE,capture_output=True)
   if proc.returncode:raise AssertionError('Unrecorded dependency not present at pre-test head: '+name)
   expected=hashlib.sha256(proc.stdout).hexdigest();origin='Immutable Git pre-test tree '+commit
  assert now==expected,('Changed historical/frozen dependency',name)
  rows.append({'path':name,'sha256':now,'origin':origin,'matches':True})
 branch=subprocess.check_output(['git','branch','--show-current'],text=True,cwd=WORKSPACE).strip();assert branch=='research/waypoint-guidance';main=subprocess.check_output(['git','rev-parse','main'],text=True,cwd=WORKSPACE).strip();assert main=='66baa31d2fc2b658b501dcd4b34e09d31af66cb4'
 dump(a.output,{'status':'passed','branch':branch,'main_unchanged':main,'selected_manifest_sources':len(manifest['sources']),'dependencies':rows,'scope':'Explicit pre-test hashes plus immutable pre-test Git tree verify all historical production research and frozen original package dependencies. New unselected prototypes labelled separately. Benchmark/analysis protocol addenda are documented, not retroactively claimed pre-frozen.'});print('Verified',len(rows),'production/dependency files; main unchanged')
if __name__=='__main__':main()
