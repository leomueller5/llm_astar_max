"""How often do genuine model proposals survive the frozen selection mechanism?"""
import argparse,json,statistics
from common import RESULTS,read_cases,dump
from llmastar.research.hybrid_guidance import normalize_routes,select_targets
from llmastar.research.geometry import SegmentGridGraph

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(RESULTS/'heldout_all.json.gz')};records=[r for r in read_cases(RESULTS/'heldout_baselines/responses.json.gz')['runs'] if r['baseline']=='vm'];rows=[]
 for r in records:
  q=cases[r['case_id']]['query'];skip=bool(r.get('meta',{}).get('api_skipped'));routes=r.get('meta',{}).get('routes') or [r.get('points',[])];normalized=normalize_routes({'routes':routes},SegmentGridGraph(q));selected=select_targets(normalized,'consensus');targets=list(dict.fromkeys(tuple(p) for p in selected if tuple(p) not in [tuple(q['start']),tuple(q['goal'])]));rows.append({'case_id':r['case_id'],'family':r['family'],'geometry_gate':skip,'provider_called':not skip,'raw_decoded_points':sum(map(len,routes)) if not skip else 0,'consensus_targets':len(targets) if not skip else 0,'usable_model_targets':not skip and bool(targets),'unknown_id_count':len(r.get('meta',{}).get('unknown_ids',[])),'schema_compatibility':bool(r.get('meta',{}).get('schema_compatibility_adapter'))})
 called=[r for r in rows if r['provider_called']];dump(a.output,{'scope':'Frozen model decoding/normalization/consensus only, without rerunning search. A nonzero target count is not proof a model macro was accepted or caused improvement. Geometry-gated paths are not model contributions. Consensus may remove diverse alternatives; this is measured, not retuned after test opening.','queries':len(rows),'geometry_gated_queries':sum(r['geometry_gate'] for r in rows),'provider_called_queries':len(called),'called_but_no_consensus_targets':sum(not r['usable_model_targets'] for r in called),'queries_with_usable_model_targets':sum(r['usable_model_targets'] for r in rows),'mean_selected_model_targets_when_called':statistics.mean(r['consensus_targets'] for r in called),'runs':rows});print('Model target utilization recorded')
if __name__=='__main__':main()
