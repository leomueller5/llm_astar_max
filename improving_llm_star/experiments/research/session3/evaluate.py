"""Sequential frozen evaluation; no paid calls or opened-test reuse."""
import sys,json,gzip,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import run,add_ablation_inputs,cached_cases,ROOT,WORKSPACE
from cases import generate


def geometry_hash(q):
 d={k:q[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
 for k in ['horizontal_barriers','vertical_barriers']:d[k]=sorted(d[k])
 return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()


def main():
 out=ROOT/'experiments/results/research_session3';sel=json.loads((Path(__file__).parent/'selection.json').read_text());modes=sel['comparisons']
 validation=add_ablation_inputs(cached_cases('validation',['standard','cot','repe']))
 run(validation,modes,9,out/'validation')
 fresh=generate('fresh_test',3)
 previous=set()
 for name in ['development_cases','validation_cases','fresh_cases']:
  with gzip.open(ROOT/f'experiments/results/research_session2/{name}.json.gz','rt') as f:previous.update(geometry_hash(c['query']) for c in json.load(f))
 maps=json.loads((WORKSPACE/'llm-astar/dataset/environment_50_30.json').read_text());previous.update(geometry_hash(q) for q in maps)
 assert not {geometry_hash(c['query']) for c in fresh}&previous,'Geometry must be fresh, not just map ids'
 (out/'fresh_disjointness.json').write_text(json.dumps({'maps':len({c['map_id'] for c in fresh}),'cases':len(fresh),'prior_canonical_geometries_checked':len(previous),'exact_geometry_overlap':0,'seed_base':990000},indent=2)+'\n')
 fresh=add_ablation_inputs(fresh)
 with gzip.open(out/'fresh_cases.json.gz','wt') as f:f.write(json.dumps(fresh,separators=(',',':')))
 run(fresh,modes,7,out/'fresh')
 print('Frozen validation and fresh fixture evaluation complete.',flush=True)
if __name__=='__main__':main()
