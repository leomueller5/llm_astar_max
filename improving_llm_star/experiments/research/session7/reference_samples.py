"""Offline evaluation targets, computed after the algorithm/prompt freeze."""
import argparse,math
from common import read_cases,dump
from oracle import remaining_costs,oracle_path,anchor
from llmastar.research.spatial_guidance import RegionField

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output',required=True);a=p.parse_args();rows=[]
    for c in read_cases(a.cases):
        q=c['query'];costs,work=remaining_costs(q);assert abs(costs[tuple(q['start'])]-c['optimal_cost'])<1e-7
        f=RegionField(q,4);h=anchor(q,'cut');path=oracle_path(q,costs)
        rows.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'reference_work':work,'optimal_cost':c['optimal_cost'],'samples':[{'region_id':r['id'],'point':r['sample'],'remaining_cost':costs.get(tuple(r['sample'])) if r['sample'] else None,'geometric_lower_bound':h(tuple(r['sample'])) if r['sample'] and math.isfinite(h(tuple(r['sample']))) else None} for r in f.regions], 'canonical_optimal_path':path})
        print(c['id'],'independent Dijkstra reference checked',flush=True)
    dump(a.output,{'scope':'Offline target/reference work, never part of inference or prompts. Full reverse-Dijkstra confirms each A* optimal reference cost; samples and canonical paths used only for analysis/oracle figures.','runs':rows})
if __name__=='__main__':main()
