"""Development-only ICL teachers; no final query solutions enter prompts."""
import argparse,json,math
from pathlib import Path
from common import read_cases,dump,RESULTS
from prompts_grounded import build
from prompts_spatial import decode
from oracle import remaining_costs,oracle_path
from llmastar.research.spatial_guidance import RegionField,SpatialSearch
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile

def features(q):
    s,t=tuple(q['start']),tuple(q['goal']);distance=max(1.,octile(s,t));walls=q['horizontal_barriers']+q['vertical_barriers']
    try:ratio=CutPotential(q,t).value(s)/distance
    except ValueError:ratio=1.
    width=q['range_x'][1]-q['range_x'][0];height=q['range_y'][1]-q['range_y'][0]
    return [math.log1p(len(walls))/5,min(4.,ratio),abs(s[0]-t[0])/width,abs(s[1]-t[1])/height,width/max(1,height)]

def select_examples(examples,q,k=2):
    query_features=features(q)
    return sorted(examples,key=lambda e:sum((a-b)**2 for a,b in zip(e['features'],query_features)))[:k]

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--responses',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);cases=read_cases(a.cases);families={'open','rooms','tree_maze','u_traps'};chosen=[]
    for c in cases:
        if c['family'] in families and not any(x['family']==c['family'] for x in chosen):chosen.append(c)
    responses={(r['case_id'],r['representation']):r for r in read_cases(a.responses)['runs']};bank=[];contrastive=[]
    for c in chosen:
        q=c['query'];costs,work=remaining_costs(q);path=oracle_path(q,costs);field=RegionField(q,8);pref=list(dict.fromkeys(field.identifier(n) for n in path));other=[r for r in field.regions if r['id'] not in pref and r['sample']]
        other.sort(key=lambda r:-min(math.dist(tuple(r['sample']),n) for n in path));avoid=[r['id'] for r in other[:24]]
        answer={'preferred':pref[:48],'avoid':avoid,'confidence':1.}
        messages,fmt,meta,image=build(q,'structured','corridor',8)
        raw=responses[c['id'],'structured']['response']['choices'][0]['message']['content'];old,_=decode(q,raw,8);teacher,_=decode(q,json.dumps(answer),8)
        baseline=SpatialSearch(mode='envelope',signal='priority').search(q);bad=SpatialSearch(mode='envelope',signal='priority').search(q,old);good=SpatialSearch(mode='envelope',signal='priority').search(q,teacher)
        example={'case_id':c['id'],'map_id':c['map_id'],'family':c['family'],'features':features(q),'input':messages[-1]['content'],'answer':answer,'observed_pops':{'no_advice':baseline['operation'],'previous_model':bad['operation'],'verified_teacher':good['operation']},'teacher_source':'Offline development optimum; allowed in training examples ONLY.'}
        bank.append(example)
        contrastive.append(dict(example,input=example['input']+'\nPrevious model reply:'+raw+'\nActual development search outcomes:'+json.dumps(example['observed_pops'])+'\nCorrect the region assessment using the verified successful route evidence. These example outcomes are not universal guarantees.'))
    dump(out/'examples_bank.json',bank);dump(out/'examples_fixed.json',[bank[0],bank[2]]);dump(out/'examples_contrastive.json',[contrastive[0],contrastive[2]])
    dump(out/'evaluation_cases.json.gz',[c for c in cases if c['map_id'] not in {e['map_id'] for e in bank}]);dump(out/'split.json',{'training_maps':[e['map_id'] for e in bank],'evaluation_maps':[c['map_id'] for c in cases if c['map_id'] not in {e['map_id'] for e in bank}],'policy':'No training geometry in ICL pilot evaluation; held-out examples frozen from these development maps only.'})
    print('Development teacher maps',len(bank),'evaluation maps',len(cases)-len(bank))
if __name__=='__main__':main()
