"""Actual response usage and recorded latency, per task including gated no-call VM."""
import argparse,json,statistics
from common import read_cases,dump,RESULTS

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();export=json.loads((RESULTS/'api_export.json').read_text());ledger={r['id']:r for r in export['requests']};groups={}
 for folder in ['heldout_baselines','heldout_cost','heldout_icl','heldout_bounds']:
  for row in read_cases(RESULTS/folder/'responses.json.gz')['runs']:
   kind=row.get('baseline',row.get('representation'));name=folder+'/'+kind;groups.setdefault(name,[]).append(row)
 report={}
 for name,rr in groups.items():
  costs=[];http=[];inputs=[];outputs=[];reasoning=[];prompt=[];client=[];called=0
  for r in rr:
   request=ledger.get(r.get('request_id'));u=r['response'].get('usage',{});costs.append((request.get('estimated_cost_usd') or 0.) if request else 0.);http.append((request.get('latency_seconds') or 0.) if request else 0.);called+=request is not None;inputs.append(u.get('prompt_tokens',0));outputs.append(u.get('completion_tokens',0));reasoning.append((u.get('completion_tokens_details') or {}).get('reasoning_tokens',0))
   if r.get('prompt_processing_seconds') is not None:prompt.append(r['prompt_processing_seconds'])
   if r.get('request_wall_seconds') is not None:client.append(r['request_wall_seconds'])
  report[name]={'queries':len(rr),'called_queries':called,'geometry_skipped':len(rr)-called,'successful_estimated_usd':sum(costs),'mean_usd_per_query_including_skips':statistics.mean(costs),'mean_input_tokens_per_query':statistics.mean(inputs),'mean_output_tokens_per_query':statistics.mean(outputs),'total_reasoning_tokens':sum(reasoning),'mean_http_seconds_per_query_including_skips':statistics.mean(http),'mean_http_seconds_when_called':sum(http)/called if called else None,'median_http_seconds_when_called':statistics.median(v for v in http if v>0) if called else None,'mean_collection_prompt_cpu_seconds':statistics.mean(prompt) if prompt else None,'mean_collection_client_wall_seconds':statistics.mean(client) if client else None}
 dump(a.output,{'scope':'Generation-time usage/HTTP latency from stored genuine responses and ledger; native replay makes zero calls. VM skipped queries have zero model cost/latency. Collector calls ran concurrently across studies, so HTTP figures are descriptive, not an isolated latency race or a measured end-to-end sum. Separate reserved live audit measures actual full online calls. Output includes reasoning, never double counted.','methods':report});print(json.dumps(report,indent=2))
if __name__=='__main__':main()
