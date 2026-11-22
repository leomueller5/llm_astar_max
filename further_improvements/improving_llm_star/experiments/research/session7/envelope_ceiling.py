"""Do safety envelopes themselves discard useful cost information? Offline only."""
import argparse,heapq,math,statistics
from common import read_cases,dump
from oracle import remaining_costs,FineOracle,regional_reference
from prompts_spatial import decode
from cost_controls import Scaled
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.spatial_guidance import SpatialSearch
ALPHA=.22640953779865894

def trusted_oracle(q,costs):
 # Explicit perfect-admissible reference, never available to the real planner.
 graph=SegmentGridGraph(q);start=tuple(q['start']);goal=tuple(q['goal']);best={start:0.};queue=[(costs[start],start,0.)];pops=0;pushes=1;closed=set()
 while queue:
  _,n,g=heapq.heappop(queue);pops+=1
  if g!=best[n] or n in closed:continue
  closed.add(n)
  if n==goal:return dict(valid=True,length=g,heap_pops=pops,heap_pushes=pushes,unique=len(closed))
  for m,c in graph.adj.get(n,[]):
   if g+c<best.get(m,math.inf)-1e-12:best[m]=g+c;heapq.heappush(queue,(g+c+costs[m],m,g+c));pushes+=1
 raise AssertionError('Oracle unreachable')

def main():
 p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();responses={(r['case_id'],r['representation']):r for r in read_cases(a.responses)['runs']};rows=[];reference_work=[]
 for c in read_cases(a.cases):
  q=c['query'];costs,work=remaining_costs(q);reference_work.append(dict(case_id=c['id'],**work));real,_=decode(q,responses[c['id'],'image']['response']['choices'][0]['message']['content'],4,'cost');fields=[('none',None),('real',Scaled(real,ALPHA)),('oracle4',regional_reference(q,4,costs)),('oracle_fine',FineOracle(q,costs))]
  for name,field in fields:
   for bound in [1.05,2.]:
    for mode in ['heuristic_envelope','envelope','focal']:
     r=SpatialSearch(mode=mode,bound=bound,base_weight=1.).search(q,field);assert r['valid'] and r['length']<=bound*c['optimal_cost']+1e-7;rows.append({'case_id':c['id'],'family':c['family'],'field':name,'mode':mode,'bound':bound,'pops':r['heap_pops'],'pushes':r['heap_pushes'],'unique':r['unique'],'cost_ratio':r['length']/c['optimal_cost']})
  r=trusted_oracle(q,costs);assert abs(r['length']-c['optimal_cost'])<1e-7;rows.append({'case_id':c['id'],'family':c['family'],'field':'TRUSTED_EXACT_ORACLE','mode':'oracle_admissible_anchor','bound':1.,'pops':r['heap_pops'],'pushes':r['heap_pushes'],'unique':r['unique'],'cost_ratio':1.})
 summary={}
 for field,mode,bound in sorted({(r['field'],r['mode'],r['bound']) for r in rows}):
  rr=[r for r in rows if (r['field'],r['mode'],r['bound'])==(field,mode,bound)];summary[f'{field}/{mode}/{bound}']={'pops':statistics.mean(r['pops'] for r in rr),'queue_ops':statistics.mean(r['pops']+r['pushes'] for r in rr),'unique':statistics.mean(r['unique'] for r in rr),'gm_cost_ratio':math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr))}
 dump(a.output,{'scope':'Validation-only explanatory ceiling after primary freeze. No paid requests or final-data tuning. Actual model fields use frozen training scalar. Exact oracle fields use coefficient1, exact remaining labels generated offline and never sent to a model. Trusted exact oracle additionally assumes known admissibility, unavailable for unverified model predictions; its reference-generation cost is not a speed claim. Full-key envelope changes permitted extra slack from (w-1)h to (w-1)(g+h); both keep goal priority g and have the documented w proof.','reference_generation':reference_work,'summary':summary,'runs':rows});print(summary)
if __name__=='__main__':main()
