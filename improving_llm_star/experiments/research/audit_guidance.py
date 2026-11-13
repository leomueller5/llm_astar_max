"""Development-only waypoint lifetime and topology audit."""
from collections import defaultdict
import json,math,statistics
from pathlib import Path
from benchmark import cached_cases,dijkstra,GridGraph,ROOT


def main():
 cases=cached_cases('development');groups=defaultdict(list)
 for c in cases:groups[c['map_id']].append(c)
 points=[]
 for map_id,group in groups.items():
  graph=GridGraph(group[0]['query'])
  for c in group:
   start,goal=tuple(c['query']['start']),tuple(c['query']['goal'])
   ds,dg=dijkstra(graph,start),dijkstra(graph,goal);opt=ds.get(goal)
   for t in set(map(tuple,c['points']))-{start,goal}:
    valid=graph.valid_point(t);reachable=t in ds and t in dg
    ratio=(ds[t]+dg[t])/opt if reachable and opt else None
    points.append({'case_id':c['id'],'point':t,'valid':valid,'reachable':reachable,
                   'forced_route_ratio':ratio,'potentially_harmful':not reachable or ratio>1.1})
 data=json.loads((ROOT/'experiments/results/research/iteration1_development/results.json').read_text())
 originals=[r for r in data['runs'] if r['variant']=='original']
 life=[s['active_expansions'] for r in originals for s in r['switches']]
 switches=[s for r in originals for s in r['switches']]
 active=[r for r in data['runs'] if r['variant']=='current_adaptive']
 updates=[e for r in active for e in r['alpha_events'] if e['reason'] in ['stagnation','progress']]
 summary={'queries':len(cases),'intermediate_points':len(points),
  'invalid_point_fraction':sum(not p['valid'] for p in points)/len(points),
  'unreachable_fraction':sum(not p['reachable'] for p in points)/len(points),
  'potentially_harmful_fraction':sum(p['potentially_harmful'] for p in points)/len(points),
  'forced_route_definition':'Shortest path forced through point / unconstrained shortest cost > 1.1; not proof of causal soft-guidance harm',
  'switched_targets':len(life),'lifetime_median':statistics.median(life),
  'lifetime_p90':sorted(life)[int(.9*len(life))],
  'fraction_lifetimes_below30':sum(v<30 for v in life)/len(life),
  'fraction_lifetimes_below40':sum(v<40 for v in life)/len(life),
  'zero_lifetimes':sum(v==0 for v in life),
  'blocked_switch_fraction':sum(s['blocked_trigger'] for s in switches)/len(switches),
  'adaptive_queries_with_actual_adjustment':sum(any(e['reason'] in ['stagnation','progress'] for e in r['alpha_events']) for r in active),
  'actual_adjustments':len(updates)}
 out=ROOT/'experiments/results/research/waypoint_audit_development.json'
 out.write_text(json.dumps({'summary':summary,'points':points},indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
