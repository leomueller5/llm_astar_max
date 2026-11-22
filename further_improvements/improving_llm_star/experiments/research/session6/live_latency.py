"""Small real end-to-end latency calibration, not algorithm selection."""
import argparse
import contextlib
import gzip
import io
import json
import math
import random
from pathlib import Path
from time import perf_counter
from api import RetryClient,RequestUnavailable
from run_hybrid import BudgetedGuidanceProvider
from hybrid import ROOT
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.hybrid_guidance import HybridWaypointPlanner
from final_benchmark import Engines


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);data=json.load(gzip.open(a.cases,'rt'))
    families=['random_walls','rooms','tree_maze','nested','competing_corridors','bottlenecks']
    selected=[next(c for c in data if c['family']==f and c['id'].endswith('_1')) for f in families]
    client=RetryClient();engines=Engines();rows=[];requests=[];rng=random.Random(667711)
    class LiveOriginalModel:
        def __init__(self,case):self.case=case;self.calls=0
        def ask(self,prompt=None,max_tokens=1000,**kwargs):
            self.calls+=1;tick=perf_counter()
            try:
                response,rid,cached=client.chat([{'role':'user','content':prompt}],
                    {'phase':'live_latency_original','prompt_version':'s6_original_v1',
                     'case_id':self.case['id']},max_tokens=1000)
                requests.append({'case_id':self.case['id'],'method':'original','request_id':rid,
                    'response':response,'cached':cached,'seconds':perf_counter()-tick})
                return response['choices'][0]['message'].get('content') or ''
            except RequestUnavailable:return 'Generated Path: []'
    for case in selected:
        order=['original','hybrid','geometry','all_endpoints'];rng.shuffle(order)
        for method in order:
            tick=perf_counter();q=case['query']
            if method=='original':
                graph=SegmentGridGraph(q);planner=engines.Original();planner.model=LiveOriginalModel(case)
                planner.cost=graph.cost;planner.is_collision=graph.collision
                with contextlib.redirect_stdout(io.StringIO()):r=planner.searching(json.loads(json.dumps(q)))
                path=planner.plot.path;r.update(valid=bool(path),path=path,provider_calls=planner.model.calls)
            else:
                provider=BudgetedGuidanceProvider(client) if method=='hybrid' else None
                source={'hybrid':'hybrid','geometry':'geometry_best','all_endpoints':'all_endpoints'}[method]
                r=HybridWaypointPlanner(provider=provider,source=source).search(q)
                if provider:
                    requests.extend({'case_id':case['id'],'method':method,**request} for request in provider.history)
            seconds=perf_counter()-tick;path=r.pop('path',[])
            assert r['valid'] and path[0]==tuple(q['start']) and path[-1]==tuple(q['goal'])
            graph=SegmentGridGraph(q)
            assert all(math.isfinite(graph.cost(x,y)) for x,y in zip(path,path[1:]))
            rows.append({'case_id':case['id'],'map_id':case['map_id'],'family':case['family'],
                'method':method,'full_end_to_end_seconds':seconds,'valid':r['valid'],
                'length':r['length'],'cost_ratio':r['length']/case['optimal_cost'],
                'logical_model_calls':r.get('provider_calls',0),'geometry_gate':r.get('geometry_gate')})
            tmp=a.output/'checkpoint.tmp'
            with gzip.open(tmp,'wt') as f:json.dump({'runs':rows,'requests':requests},f)
            tmp.replace(a.output/'checkpoint.json.gz')
        print(case['id'],'live calibration completed',flush=True)
    with gzip.open(a.output/'results.json.gz','wt') as f:json.dump({'scope':'Six preselected families, second query on the first held-out synthetic map per family. Actual live API+planning wall time, not reconstructed latency. This small calibration is not used for algorithm selection; primary220-query replay remains frozen.','runs':rows,'requests':requests},f)


if __name__=='__main__':main()
