"""Fixed-hash map illustrations, not selected favorable benchmark cases."""
import argparse,hashlib,os,tempfile
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'llm-astar-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import Normalize
from common import RESULTS,read_cases,dump
from native_benchmark import ALPHA,load_costs
from prompts_spatial import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cases=read_cases(RESULTS/'heldout_main.json.gz');paths={(r['case_id'],r['method']):r for r in read_cases(RESULTS/'final_native/paths.json.gz') if r['seed']==0};traces={(r['case_id'],r['method']):r['trace'] for r in read_cases(RESULTS/'final_native/traces.json.gz')};cost=load_costs(RESULTS/'heldout_cost/responses.json.gz');selected=[]
 for family in ['tree_maze','nested']:
  c=min((c for c in cases if c['family']==family),key=lambda c:hashlib.sha256(('s7figure'+c['id']).encode()).hexdigest());selected.append(c['id']);q=c['query'];field,_=decode(q,cost[c['id'],'image']['response']['choices'][0]['message']['content'],4,'cost');values={r['id']:ALPHA*field.values.get(r['id'],(0.,.5,0.))[0]*field.values.get(r['id'],(0.,.5,0.))[2] for r in field.regions};norm=Normalize(0,max(1e-9,max(values.values())));fig,axes=plt.subplots(1,3,figsize=(15,5.3))
  for ax,method,title in zip(axes,['astar_cut','rh_image105','vm_geo105'],['Optimal cut A*','LLM-RH* image1.05','Geometric VM1.05']):
   for r in field.regions:
    lo,hi=r['bounds'];ax.add_patch(Rectangle((lo[0]-.5,lo[1]-.5),hi[0]-lo[0]+1,hi[1]-lo[1]+1,facecolor=plt.cm.YlOrRd(norm(values[r['id']])),alpha=.25,edgecolor='#aaaaaa',lw=.35))
   for y,lo,hi in q['horizontal_barriers']:ax.plot([lo,hi],[y,y],color='black',lw=.6)
   for x,lo,hi in q['vertical_barriers']:ax.plot([x,x],[lo,hi],color='black',lw=.6)
   trace=traces.get((c['id'],method),[])
   if trace:
    pts=[r['node'] for r in trace];ax.scatter([n[0] for n in pts],[n[1] for n in pts],s=2,c='#326b99',alpha=.16,rasterized=True)
   row=paths.get((c['id'],method));path=row.get('path',[]) if row else []
   if path:ax.plot([n[0] for n in path],[n[1] for n in path],c='#b1262b',lw=1.1)
   for name,color in [('start','green'),('goal','purple')]:ax.scatter(*q[name],c=color,s=25,zorder=5);ax.annotate(name[0].upper(),q[name],fontsize=8,color=color)
   ratio=row['length']/c['optimal_cost'] if row and row['valid'] else None
   ax.set(title=title+'\n'+(f'cost/opt={ratio:.4f}; expanded={len(trace)}' if ratio is not None else 'No completed audited path'),xlim=q['range_x'],ylim=q['range_y'],xlabel='x (right)',ylabel='y (up)');ax.set_aspect('equal')
  fig.suptitle(c['id']+' / '+family+': blue=expanded labels, red=returned path. Heat=uncapped calibrated model residual; controls ignore heat.',fontsize=10);fig.tight_layout();fig.savefig(out/(family+'.png'),dpi=170,bbox_inches='tight');fig.savefig(out/(family+'.pdf'),bbox_inches='tight');plt.close(fig)
 dump(out/'selection.json',{'scope':'One primary tree-maze and nested-obstacle query chosen by fixed ID hash, not favorable performance. Analysis-only path overlays never enter model inputs.','cases':selected})
if __name__=='__main__':main()
