"""Fresh correctness only: NO real-model performance claim and no API imports."""
import sys,json,gzip,math,random,argparse,contextlib,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from datasets import generate,geometry_hash,ROOT
from llmastar.research.real_guidance.lineage import PathConsistentSearch
from llmastar.research.geometry import SegmentGridGraph
from shapely.geometry import LineString
from shapely.strtree import STRtree


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);cases=generate('fresh',queries=2);known=set()
 for file in ['development.json.gz','validation.json.gz']:
  with gzip.open(ROOT/'experiments/results/research_session5'/file,'rt') as f:known.update(c['geometry_hash'] for c in json.load(f))
 for file in ['development_maps_v1.json.gz','fresh_maps_frozen.json.gz']:
  with gzip.open(ROOT/'experiments/results/research_session4'/file,'rt') as f:known.update(geometry_hash(c['query']) for c in json.load(f))
 assert not known&{c['geometry_hash'] for c in cases}
 with gzip.open(a.output/'cases.json.gz','wt') as f:json.dump(cases,f)
 rows=[];edges=0
 for c in cases:
  q=c['query'];g=SegmentGridGraph(q);rng=random.Random(sum(map(ord,c['id'])));hints=[]
  while len(hints)<3:
   p=rng.randrange(1,g.x1),rng.randrange(1,g.y1)
   if g.valid_point(p):hints.append(p)
  walls=[LineString([(a,y),(b,y)]) for y,a,b in q['horizontal_barriers']]+[LineString([(x,a),(x,b)]) for x,a,b in q['vertical_barriers']];tree=STRtree(walls)
  for mode,settings in [('none',dict(guidance=False)),('bounded',{}),('full',dict(trust=True,path_budget=True,skip_unverified=True)),('seed',dict(seed_prefix=True))]:
   r=PathConsistentSearch(score='bounded',**settings).search(q,hints)
   assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
   for a,b in zip(r['path'],r['path'][1:]):
    assert max(abs(a[0]-b[0]),abs(a[1]-b[1]))==1 and not len(tree.query(LineString([a,b]),predicate='intersects'));edges+=1
   assert abs(sum(math.dist(a,b) for a,b in zip(r['path'],r['path'][1:]))-r['length'])<1e-7
   rows.append({'case_id':c['id'],'mode':mode,'valid':True,'cost_ratio':r['length']/c['optimal_cost'],'unique':r['unique']})
 result={'scope':'Fresh-map algorithmic correctness on random synthetic targets ONLY, not held-out LLM evaluation. No model responses or optimal paths supplied as advice. Reference costs used only after search. Exact geometry disjoint from Session5 dev/validation and Session4 dev/fresh.','cases':len(cases),'maps':len(set(c['map_id'] for c in cases)),'checked_paths':len(rows),'shapely_edges':edges,'paid_api_calls':0,'runs':rows}
 (a.output/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='runs'}))
if __name__=='__main__':main()
