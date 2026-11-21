import argparse,statistics,math
from common import read_cases,dump
from prompts_spatial import decode
from oracle import remaining_costs,regional_reference,FineOracle
from feedback import evidence,GeometricBoost,damp_from_evidence
from cost_controls import Scaled,Constant
from llmastar.research.spatial_guidance import SpatialSearch

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--coefficients',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases={c['id']:c for c in read_cases(a.cases)};alpha=read_cases(a.coefficients)['full_development_alpha'];rows=[]
    for rr in read_cases(a.responses)['runs']:
        if rr['representation']!='image':continue
        c=cases[rr['case_id']];q=c['query'];raw,_=decode(q,rr['response']['choices'][0]['message']['content'],rr['side'],'cost');field=Scaled(raw,alpha['image']);costs,work=remaining_costs(q);regional=regional_reference(q,rr['side'],costs);fine=FineOracle(q,costs)
        for method in ['none','observe','halve','zero','strong_anchor','classical_local','oracle_regional','oracle_fine']:
            records=[]
            def revise(context):
                pairs=evidence(q,field,context);records.append(dict(context=context,contradictions=pairs,eligible=len(pairs)>=2))
                if len(pairs)<2 or method=='observe':return None
                if method=='halve':return Scaled(raw,alpha['image']*.5)
                if method=='zero':return Constant(0.)
                if method=='strong_anchor':return GeometricBoost(q)
                if method=='classical_local':return damp_from_evidence(q,field,pairs)
                return regional if method=='oracle_regional' else fine
            result=SpatialSearch(mode='heuristic_envelope',base_weight=1).search(q,field,revision=None if method=='none' else revise,revision_after=128)
            rows.append(dict(case_id=c['id'],map_id=c['map_id'],family=c['family'],method=method,pops=result['heap_pops'],unique=result['unique'],cost_ratio=result['length']/c['optimal_cost'],rebuilds=result['rebuilds'],events=records,seconds=result['total_seconds']))
        print(c['id'],'event-driven correction ceiling',flush=True)
    summary={}
    for method in sorted({r['method'] for r in rows}):
        rr=[r for r in rows if r['method']==method];summary[method]=dict(pops=statistics.mean(r['pops'] for r in rr),unique=statistics.mean(r['unique'] for r in rr),eligible=sum(bool(r['events'] and r['events'][0]['eligible']) for r in rr),rebuilds=sum(r['rebuilds'] for r in rr),gm_cost=math.exp(statistics.mean(math.log(r['cost_ratio']) for r in rr)))
    dump(a.output,dict(scope='Development feedback oracle/controls. First effort event128unique expansions, then at leasttwo observed legal frontier edges with >2 cost-unit predicted triangle violation. One intervention at most. Regional/fine references explicitly oracle, unavailable to actual model. Fine oracle exceeds the expressiveness of the real coarse output.',summary=summary,runs=rows));print(summary)
if __name__=='__main__':main()
