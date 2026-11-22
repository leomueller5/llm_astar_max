"""Single-session $3 cap, crash-safe reservations and immediate response caching.

Only the user-approved exact snapshot and public OpenAI host are allowed. No SDK
retries. Unknown/failed calls retain their full reservation, including after a
process crash. Credentials exist only in process memory and HTTP headers.
"""
import argparse,hashlib,json,os,sqlite3,time,urllib.request,urllib.error,uuid
from pathlib import Path
from datetime import datetime,timezone

MODEL='gpt-4o-mini-2024-07-18'
CAP=3_000_000_000  # nanoUSD; integer arithmetic throughout
INPUT=150;CACHED_INPUT=75;OUTPUT=600  # nanoUSD/token; official Nov18 price
CONTEXT=128000
ROOT=Path(__file__).resolve().parents[3]
ARTIFACT=ROOT/'experiments/results/research_session5'
DB=ARTIFACT/'api_ledger.sqlite3'
PRICING={'model':MODEL,'input_usd_per_million':.15,'cached_input_usd_per_million':.075,'output_usd_per_million':.60,'context_tokens':CONTEXT,'verified_utc':'2026-11-18','source':'https://developers.openai.com/api/docs/models/gpt-4o-mini','reasoning_billing':'Reasoning tokens, if reported, are a subset of completion tokens; never double charged.'}

class BudgetExceeded(RuntimeError):pass
class RequestUnavailable(RuntimeError):pass

def now():return datetime.now(timezone.utc).isoformat()

def load_key():
    key=os.environ.get('OPENAI_API_KEY')
    if not key:
        # Explicitly authorized by user. Never return text to a log or traceback.
        try:lines=Path('~/.config/llm-astar/.env').expanduser().read_text().splitlines()
        except OSError:raise RequestUnavailable('Credential configuration unavailable') from None
        for line in lines:
            line=line.strip().removeprefix('export ')
            if line.startswith('OPENAI_API_KEY='):
                key=line.split('=',1)[1].strip().strip('\"\'');break
    if not key:raise RequestUnavailable('Credential variable unavailable')
    return key

class Ledger:
    def __init__(self,path=DB):
        path=Path(path);self.directory=path.parent;path.parent.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(path,timeout=30)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, created TEXT, payload TEXT, metadata TEXT, status TEXT, reserve INTEGER, charged INTEGER, response TEXT, latency REAL, error TEXT)');self.db.commit()
        archive=self.directory/'api_export.json'
        if archive.is_file() and not self.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]:
            data=json.loads(archive.read_text())
            if data.get('pricing',{}).get('model')!=MODEL:raise RuntimeError('Archived model policy mismatch')
            for r in data.get('requests',[]):
                reserve=r.get('reserved_nano',round(r['reserved_usd']*1e9));charged=r.get('charged_nano')
                if charged is None and r.get('estimated_cost_usd') is not None:charged=round(r['estimated_cost_usd']*1e9)
                self.db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)',(r['id'],r['created'],json.dumps(r['payload']),json.dumps(r['metadata']),r['status'],reserve,charged,json.dumps(r['response']) if r.get('response') else None,r.get('latency_seconds'),r.get('error')))
            self.db.commit()
    def summary(self):
        rows=self.db.execute('SELECT status,reserve,charged,response FROM requests').fetchall();usage={'prompt_tokens':0,'completion_tokens':0,'reasoning_tokens':0,'cached_input_tokens':0}
        for status,reserve,charged,response in rows:
            if response:
                u=json.loads(response).get('usage',{});usage['prompt_tokens']+=u.get('prompt_tokens',0);usage['completion_tokens']+=u.get('completion_tokens',0);usage['reasoning_tokens']+=u.get('completion_tokens_details',{}).get('reasoning_tokens',0);usage['cached_input_tokens']+=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        spent=sum(r[2] or 0 for r in rows);held=sum(r[1] for r in rows if r[2] is None)
        return dict(cap_usd=CAP/1e9,accounted_usd=spent/1e9,held_worst_case_usd=held/1e9,remaining_authorized_usd=(CAP-spent-held)/1e9,attempts=len(rows),successes=sum(r[0]=='success' for r in rows),**usage)
    def reserve(self,identifier,payload,metadata):
        # Full context-window input cost is a conservative upper bound independent
        # of local tokenizers/server message framing. Output cap includes reasoning.
        amount=CONTEXT*INPUT+payload['max_completion_tokens']*OUTPUT
        self.db.execute('BEGIN IMMEDIATE')
        existing=self.db.execute('SELECT status,response FROM requests WHERE id=?',(identifier,)).fetchone()
        if existing:
            self.db.rollback()
            if existing[0]=='success':return json.loads(existing[1])
            raise RequestUnavailable('Previous attempt unresolved/failed; no implicit retry')
        used=self.db.execute('SELECT COALESCE(SUM(COALESCE(charged,reserve)),0) FROM requests').fetchone()[0]
        if used+amount>CAP:self.db.rollback();raise BudgetExceeded('Next worst-case request exceeds $3 cap')
        self.db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)',(identifier,now(),json.dumps(payload),json.dumps(metadata),'reserved',amount,None,None,None,None));self.db.commit();return None
    def finish(self,identifier,response,latency):
        # Cache first, before any accounting logic. Crash leaves a held reservation.
        raw=json.dumps(response);self.db.execute('UPDATE requests SET response=?,latency=?,status=? WHERE id=?',(raw,latency,'cached_pending_accounting',identifier));self.db.commit()
        u=response.get('usage',{});p=u.get('prompt_tokens');o=u.get('completion_tokens')
        if not isinstance(p,int) or not isinstance(o,int) or p<0 or o<0:return
        cached=min(p,u.get('prompt_tokens_details',{}).get('cached_tokens',0));amount=(p-cached)*INPUT+cached*CACHED_INPUT+o*OUTPUT
        limit=self.db.execute('SELECT reserve FROM requests WHERE id=?',(identifier,)).fetchone()[0]
        if amount>limit:raise RuntimeError('Usage exceeds conservative reservation; stop all requests')
        self.db.execute('UPDATE requests SET status=?,charged=? WHERE id=?',('success',amount,identifier));self.db.commit()
    def fail(self,identifier,error,latency):
        self.db.execute('UPDATE requests SET status=?,error=?,latency=? WHERE id=?',('failed_conservative_hold',error,latency,identifier));self.db.commit()
    def export(self,path=None):
        rows=[]
        for rid,created,payload,metadata,status,reserve,charged,response,latency,error in self.db.execute('SELECT * FROM requests ORDER BY created'):
            rows.append(dict(id=rid,created=created,payload=json.loads(payload),metadata=json.loads(metadata),status=status,reserved_nano=reserve,charged_nano=charged,reserved_usd=reserve/1e9,estimated_cost_usd=None if charged is None else charged/1e9,response=json.loads(response) if response else None,latency_seconds=latency,error=error))
        target=Path(path or self.directory/'api_export.json');target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps({'pricing':PRICING,'summary':self.summary(),'requests':rows},indent=2)+'\n');temp.replace(target)

