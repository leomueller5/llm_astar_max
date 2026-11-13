"""Check production lazy geometry reproduces all selected held-out search results."""
import gzip,json,math
from benchmark import ROOT,cached_cases
from datasets import generate
from llmastar.research.search import LazyGridGraph
from llmastar.research.incumbent import IncumbentSearch

def main():
 base=ROOT/'experiments/results/research';counts={}
 for suite,cases in [('heldout_cached',cached_cases('test',['standard','cot','repe'])),('heldout_synthetic',generate('test',3))]:
  with gzip.open(base/suite/'results.json.gz','rt') as stream:data=json.load(stream)
  stored={r['case_id']:r for r in data['runs'] if r['variant']=='sieved_cert'}
  for c in cases:
   r=IncumbentSearch(certificate=1,repair_radius=1,obstacle_certificate=True,certificate_only=True,certificate_pruning=True).search(c['query'],c['points'],LazyGridGraph(c['query']))
   s=stored[c['id']]
   assert r['valid']==s['valid'] and r['unique']==s['unique'] and r['operation']==s['operation']
   assert (r['length'] is None and s['length'] is None) or math.isclose(r['length'],s['length'],abs_tol=1e-9)
  counts[suite]=len(cases)
 (base/'native_geometry_verification.json').write_text(json.dumps(counts,indent=2)+'\n')
 print(counts)
if __name__=='__main__':main()
