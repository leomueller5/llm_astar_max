"""Development-only audit of real-response guidance and residual opportunity."""
import sys,json,gzip,statistics,math
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark import ROOT,cached_cases
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.efficient import EfficientCertificateSearch

def main():
 old=ROOT/'experiments/results/research'
 audit=json.loads((old/'waypoint_audit_development.json').read_text());labels=defaultdict(list)
 for p in audit['points']:labels[p['case_id']].append(p)
 with gzip.open(old/'iteration1_development/results.json.gz','rt') as f:runs=json.load(f)['runs']
 pairs=defaultdict(dict)
 for r in runs:
  if r['variant'] in ['robust_original','wa2']:pairs[r['case_id']][r['variant']]=r
 records=[]
 for c in cached_cases('development'):
  g=SegmentGridGraph(c['query']);r=EfficientCertificateSearch(segment_mode='analytic',witness=True,use_waypoints=False,prepare_only=True).search(c['query'],[],g)
  pts=labels[c['id']];rr=pairs.get(c['id'],{})
  records.append(dict(case_id=c['id'],map_id=c['map_id'],geometry_certified=r['valid'],raw_intermediate_points=len(pts),
    valid_reachable=sum(p['reachable'] and p['valid'] for p in pts),
    benign_forced_detour=sum(p['reachable'] and p['forced_route_ratio'] is not None and p['forced_route_ratio']<=1.1 for p in pts),
    guidance_unique=rr.get('robust_original',{}).get('unique'),control_unique=rr.get('wa2',{}).get('unique'),
    guidance_cost=rr.get('robust_original',{}).get('length'),control_cost=rr.get('wa2',{}).get('length')))
 summary=dict(previous_switch_audit=audit['summary'],cases=len(records),geometry_solved=sum(r['geometry_certified'] for r in records))
 for label,rows in [('all',records),('geometry_residual',[r for r in records if not r['geometry_certified']])]:
  paired=[r for r in rows if r['guidance_unique'] is not None and r['control_unique'] is not None]
  summary[label]={'cases':len(rows),'with_benign_point':sum(r['benign_forced_detour']>0 for r in rows),
   'fewer_expansions_with_original_formula':sum(r['guidance_unique']<r['control_unique'] for r in paired),
   'shorter_path_with_original_formula':sum(r['guidance_cost']<r['control_cost']-1e-9 for r in paired),
   'both_improved':sum(r['guidance_unique']<r['control_unique'] and r['guidance_cost']<r['control_cost']-1e-9 for r in paired)}
 out=ROOT/'experiments/results/research_session3';(out/'audit.json').write_text(json.dumps({'summary':summary,'cases':records},indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
