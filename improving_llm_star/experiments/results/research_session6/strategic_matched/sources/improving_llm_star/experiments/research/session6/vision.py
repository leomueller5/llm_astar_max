"""Matched text/image geometric candidates. Draws no solved/reference route."""
import base64
import io
import json
import os
from time import perf_counter

os.environ.setdefault('MPLBACKEND','Agg')
from hybrid import SYSTEM
from strategic import schema


def visual_input(query,proposal,image=True):
    tick=perf_counter()
    lookup={f'P{i}':p for i,p in enumerate(proposal['points'].values())}
    obstacles={f'P{i}':k for i,k in enumerate(proposal['points'])}
    payload={'map':query,'candidate_points':lookup,'candidate_obstacles':obstacles,
             'geometric_proposed_route':proposal['geometry_best'],
             'geometric_route_conflicts':proposal['candidates'][0]['conflicts']}
    prompt=('Choose a compact ordered route of at most EIGHT green candidate IDs '
        'from S to G. The orange dashed geometric proposal may cross walls; '
        'correct its strategic bypasses. Account for connected obstacles and '
        'downstream walls. Every black segment, including its endpoints, is '
        'blocked. Green candidates are already free integer cells. Do not visit '
        'irrelevant candidates or both sides of a wall unnecessarily. The route '
        'may pass around obstacles between candidates; A* constructs unit moves. '
        'Return JSON targets only. No solved reference path has been supplied.\n')
    content=[{'type':'text','text':prompt+json.dumps(payload,separators=(',',':'))}]
    png=None
    if image:
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(10.1,6.1),dpi=100)
        for y,a,b in query['horizontal_barriers']:
            ax.plot([a,b],[y,y],color='black',linewidth=2.8,solid_capstyle='round')
        for x,a,b in query['vertical_barriers']:
            ax.plot([x,x],[a,b],color='black',linewidth=2.8,solid_capstyle='round')
        route=proposal['geometry_best']
        ax.plot([p[0] for p in route],[p[1] for p in route],color='darkorange',linestyle='--',linewidth=1.,alpha=.6)
        for identifier,p in lookup.items():
            ax.scatter(*p,s=15,color='green',zorder=4)
            ax.annotate(identifier,p,xytext=(3,3),textcoords='offset points',fontsize=7,
                color='darkgreen',bbox={'facecolor':'white','alpha':.8,'pad':.2,'edgecolor':'none'},zorder=5)
        for label,key,color in [('S','start','blue'),('G','goal','red')]:
            p=query[key];ax.scatter(*p,s=100,marker='*',color=color,zorder=7)
            ax.annotate(label,p,xytext=(4,-12),textcoords='offset points',color=color,fontsize=13,fontweight='bold',zorder=8)
        ax.set_xlim(query['range_x']);ax.set_ylim(query['range_y']);ax.set_aspect('equal')
        ax.set_xlabel('x (right)');ax.set_ylabel('y (up)');ax.grid(alpha=.12)
        fig.tight_layout();buffer=io.BytesIO();fig.savefig(buffer,format='png');plt.close(fig)
        png=buffer.getvalue();content.append({'type':'image_url','image_url':{
            'url':'data:image/png;base64,'+base64.b64encode(png).decode(),'detail':'high'}})
    fmt=schema('visual_route',{'targets':{'type':'array','maxItems':8,
        'items':{'type':'string','enum':list(lookup)}}})
    return [{'role':'system','content':SYSTEM},{'role':'user','content':content}],fmt,lookup,png,perf_counter()-tick
