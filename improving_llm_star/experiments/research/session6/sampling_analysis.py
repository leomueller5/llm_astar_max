"""Output-variability sensitivity; temperature0.3, not the primary comparison."""
import argparse
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from hybrid import ROOT
from llmastar.research.hybrid_guidance import HybridWaypointPlanner


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    cases={c['id']:c for c in json.load(gzip.open(a.root/'sampling_development.json.gz','rt'))}
    rows=[];raw=defaultdict(set)
    for seed in [19,20,21]:
        data=json.load(gzip.open(a.root/f'sampling_seed{seed}/responses.json.gz','rt'))['runs']
        for response in data:
            c=cases[response['case_id']];routes=response['meta'].get('routes') or [response['points']]
            raw[c['id']].add(json.dumps(routes))
            for selection in ['first','consensus']:
                r=HybridWaypointPlanner(selection=selection).search(c['query'],routes={'routes':routes})
                assert r['valid'] and r['length']<=2*c['optimal_cost']+1e-7
                rows.append({'case_id':c['id'],'map_id':c['map_id'],'seed':20261100+seed,
                    'selection':selection,'pops':r['total_heap_pops'],'unique':r['unique'],
                    'cost_ratio':r['length']/c['optimal_cost'],'valid':r['valid']})
    summary={}
    for selection in ['first','consensus']:
        rr=[r for r in rows if r['selection']==selection]
        by=defaultdict(list)
        for r in rr:by[r['case_id']].append(r['pops'])
        summary[selection]={'trials':len(rr),'valid':sum(r['valid'] for r in rr),
            'mean_pops':statistics.mean(r['pops'] for r in rr),
            'mean_within_case_sd':statistics.mean(statistics.stdev(v) for v in by.values()),
            'largest_within_case_range':max(max(v)-min(v) for v in by.values()),
            'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr))}
    a.output.write_text(json.dumps({'scope':'Ten development cases selected by hash among geometry-unresolved queries. Three true API outputs at temperature0.3, same exact snapshot. Sensitivity only; main baseline uses temperature0. All methods replay the identical response per seed.','distinct_route_outputs':{k:len(v) for k,v in raw.items()},'summary':summary,'runs':rows},indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