class BudgetClient:
    def __init__(self,ledger=None,transport=None):self.ledger=ledger or Ledger();self.transport=transport
    def chat(self,messages,metadata,max_tokens=1024,seed=20261118,temperature=0):
        if not 1<=max_tokens<=16384:raise ValueError('Invalid completion cap')
        if not isinstance(messages,list) or any(set(m)-{'role','content'} or m['role'] not in ['system','user','assistant'] or not isinstance(m['content'],str) for m in messages):raise ValueError('Text messages only; no tools/remote content')
        payload=dict(model=MODEL,messages=messages,max_completion_tokens=max_tokens,temperature=temperature,seed=seed)
        identifier=hashlib.sha256(json.dumps({'payload':payload,'metadata':metadata},sort_keys=True).encode()).hexdigest()
        cached=self.ledger.reserve(identifier,payload,metadata)
        if cached is not None:return cached,identifier,True
        started=time.perf_counter()
        try:
            if self.transport:response=self.transport(payload)
            else:
                key=load_key();request=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(request,timeout=60) as stream:raw=stream.read()
                # No credential should occur in provider data; redact defensively.
                response=json.loads(raw.decode().replace(key,'[REDACTED]'))
            self.ledger.finish(identifier,response,time.perf_counter()-started);self.ledger.export()
            return response,identifier,False
        except Exception as exc:
            kind=('HTTP_'+str(exc.code)) if isinstance(exc,urllib.error.HTTPError) else type(exc).__name__
            self.ledger.fail(identifier,kind,time.perf_counter()-started);self.ledger.export()
            raise RequestUnavailable('Request failed safely: '+kind) from None

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','models','probe']);a=p.parse_args();ledger=Ledger()
    if a.action=='status':ledger.export();print(json.dumps(ledger.summary()));return
    if a.action=='models':
        key=load_key()
        try:
            req=urllib.request.Request('https://api.openai.com/v1/models',headers={'Authorization':'Bearer '+key})
            with urllib.request.urlopen(req,timeout=30) as stream:ids={r['id'] for r in json.load(stream)['data']}
            result={'authenticated':True,'requested_model':MODEL,'exact_snapshot_available':MODEL in ids,'historical_o4_available':'o4-mini' in ids,'verified_utc':now(),'paid_requests':0}
        except Exception as exc:result={'authenticated':False,'error':('HTTP_'+str(exc.code)) if isinstance(exc,urllib.error.HTTPError) else type(exc).__name__,'paid_requests':0}
        (ARTIFACT/'model_availability.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return
    try:
        r,rid,cached=BudgetClient(ledger).chat([{'role':'user','content':'Reply only OK.'}],{'phase':'connectivity','prompt_version':'probe_v1'},max_tokens=8)
        print(json.dumps({'connected':True,'model':r.get('model'),'response_cached':cached,'usage':r.get('usage'),'budget':ledger.summary()}))
    except RequestUnavailable as exc:print(str(exc))
if __name__=='__main__':main()
