"""Cached-response public API timing on predetermined validation queries."""
import sys,json,random,copy,statistics,gzip,contextlib,io
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import ROOT,cached_cases
from llmastar.pather import SeededLLMAStar,WitnessFirstLLMAStar


def main():
 cases=cached_cases('validation')[::5];rows=[];rng=random.Random(1632026)
 modes=['witness','seed_off','seed_cut','quality']
 for repeat in range(-1,7):
  for c in (cases[:2] if repeat<0 else cases):
   order=list(modes);rng.shuffle(order)
   for mode in order:
    if mode=='witness':p=WitnessFirstLLMAStar(use_waypoints=False)
    else:p=SeededLLMAStar(waypoint_response=c['response'],guidance=mode!='seed_off',strategy='quality' if mode=='quality' else 'cut')
    q=copy.deepcopy(c['query']);began=perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):r=p.searching(q)
    elapsed=perf_counter()-began
    assert p.search_metrics['path_valid']
    if repeat>=0:rows.append(dict(case_id=c['id'],map_id=c['map_id'],mode=mode,repeat=repeat,seconds=elapsed,cost=r['length']))
 summary={m:{'mean_case_median_ms':statistics.mean(statistics.median(r['seconds'] for r in rows if r['mode']==m and r['case_id']==c['id']) for c in cases)*1000} for m in modes}
 out=ROOT/'experiments/results/research_session3/public_timing.json'
 if out.exists():raise FileExistsError(out)
 out.write_text(json.dumps({'scope':'40 fixed validation queries,7 randomized interleaved repeats; query parse/copy, initial cached response processing, fresh geometry, guidance and search included. Construction/imports/network/rendering excluded uniformly. Guidance-disabled methods skip model parsing. No paid calls.','summary':summary,'runs':rows},indent=2)+'\n');print(summary)
if __name__=='__main__':main()
