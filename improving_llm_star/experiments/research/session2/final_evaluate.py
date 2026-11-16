"""Frozen, sequential final evaluation. Existing successful stages are not overwritten."""
import sys,json,gzip,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import run,cached_cases,ROOT
from cases import generate


def main():
 out=ROOT/'experiments/results/research_session2';selection=json.loads((Path(__file__).parent/'selection.json').read_text())
 casefile=out/'fresh_cases.json.gz'
 if casefile.exists():
  with gzip.open(casefile,'rt') as f:cases=json.load(f)
 else:
  cases=generate('fresh_test',8)
  with gzip.open(casefile,'wt') as f:json.dump(cases,f,separators=(',',':'))
 assert len(cases)==640 and len({c['map_id'] for c in cases})==80
 stages={};modes=selection['fresh_protocol']['variants']
 target=out/'fresh_core'
 if not (target/'summary.json').exists():run(cases,modes,11,target)
 stages['fresh_core']='complete';(out/'final_stages.json').write_text(json.dumps(stages,indent=2)+'\n')
 target=out/'fresh_native'
 if not (target/'summary.json').exists():
  subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('native.py')),'--cases',str(casefile),'--repeats','7','--output',str(target)],check=True)
 stages['fresh_native']='complete';(out/'final_stages.json').write_text(json.dumps(stages,indent=2)+'\n')
 target=out/'opened_cached_confirmation'
 if not (target/'summary.json').exists():run(cached_cases('test',['standard','cot','repe']),modes,7,target)
 stages['opened_cached_confirmation']='complete';(out/'final_stages.json').write_text(json.dumps(stages,indent=2)+'\n')
 print('All frozen evaluation stages complete.',flush=True)
if __name__=='__main__':main()
