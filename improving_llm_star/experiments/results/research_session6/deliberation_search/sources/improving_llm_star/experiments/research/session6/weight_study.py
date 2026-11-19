"""Quality/work tradeoff, with matched geometry and real-guidance controls."""
import argparse
import gzip
import json
import math
import statistics
from pathlib import Path
from time import perf_counter
from hybrid import portfolio,ROOT
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.macro_guidance import MacroGuidedSearch


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);cases={c['id']:c for c in json.load(gzip.open(a.cases,'rt'))}
    inputs=json.load(gzip.open(a.responses,'rt'))['runs'];rows=[]
    for case_response in inputs:
        c=cases[case_response['case_id']];q=c['query']
        for weight in [1.,1.05,1.2,2.]:
            for mode in ['llm','geometry','no_advice']:
                for rep in range(3):
                    tick=perf_counter();graph=SegmentGridGraph(q);proposal=portfolio(q,graph)
                    points=case_response['points'] if mode=='llm' else proposal['geometry_best'] if mode=='geometry' else []
                    r=MacroGuidedSearch(weight=weight,heuristic='cut').search(q,points,graph)
                    seconds=perf_counter()-tick;r.pop('path',None);r.pop('trace',None);r.pop('events',None)
                    if r['valid']:assert r['length']<=weight*c['optimal_cost']+1e-7
                    rows.append(dict(r,case_id=c['id'],map_id=c['map_id'],weight=weight,
                        mode=mode,rep=rep,full_compute_seconds=seconds,
                        cost_ratio=r['length']/c['optimal_cost'] if r['valid'] else None))
        print(c['id'],'completed',flush=True)
    summary={}
    for weight,mode in sorted({(r['weight'],r['mode']) for r in rows}):
        rr=[r for r in rows if r['weight']==weight and r['mode']==mode];one=[r for r in rr if r['rep']==0]
        summary[str(weight)+'/'+mode]={'valid':sum(r['valid'] for r in one),'cases':len(one),
            'mean_pops':statistics.mean(r['heap_pops'] for r in one),
            'mean_unique':statistics.mean(r['unique'] for r in one),
            'mean_ms':1000*statistics.mean(statistics.median(r['full_compute_seconds'] for r in rr if r['case_id']==c['case_id']) for c in one),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in one if r['valid']))}
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'summary':summary,'runs':rows},f)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
