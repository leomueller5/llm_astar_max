"""No oracle imports: inference uses map facts and admissible lower bounds only."""
import base64,io,json,math,os,tempfile
from pathlib import Path
from common import ROOT
from llmastar.research.spatial_guidance import RegionField
from llmastar.research.geometry import SegmentGridGraph
from llmastar.research.strategic.cuts import CutPotential
from llmastar.research.search import octile
SYSTEM='You assist an eight-neighbor grid A* planner. Walls are CLOSED segments: crossing or touching them is illegal. Coordinates are x right, y UP. Diagonal moves cost sqrt(2), axial moves cost 1. Give compact strategic spatial advice, not a complete step-by-step path. Never assume a direct line through a wall is traversable.'

def schema(name,properties):return {'type':'json_schema','json_schema':{'name':name,'strict':True,'schema':{'type':'object','additionalProperties':False,'properties':properties,'required':list(properties)}}}

def ascii_map(query):
    g=SegmentGridGraph(query);s,t=tuple(query['start']),tuple(query['goal']);rows=[]
    for y in range(g.y1-1,g.y0,-1):
        rows.append(str(y).rjust(3)+' '+''.join('S' if (x,y)==s else 'G' if (x,y)==t else '#' if g.blocked((x,y)) else '.' for x in range(g.x0+1,g.x1)))
    return 'Exact integer-cell occupancy, highest y first. # is blocked; . free. First column x='+str(g.x0+1)+'.\n'+'\n'.join(rows)

def render(query,side=8,labeled=False):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'llm-astar-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    f=RegionField(query,side);g=f.graph;fig,ax=plt.subplots(figsize=(6.4,6.4),dpi=80)
    for y,lo,hi in query['horizontal_barriers']:ax.plot([lo,hi],[y,y],color='black',lw=2)
    for x,lo,hi in query['vertical_barriers']:ax.plot([x,x],[lo,hi],color='black',lw=2)
    for r in f.regions:
        lo,hi=r['bounds'];x=(lo[0]+hi[0])/2;y=(lo[1]+hi[1])/2
        ax.text(x,y,r['id'],ha='center',va='center',fontsize=6,color='#777777',alpha=.8)
    for i in range(side+1):
        ax.axvline(g.x0+1+i*f.width/side-.5,color='#cccccc',ls=':',lw=.5)
        ax.axhline(g.y0+1+i*f.height/side-.5,color='#cccccc',ls=':',lw=.5)
    candidates={}
    if labeled:
        from llmastar.research.geometric_advice import portfolio
        p=portfolio(query,g,budget=12)
        for identifier,point in list(p['points'].items())[:16]:
            short='P'+str(len(candidates));candidates[short]=point
            ax.plot(*point,'b.',ms=3);ax.annotate(short,point,fontsize=5,color='blue',xytext=(2,2),textcoords='offset points')
    for key,color,label in [('start','green','S'),('goal','red','G')]:
        x,y=query[key];ax.plot(x,y,'o',color=color,ms=6);ax.annotate(label,(x,y),xytext=(4,4),textcoords='offset points',weight='bold',fontsize=10,color=color)
    ax.set(xlim=(g.x0,g.x1),ylim=(g.y0,g.y1),xlabel='x (right)',ylabel='y (up)',title='Map facts only; region R0 at lower left');ax.set_aspect('equal');fig.tight_layout()
    b=io.BytesIO();fig.savefig(b,format='png',dpi=80);plt.close(fig)
    return b.getvalue(),candidates

