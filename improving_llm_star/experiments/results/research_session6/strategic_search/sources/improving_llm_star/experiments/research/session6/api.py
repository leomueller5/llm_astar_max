"""Session 6: bounded retries against the unchanged cumulative Session 5 ledger.

Each transport attempt reserves its own worst-case exposure. Ambiguous failures
remain charged at that upper bound; historical exports are never overwritten.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'session5'))
from api_budget import (Ledger, BudgetClient, RequestUnavailable, MODEL, DB,
                        load_key, now)

ARTIFACT = Path(__file__).resolve().parents[3] / 'experiments/results/research_session6'


class CumulativeLedger(Ledger):
    def __init__(self, path=DB, export_path=None):
        super().__init__(path)
        self.export_path = Path(export_path or ARTIFACT / 'api_export.json')
        # Restore Session 6 additions too when reproducing from portable exports.
        if self.export_path.exists():
            data = json.loads(self.export_path.read_text())
            for r in data.get('requests', []):
                self.db.execute('INSERT OR IGNORE INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (r['id'], r['created'], json.dumps(r['payload']), json.dumps(r['metadata']),
                     r['status'], r['reserved_nano'], r['charged_nano'],
                     json.dumps(r['response']) if r.get('response') else None,
                     r.get('latency_seconds'), r.get('error')))
            self.db.commit()

    def export(self, path=None):
        super().export(path or self.export_path)


class RetryClient:
    def __init__(self, ledger=None, transport=None, attempts=2, backoff=.75):
        if not 1 <= attempts <= 3 or backoff < 0:
            raise ValueError('At most three separately reserved attempts')
        self.ledger = ledger or CumulativeLedger()
        self.transport = transport or self._transport
        self.attempts = attempts
        self.backoff = backoff
        self.last_error = None
        self.consecutive_failures = 0

    def _transport(self, payload):
        key = load_key()
        request = urllib.request.Request('https://api.openai.com/v1/chat/completions',
            data=json.dumps(payload).encode(),
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
            method='POST')
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.loads(response.read().decode().replace(key, '[REDACTED]'))
        except urllib.error.HTTPError as exc:
            self.last_error = {'kind': 'HTTPError', 'status': exc.code,
                               'retryable': exc.code in [408, 429] or exc.code >= 500}
            raise
        except Exception as exc:
            reason = getattr(exc, 'reason', None)
            self.last_error = {'kind': type(exc).__name__,
                               'reason_kind': type(reason).__name__,
                               'errno': getattr(reason, 'errno', None),
                               'retryable': True}
            raise

    def _structured_chat(self,messages,metadata,max_tokens,response_format):
        if not 1<=max_tokens<=16384 or not isinstance(response_format,dict) or response_format.get('type')!='json_schema':
            raise ValueError('Invalid structured request')
        if not isinstance(messages,list) or any(set(m)-{'role','content'} or m['role'] not in ['system','user','assistant'] or not isinstance(m['content'],str) for m in messages):
            raise ValueError('Text messages only')
        payload={'model':MODEL,'messages':messages,'max_completion_tokens':max_tokens,
                 'seed':20261118,'temperature':0,'response_format':response_format}
        identifier=hashlib.sha256(json.dumps({'payload':payload,'metadata':metadata},sort_keys=True).encode()).hexdigest()
        cached=self.ledger.reserve(identifier,payload,metadata)
        if cached is not None:
            return cached,identifier,True
        started=time.perf_counter()
        try:
            response=self.transport(payload)
            self.ledger.finish(identifier,response,time.perf_counter()-started)
            self.ledger.export()
            return response,identifier,False
        except Exception as exc:
            kind='HTTP_'+str(exc.code) if isinstance(exc,urllib.error.HTTPError) else type(exc).__name__
            self.ledger.fail(identifier,kind,time.perf_counter()-started);self.ledger.export()
            raise RequestUnavailable('Structured request failed safely: '+kind) from None

    def chat(self, messages, metadata, max_tokens=512,response_format=None):
        if self.consecutive_failures >= 3:
            raise RequestUnavailable('Circuit open after three failed logical requests')
        client = BudgetClient(self.ledger, self.transport)
        for attempt in range(self.attempts):
            try:
                tagged=dict(metadata,session=6,retry_attempt=attempt)
                result = self._structured_chat(messages,tagged,max_tokens,response_format) if response_format else client.chat(messages,tagged,max_tokens=max_tokens)
                self.consecutive_failures = 0
                return result
            except RequestUnavailable:
                if self.last_error and not self.last_error.get('retryable'):
                    break
                if attempt + 1 < self.attempts:
                    time.sleep(self.backoff * 2 ** attempt)
        self.consecutive_failures += 1
        raise RequestUnavailable('Bounded attempts exhausted; reservations retained')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'models', 'probe'])
    args = parser.parse_args()
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    ledger = CumulativeLedger()
    if args.action == 'models':
        try:
            key = load_key()
            request = urllib.request.Request('https://api.openai.com/v1/models',
                headers={'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(request, timeout=20) as response:
                ids = {m['id'] for m in json.load(response)['data']}
            result = {'authenticated': True, 'exact_snapshot_available': MODEL in ids,
                      'model': MODEL, 'time': now(), 'paid_requests': 0}
        except Exception as exc:
            result = {'authenticated': False, 'error_kind': type(exc).__name__,
                      'paid_requests': 0}
        (ARTIFACT / 'model_availability.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    elif args.action == 'probe':
        client = RetryClient(ledger)
        try:
            response, _, cached = client.chat([{'role':'user','content':'Reply OK.'}],
                {'phase':'connectivity','prompt_version':'session6_probe_v1'}, max_tokens=8)
            print(json.dumps({'connected':True,'model':response.get('model'),
                              'usage':response.get('usage'),'cached':cached}))
        except RequestUnavailable:
            print(json.dumps({'connected':False,'diagnostic':client.last_error}))
    ledger.export()
    print(json.dumps(ledger.summary()))


if __name__ == '__main__':
    main()
