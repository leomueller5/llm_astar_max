"""Canonical geometry disjointness, not just differently named random seeds."""
import argparse,gzip,json,hashlib
from pathlib import Path
from common import ROOT,RESULTS,read_cases,dump

def fingerprint(q):
    x={k:q[k] for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']}
    for k in ['horizontal_barriers','vertical_barriers']:x[k]=sorted(x[k])
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def prior_geometries(exclude_session7=True):
    result={};files=[];names=['development','validation','heldout','fresh','maps','cases','team','synthetic']
    for folder in [ROOT/'experiments/results',ROOT/'dataset']:
        for p in folder.rglob('*.json*'):
            if exclude_session7 and 'research_session7' in p.parts:continue
            if p.suffix not in ['.json','.gz'] or not any(t in p.name.lower() for t in names):continue
            if any(t in p.name.lower() for t in ['responses','results','checkpoint','api_export','analysis','manifest']):continue
            if p.stat().st_size>20_000_000:continue
            try:
                with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:data=json.load(f)
            except (ValueError,OSError,UnicodeDecodeError):continue
            before=len(result)
            def visit(value,depth=0):
                if depth>6:return
                if isinstance(value,dict):
                    if all(k in value for k in ['range_x','range_y','horizontal_barriers','vertical_barriers']):
                        try:result.setdefault(fingerprint(value),str(p))
                        except (TypeError,ValueError):pass
                        return
                    for k,v in value.items():
                        if k not in ['response','payload','messages','path','trace']:visit(v,depth+1)
                elif isinstance(value,list):
                    for v in value:visit(v,depth+1)
            visit(data)
            if len(result)>before:files.append(str(p))
    return result,files

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--require-disjoint',action='store_true');a=p.parse_args();prior,files=prior_geometries();training={};report={}
    for name in ['development.json.gz','validation.json.gz']:
        path=RESULTS/name
        if path.exists():
            for c in read_cases(path):training.setdefault(fingerprint(c['query']),[]).append(c['id'])
    for name in a.cases:
        cases=read_cases(name);hashes={};seen=[]
        for c in cases:hashes.setdefault(fingerprint(c['query']),[]).append(c['id'])
        for key,ids in hashes.items():
            if key in prior or (a.require_disjoint and key in training):seen.append({'case_ids':ids,'prior_source':prior.get(key),'session7_training_ids':training.get(key,[])})
        report[name]={'cases':len(cases),'distinct_geometries':len(hashes),'within_file_duplicate_geometry_clusters':[v for v in hashes.values() if len(v)>1],'overlap':seen}
    dump(a.output,{'known_prior_geometries':len(prior),'sources':files,'files':report,'scope':'Canonical sorted geometry fingerprint excludes start/goal. Statistical resampling must cluster equal geometries, regardless of map IDs. Prior scan covers all recognizably named map/case datasets, omitting model messages and analysis outputs.'})
    print(json.dumps({k:{f:v for f,v in d.items() if f not in ['within_file_duplicate_geometry_clusters','overlap']}|{'overlap_count':len(d['overlap'])} for k,d in report.items()},indent=2))
    if a.require_disjoint and any(d['overlap'] for d in report.values()):raise SystemExit('Held-out geometry leakage detected')
if __name__=='__main__':main()
