"""Read-only local source/artifact safety audit. Never emits credential bytes."""
import argparse,gzip,hashlib,json,re,subprocess,sys
from pathlib import Path
from api import load_key

def git(*args):return subprocess.check_output(['git',*args]).decode().strip()
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    key=load_key().encode()
    paths=set(git('diff','--name-only','31f2798','--').splitlines())
    paths.update(git('ls-files','--others','--exclude-standard').splitlines())
    matches=[];decompressed=0;scanned=0;size=0;artifacts=[]
    patterns=[re.compile(rb'sk-(?:proj-)?[A-Za-z0-9_-]{24,}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'AKIA[0-9A-Z]{16}')]
    for name in sorted(paths):
        path=Path(name)
        if not path.is_file():continue
        raw=path.read_bytes();scanned+=1;size+=len(raw)
        variants=[raw]
        if path.suffix=='.gz':variants.append(gzip.decompress(raw));decompressed+=1
        for data in variants:
            if key and key in data:matches.append({'file':name,'kind':'actual_configured_credential'})
            if any(p.search(data) for p in patterns):matches.append({'file':name,'kind':'generic_secret_pattern'})
        if path.suffix in ['.sqlite3','.db','.env'] or any(x in path.parts for x in ['__pycache__','.venv']):artifacts.append(name)
    manifest=json.loads(Path('improving_llm_star/experiments/results/research_session6/frozen_manifest.json').read_text())
    hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected for name,expected in manifest['sources'].items()}
    ancestors={ref:subprocess.run(['git','merge-base','--is-ancestor',ref,'HEAD']).returncode==0 for ref in ['572603d','2ed7763','1020fe0','31f2798']}
    result={'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','get-url','origin'),
        'main_unchanged':git('rev-parse','main')=='66baa31d2fc2b658b501dcd4b34e09d31af66cb4',
        'preserved_contribution_ancestors':ancestors,'scanned_files':scanned,'scanned_bytes':size,'gzip_payloads_scanned':decompressed,
        'secret_findings':matches,'unwanted_artifacts':artifacts,'frozen_source_checks':hashes,
        'git_diff_check_clean':subprocess.run(['git','diff','--check'],stdout=subprocess.DEVNULL).returncode==0,
        'identity':{'name':git('config','user.name'),'email':git('config','user.email')},
        'publication_decision':'Do not push: configured author email cannot be verified as associated with authenticated GitHub account. Identity and authentication remain unchanged.'}
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    if matches or artifacts or not all(hashes.values()) or not all(ancestors.values()) or not result['main_unchanged'] or not result['git_diff_check_clean']:sys.exit(1)
if __name__=='__main__':main()
