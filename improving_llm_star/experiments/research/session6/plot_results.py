"""Standalone scientific PDF/PNG figures from cached frozen results."""
import argparse
import gzip
import json
import math
import textwrap
import os
import tempfile
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'llm-astar-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

NAMES={'original':'Original LLM-A*','robust_original':'Original + engine fixes',
       'astar':'A*','wa2':'Weighted A*','cut2':'Cut, no LLM','cut105':'Cut, w=1.05',
       'hybrid':'LLM-A*-VM','hybrid_quality':'VM, w=1.05','geometry_best':'VM, geometry route',
       'geometry_consensus':'VM, geometry consensus','all_endpoints':'VM, all endpoints',
       'llm_only':'VM, original LLM points'}
COLORS={'original':'#777777','hybrid':'#e67e22','hybrid_quality':'#a84d00',
        'all_endpoints':'#246c9e','geometry_consensus':'#51a1c8','geometry_best':'#92c5de','cut2':'#27446d'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    a.output.mkdir(parents=True);analysis=json.loads((a.root/'final_analysis/analysis.json').read_text())
    raw=json.load(gzip.open(a.root/'final_heldout/results.json.gz','rt'))['runs']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    with PdfPages(a.output/'SESSION6_FIGURES.pdf') as pdf:
        fig=plt.figure(figsize=(8.27,11.69));fig.text(.08,.93,'LLM-A* Research Session 6',fontsize=22,weight='bold')
        fig.text(.08,.89,'Frozen held-out evaluation · 19 November 2026',fontsize=12)
        paragraphs=[
            '200 queries on 20 reserved team maps, plus 20 fresh queries from ten challenging map families. All methods reuse identical raw model responses. Native timing includes fresh query-local preprocessing and excludes API latency.',
            'The verified-macro method improves substantially over the frozen original. Strong matched geometric controls explain most of the gain. A general additional advantage from genuine GPT-4o-mini guidance was not established.',
            'The selected method uses geometry-gated model calls, consensus-supported free endpoints and physically verified macro edges. Its fixed admissible anchor retains a w-suboptimality bound; w=1.05 is the tighter-quality profile.',
            'Runtime confidence intervals resample whole maps. Many related comparisons are shown; isolated nominal intervals should not be treated as proof of general LLM superiority. Memory figures are traced planning allocations, not total native RSS.'
        ]
        y=.82
        for paragraph in paragraphs:
            text='\n'.join(textwrap.wrap(paragraph,89));fig.text(.08,y,text,va='top',linespacing=1.5);y-=.15
        fig.text(.08,.12,'Detailed methods, failed experiments and exact commands: README.md / REPORT.md\nOriginal and historical results remain preserved. No oracle reference entered a paid prompt.',fontsize=10)
        pdf.savefig(fig);plt.close(fig)

        for stratum,title in [('team_maps','200 queries · newly uploaded team maps'),('challenging','20 queries · fresh challenging families')]:
            methods=['original','robust_original','astar','wa2','cut2','hybrid','geometry_consensus','all_endpoints','hybrid_quality','cut105']
            summary=analysis[stratum]['summary']
            fig,axes=plt.subplots(1,2,figsize=(13,5.5))
            y=np.arange(len(methods));color=[COLORS.get(m,'#b7c9d7') for m in methods]
            axes[0].barh(y,[summary[m]['mean_ms'] for m in methods],color=color)
            axes[0].set_yticks(y,[NAMES[m] for m in methods]);axes[0].invert_yaxis();axes[0].set_xscale('log')
            axes[0].set_xlabel('Mean query CPU time (ms, log scale)');axes[0].set_title('Complete local computation, API excluded')
            axes[1].barh(y,[summary[m]['mean_total_heap_pops'] for m in methods],color=color)
            axes[1].set_yticks(y,[]);axes[1].invert_yaxis();axes[1].set_xlabel('Mean total heap pops, preprocessing included')
            axes[1].set_title('Separate untimed heap audit')
            fig.suptitle(title,fontsize=14);fig.tight_layout();fig.savefig(a.output/(stratum+'_runtime_work.png'),dpi=220);pdf.savefig(fig);plt.close(fig)

        fig,axes=plt.subplots(1,2,figsize=(12,4.8))
        for ax,(stratum,title) in zip(axes,[('team_maps','Team maps'),('challenging','Challenging families')]):
            methods=['geometry_best','geometry_consensus','all_endpoints','cut2']
            for i,m in enumerate(methods):
                stat=analysis[stratum]['comparisons'][m]['total_heap_pops'];value=stat['ratio'];lo,hi=stat['ci95']
                if value is not None and lo is not None and hi is not None:
                    ax.errorbar(value,i,xerr=[[value-lo],[hi-value]],fmt='o',capsize=4,color=COLORS.get(m,'black'))
            ax.axvline(1,color='black',linestyle='--',linewidth=1)
            ax.set_yticks(range(len(methods)),[NAMES[m] for m in methods]);ax.invert_yaxis()
            ax.set_xlabel('VM / matched control: total heap pops');ax.set_title(title)
        fig.suptitle('Paired whole-map bootstrap: nominal 95% intervals',fontsize=13)
        fig.tight_layout();fig.savefig(a.output/'paired_llm_contribution.png',dpi=220);pdf.savefig(fig);plt.close(fig)

        fig,axes=plt.subplots(1,2,figsize=(12,4.7))
        for ax,(stratum,title) in zip(axes,[('team_maps','Team maps'),('challenging','Challenging families')]):
            for method in ['original','hybrid','hybrid_quality','all_endpoints','cut105']:
                values=sorted(r['cost_ratio'] for r in raw if r['rep']==-1 and r['valid'] and r['method']==method and ((r['family']=='team_random_walls')==(stratum=='team_maps')))
                ax.step(values,np.arange(1,len(values)+1)/len(values),where='post',label=NAMES[method],color=COLORS.get(method))
            ax.axvline(1.05,color='#ad3333',linestyle=':',linewidth=1)
            ax.set_xlabel('Path cost / optimal A* cost');ax.set_ylabel('Fraction of valid queries');ax.set_title(title);ax.set_xlim(.995,1.46);ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(a.output/'path_quality_cdf.png',dpi=220);pdf.savefig(fig);plt.close(fig)

        memory_path=a.root/'memory_profiles/memory.json'
        if memory_path.exists():
            memory=json.loads(memory_path.read_text());methods=['original','robust_original','astar','cut2','hybrid','all_endpoints']
            fig,ax=plt.subplots(figsize=(10,5))
            values=[[r['peak_traced_bytes']/1024 for r in memory['runs'] if r['method']==m and r['peak_traced_bytes'] is not None] for m in methods]
            ax.boxplot(values,tick_labels=[NAMES[m] for m in methods]);ax.set_yscale('log');ax.set_ylabel('Peak traced KiB (log scale)')
            ax.set_title('Planning + diagnostics allocations on 14 fixed cases; not full native RSS')
            ax.tick_params(axis='x',labelrotation=18);fig.tight_layout();fig.savefig(a.output/'traced_memory.png',dpi=220);pdf.savefig(fig);plt.close(fig)

        cases={c['id']:c for c in json.load(gzip.open(a.root/'heldout_all.json.gz','rt'))}
        responses=json.load(gzip.open(a.root/'heldout_hybrid/responses.json.gz','rt'))['runs']
        example=next(r for r in responses if r.get('api_calls')==1)
        cid=example['case_id'];q=cases[cid]['query'];paths=json.load(gzip.open(a.root/'final_heldout/paths.json.gz','rt'))
        fig,ax=plt.subplots(figsize=(11,7))
        for y,lo,hi in q['horizontal_barriers']:ax.plot([lo,hi],[y,y],color='black',linewidth=2)
        for x,lo,hi in q['vertical_barriers']:ax.plot([x,x],[lo,hi],color='black',linewidth=2)
        for method in ['original','hybrid','all_endpoints']:
            row=next(r for r in paths if r['case_id']==cid and r['method']==method)
            if row['valid']:
                path=row['path'];ax.plot([p[0] for p in path],[p[1] for p in path],label=NAMES[method],color=COLORS.get(method),alpha=.8)
        ax.scatter(*q['start'],marker='*',s=130,color='green',label='Start');ax.scatter(*q['goal'],marker='*',s=130,color='red',label='Goal')
        ax.set_xlim(q['range_x']);ax.set_ylim(q['range_y']);ax.set_aspect('equal');ax.legend()
        ax.set_title(cid+': first model-invoked test case, selected without performance filtering')
        fig.tight_layout();fig.savefig(a.output/'fixed_real_guidance_example.png',dpi=220);pdf.savefig(fig);plt.close(fig)
    print(a.output/'SESSION6_FIGURES.pdf')


if __name__=='__main__':main()
