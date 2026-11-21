"""Credential-safe review of changed/new files, including compressed artifacts."""
import argparse,gzip,hashlib,json,re,subprocess
from pathlib import Path
from common import WORKSPACE,dump
from api import load_key

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();destination=Path(a.output).resolve();paths=subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z'],cwd=WORKSPACE).decode().split('\0');paths+=subprocess.check_output(['git','diff','--name-only','-z','86c8c88..HEAD'],cwd=WORKSPACE).decode().split('\0');paths+=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=WORKSPACE).decode().split('\0');paths=sorted(set(paths));key=load_key();assert key,'Configured key unavailable for actual-key scan';key=key.encode();findings=[];review=[];patterns={'openai_token':rb'sk-(?:proj-)?[A-Za-z0-9_-]{24,}','github_token':rb'gh[pousr]_[A-Za-z0-9]{30,}','huggingface_token':rb'hf_[A-Za-z0-9]{30,}','aws_access_id':rb'AKIA[A-Z0-9]{16}','private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'}
 for name in paths:
  if not name:continue
  path=WORKSPACE/name
  if not path.is_file() or path.resolve()==destination:continue
  raw=path.read_bytes();data=gzip.decompress(raw) if path.suffix=='.gz' else raw
  if key in data:findings.append({'path':name,'kind':'actual_configured_key'})
  for kind,pattern in patterns.items():
   if re.search(pattern,data):findings.append({'path':name,'kind':kind})
  if path.name.startswith('.env') or path.suffix in ['.sqlite','.sqlite3','.db','.pem']:findings.append({'path':name,'kind':'unexpected_credential_or_database_artifact'})
  review.append({'path':name,'bytes':len(raw),'uncompressed_bytes':len(data),'sha256':hashlib.sha256(raw).hexdigest()})
 diff=subprocess.run(['git','diff','--check'],cwd=WORKSPACE,capture_output=True,text=True);assert diff.returncode==0,'Whitespace errors; inspect git diff --check'
 author=subprocess.check_output(['git','var','GIT_AUTHOR_IDENT'],cwd=WORKSPACE,text=True).strip();committer=subprocess.check_output(['git','var','GIT_COMMITTER_IDENT'],cwd=WORKSPACE,text=True).strip();assert author.startswith('Leo <leonard.mueller2005@gmail.com>') and committer.startswith('Leo <leonard.mueller2005@gmail.com>')
 report={'actual_key_value_never_printed_or_persisted':True,'files_scanned':len(review),'findings':findings,'diff_check_passed':True,'author_identity_existing':True,'committer_identity_existing':True,'publication_authorization':'Account verified but matching verified commit email absent; no push.','files':review};dump(destination,report);print('Scanned',len(review),'files; findings',len(findings));assert not findings,'Credential/artifact patterns found; only paths/types saved, never values'
if __name__=='__main__':main()