def build(query,representation='structured',task='corridor',side=8,examples=None,feedback=None):
    field=RegionField(query,side);g=field.graph;ids=[r['id'] for r in field.regions]
    metadata={'range_x':query['range_x'],'range_y':query['range_y'],'start':query['start'],'goal':query['goal'],'region_grid':{'side':side,'id_rule':'R(iy*side+ix), ix increases right, iy increases UP from zero','interior_min':[g.x0+1,g.y0+1],'interior_max':[g.x1-1,g.y1-1],'width':field.width,'height':field.height}}
    if task=='cost':
        try:h=CutPotential(query,tuple(query['goal'])).value
        except ValueError:h=lambda p:octile(p,tuple(query['goal']))
        metadata['regions']=[dict(r,geometric_lower_bound=h(tuple(r['sample'])) if r['sample'] and math.isfinite(h(tuple(r['sample']))) else None) for r in field.regions]
        instruction='For EACH region sample, estimate ADDITIONAL remaining distance beyond the supplied geometric_lower_bound to the GOAL, ignoring the start. detour=0 when the bound already accounts for the route. priority is the chance this region is useful for a SHORT start-to-goal route, not merely locally close to the goal. confidence is your uncertainty estimate. Do not confuse distance-to-goal with additional detour. Return each region ID once.'
        item={'type':'object','additionalProperties':False,'properties':{'region_id':{'type':'string','enum':ids},'detour':{'type':'number','minimum':0,'maximum':100000},'priority':{'type':'number','minimum':0,'maximum':1},'confidence':{'type':'number','minimum':0,'maximum':1}},'required':['region_id','detour','priority','confidence']}
        fmt=schema('regional_cost_estimates',{'predictions':{'type':'array','items':item,'minItems':len(ids),'maxItems':len(ids)}})
    else:
        instruction='Identify the SMALL SET of coarse regions likely traversed by a short valid START-to-GOAL route. Think about global wall connectivity and necessary temporary movement away from the goal. Return preferred region IDs in route order, and avoid IDs ONLY for genuinely misleading dead ends. Regions may contain both good and bad cells: do not reject a whole region merely because a wall passes through it. Include start/goal regions where appropriate. Be selective, but do not omit necessary detours. Confidence is not a correctness proof.'
        fmt=schema('spatial_route_assessment',{'preferred':{'type':'array','items':{'type':'string','enum':ids},'maxItems':min(48,len(ids))},'avoid':{'type':'array','items':{'type':'string','enum':ids},'maxItems':min(24,len(ids))},'confidence':{'type':'number','minimum':0,'maximum':1}})
    context=dict(metadata)
    if representation in ['coordinates','hybrid','structured']:context['obstacles']={'horizontal_barriers':query['horizontal_barriers'],'vertical_barriers':query['vertical_barriers']}
    if representation=='structured':
        context['wall_descriptions']=[{'id':f'H{i}','from':[lo,y],'to':[hi,y]} for i,(y,lo,hi) in enumerate(query['horizontal_barriers'])]+[{'id':f'V{i}','from':[x,lo],'to':[x,hi]} for i,(x,lo,hi) in enumerate(query['vertical_barriers'])]
    text=instruction+'\n'+json.dumps(context,separators=(',',':'))
    image=None
    if representation=='ascii':text+='\n'+ascii_map(query)
    elif representation in ['image','image_labeled','hybrid']:
        image,candidates=render(query,side,labeled=representation=='image_labeled')
        if candidates:text+='\nFree candidate labels:'+json.dumps(candidates,separators=(',',':'))
    elif representation not in ['coordinates','structured']:raise ValueError('Unknown representation')
    if feedback is not None:text+='\nActual search observations (not an optimal route):'+json.dumps(feedback,separators=(',',':'))
    messages=[{'role':'system','content':SYSTEM}]
    for example in examples or []:
        messages.extend([{'role':'user','content':example['input']},{'role':'assistant','content':json.dumps(example['answer'],separators=(',',':'))}])
    messages.append({'role':'user','content':[{'type':'text','text':text},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image).decode(),'detail':'high'}}] if image else text})
    return messages,fmt,{'side':side,'representation':representation,'task':task,'image_bytes':len(image) if image else 0,'region_ids':ids},image

def decode(query,raw,side=8,task='corridor',confidence=True):
    field=RegionField(query,side)
    try:obj=json.loads(raw)
    except (TypeError,ValueError):return field,{'parsed':False,'error':'json'}
    if not isinstance(obj,dict):return field,{'parsed':False,'error':'object'}
    if task=='cost':
        try:field.update(obj)
        except (ValueError,TypeError):return field,{'parsed':False,'error':'prediction_list'}
        return field,{'parsed':field.rejections==0,'rejections':field.rejections,'coverage':len(field.values)/len(field.regions)}
    ids={r['id'] for r in field.regions};pref=obj.get('preferred',[]);avoid=obj.get('avoid',[]);conf=obj.get('confidence',0.)
    if (not isinstance(pref,list) or not isinstance(avoid,list) or any(type(v) is not str or v not in ids for v in pref+avoid) or type(conf) not in [int,float] or not math.isfinite(conf) or not 0<=conf<=1):return field,{'parsed':False,'error':'schema'}
    field.update([{'region_id':r['id'],'priority':1. if r['id'] in pref else 0. if r['id'] in avoid else .5,'detour':0.,'confidence':conf if confidence else 1.} for r in field.regions])
    return field,{'parsed':True,'preferred':list(dict.fromkeys(pref)),'avoid':list(dict.fromkeys(avoid)),'confidence':conf,'overlap':len(set(pref)&set(avoid))}
