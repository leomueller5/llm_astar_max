"""Development-motivated grounding revision, kept separate from paired v1 pilot."""
import json
from prompts_spatial import build as original_build
from common import ROOT
from llmastar.research.spatial_guidance import RegionField
from llmastar.research.geometry import SegmentGridGraph

def build(query,representation='structured',task='corridor',side=8,examples=None,feedback=None):
    messages,fmt,meta,image=original_build(query,representation,task,side,examples,feedback)
    field=RegionField(query,side);s=field.identifier(query['start']);t=field.identifier(query['goal'])
    grounding={'start_region':s,'goal_region':t,'free_region_samples':[{'id':r['id'],'bounds':r['bounds'],'sample':r['sample']} for r in field.regions],
        'self_check_rules':['The preferred route must start in start_region and finish in goal_region.','Never mark start_region or goal_region as avoid.','A region ID is a location, not its numeric rank. Descending IDs are not inherently a route.','Do not mark a location both preferred and avoid. Empty avoid is better than invented dead ends.']}
    prefix='IMPORTANT exact spatial grounding (computed from coordinates; do not infer a different region numbering):'+json.dumps(grounding,separators=(',',':'))+'\n'
    last=messages[-1]
    if isinstance(last['content'],list):last['content'][0]['text']=prefix+last['content'][0]['text']
    else:last['content']=prefix+last['content']
    if task=='corridor':fmt['json_schema']['schema']['properties']['avoid']['items']['enum']=[r['id'] for r in field.regions if r['id'] not in [s,t]]
    meta['grounding_version']='explicit_regions_v2';return messages,fmt,meta,image
