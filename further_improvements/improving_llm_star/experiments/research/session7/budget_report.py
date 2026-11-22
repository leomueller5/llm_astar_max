"""Public cost/usage audit: aggregate ledger metadata only, no credential access."""
import argparse,json,collections,statistics
from pathlib import Path
from common import RESULTS,dump
MODEL='gpt-4o-mini-2024-07-18'

def summarize(rows):
 successes=[r for r in rows if r['status']=='success'];counts=collections.Counter(r['status'] for r in rows);tokens=collections.Counter();latencies=[];image=[]
 for r in successes:
  response=r['response'];assert response['model']==MODEL;u=response.get('usage',{});tokens['input']+=u.get('prompt_tokens',0);tokens['output']+=u.get('completion_tokens',0);tokens['cached_input']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0);tokens['reasoning']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
  assert (u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)<=u.get('completion_tokens',0)
  if r.get('latency_seconds') is not None:latencies.append(r['latency_seconds'])
  if any(isinstance(m.get('content'),list) and any(c.get('type')=='image_url' for c in m['content']) for m in r.get('payload',{}).get('messages',[])):image.append(u.get('prompt_tokens',0))
 return {'attempts':len(rows),'statuses':dict(counts),'successful_estimated_usd':sum(r.get('estimated_cost_usd') or 0 for r in successes),'usage':dict(tokens),'http_mean_seconds':statistics.mean(latencies) if latencies else None,'http_median_seconds':statistics.median(latencies) if latencies else None,'image_successful_requests':len(image),'image_prompt_tokens_including_text':sum(image),'all_successful_snapshots_exact':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();data=json.loads((RESULTS/'api_export.json').read_text());rows=data['requests'];s7=[r for r in rows if r.get('metadata',{}).get('session')==7];phases={}
 for phase in sorted({r.get('metadata',{}).get('phase','unknown') for r in s7}):phases[phase]=summarize([r for r in s7 if r.get('metadata',{}).get('phase','unknown')==phase])
 open_requests=[r['id'] for r in rows if r['status'] in ['reserved','pending']]
 report={'scope':'Estimated token-price exposure, not provider invoice. Authoritative cumulative ledger never reset. Ambiguous failures and schema rejection reservations retained conservatively. Reasoning is included in output, never charged twice. Image input billed in reported prompt tokens; API does not separately itemize image token count.','pricing':data['pricing'],'cumulative':data['summary'],'session7':summarize(s7),'by_phase':phases,'open_requests':open_requests,'held_request_statuses':dict(collections.Counter(r['status'] for r in rows if r['status']!='success'))}
 assert data['summary']['accounted_usd']+data['summary']['held_worst_case_usd']<=3.+1e-9
 dump(a.output,report);print(json.dumps({'cumulative':report['cumulative'],'session7':report['session7'],'open_requests':len(open_requests)},indent=2))
if __name__=='__main__':main()
