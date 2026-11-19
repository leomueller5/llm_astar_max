"""Exact residuals on development TEACHER maps only; evaluation maps disjoint."""
import argparse,json,math
from common import read_cases,dump
from prompts_grounded import build
from oracle import remaining_costs,regional_reference
from examples import features

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--split',required=True);p.add_argument('--output',required=True);a=p.parse_args();cases=read_cases(a.cases)
    import pathlib
    training=set(json.loads(pathlib.Path(a.split).read_text())['training_maps']);bank=[]
    for c in cases:
        if c['map_id'] not in training:continue
        q=c['query'];costs,work=remaining_costs(q);f=regional_reference(q,4,costs)
        answer={'predictions':[{'region_id':r['id'],'detour':round(f.values.get(r['id'],(0.,.5,0.))[0],3),'priority':round(f.values.get(r['id'],(0.,.5,0.))[1],3),'confidence':1. if r['id'] in f.values else 0.} for r in f.regions]}
        messages,fmt,meta,img=build(q,'structured','cost',4)
        bank.append({'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'features':features(q),'input':messages[-1]['content']+'\nThis is a verified development example. Predict only the EXTRA cost beyond the given lower bound. A large lower bound does not imply a large EXTRA cost.','answer':answer,'teacher_source':'Offline exact residuals on DEVELOPMENT examples only; never evaluation query costs.'})
    dump(a.output,[bank[0],bank[2]]);print('Cost ICL teachers',[(x['case_id'],x['family']) for x in [bank[0],bank[2]]])
if __name__=='__main__':main()
