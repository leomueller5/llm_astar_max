"""Offline cumulative expenditure and original waypoint-activity audit."""
import argparse,gzip,json,statistics
from pathlib import Path
from collections import Counter

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    ledger=json.loads((root/'api_export.json').read_text());req=ledger['requests']
    old=json.loads((root.parent/'research_session5/api_export.json').read_text());old_ids={r['id'] for r in old['requests']}
    new=[r for r in req if r['id'] not in old_ids]
    def aggregate(rows):
        usage=[r['response'].get('usage',{}) for r in rows if r.get('response')]
        return {'attempts':len(rows),'successes':sum(r['status']=='success' for r in rows),
            'charged_usd':sum(r['charged_nano'] or 0 for r in rows)/1e9,
            'held_usd':sum(r['reserved_nano'] for r in rows if r['status']!='success')/1e9,
            'input_tokens':sum(u.get('prompt_tokens',0) for u in usage),
            'output_tokens':sum(u.get('completion_tokens',0) for u in usage),
            'reasoning_tokens_in_output':sum((u.get('completion_tokens_details') or {}).get('reasoning_tokens',0) for u in usage),
            'actual_response_models':dict(Counter(r['response'].get('model') for r in rows if r.get('response')))}
    budget={'cumulative':ledger['summary'],'session6_only':aggregate(new),'historical_session5':aggregate(old['requests']),
        'pricing':ledger['pricing'],'new_ambiguous_failures':[{'id':r['id'],'reserved_usd':r['reserved_nano']/1e9,'error_type':(r.get('error') or '').split(':')[0]} for r in new if r['status']!='success'],
        'note':'Reasoning tokens are included in billed output tokens, not added a second time. All unknown failures remain held, including eight historical and one new attempt. No budget reset or refund assumption.'}
    (root/'BUDGET_REPORT.json').write_text(json.dumps(budget,indent=2))
    raw=json.load(gzip.open(root/'final_heldout/results.json.gz','rt'))['runs'];orig=[r for r in raw if r['method']=='original' and r['rep']==-1]
    durations=[s['active_pops'] for r in orig for s in r.get('switches',[])];dup=[r.get('duplicate_pops',r.get('duplicates',0)) for r in orig]
    activity={'scope':'All frozen-original waypoint-switch events, including the switch to final goal; counters are original CLOSED appends/queue pops, not distinct states.','queries':len(orig),'switch_events':len(durations),
        'median_active_pops':statistics.median(durations) if durations else None,'mean_active_pops':statistics.mean(durations) if durations else None,
        'fraction_at_most_one':sum(x<=1 for x in durations)/len(durations) if durations else None,
        'fraction_below_30':sum(x<30 for x in durations)/len(durations) if durations else None,
        'mean_duplicate_pops':statistics.mean(dup),'pops_definition':'Original operation field equals every appended CLOSED entry, including duplicates. Separate heap audit also counts pushes and heapify calls.'}
    (root/'WAYPOINT_ACTIVITY.json').write_text(json.dumps(activity,indent=2));print(json.dumps(budget,indent=2));print(json.dumps(activity,indent=2))
if __name__=='__main__':main()
