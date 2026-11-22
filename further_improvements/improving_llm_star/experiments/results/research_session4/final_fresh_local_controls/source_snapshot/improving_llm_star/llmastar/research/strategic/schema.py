"""Versioned strategic advice, deliberately separate from search correctness."""
from dataclasses import dataclass
import json,math,re
from typing import Optional


@dataclass(frozen=True)
class Bypass:
    obstacle_id:str
    side:str


@dataclass(frozen=True)
class Strategy:
    identifier:str
    confidence:Optional[float]=None
    waypoints:tuple=()
    regions:tuple=()
    bypasses:tuple=()


@dataclass(frozen=True)
class StrategicGuidance:
    strategies:tuple=()
    source:str='unspecified'
    abstain:bool=False
    warnings:tuple=()
    version:int=1


def _point(p):
    if not isinstance(p,(list,tuple)) or len(p)!=2:return None
    try:
        if not all(type(x) in [int,float] and math.isfinite(x) and int(x)==x for x in p):return None
    except (OverflowError,ValueError):return None
    return tuple(int(x) for x in p)


def parse_guidance(raw,source='unspecified',max_characters=100000,max_strategies=4,max_points=256,max_regions=2048):
    """Invalid entries are rejected, never turned into trusted constraints.

    Legacy Generated Path arrays stay supported. Parsing does not infer that a
    waypoint/region is traversable; the search validates actual geometry.
    """
    if isinstance(raw,StrategicGuidance):return raw
    warnings=[]
    if isinstance(raw,str):
        if len(raw)>max_characters:return StrategicGuidance(source=source,abstain=True,warnings=('response_too_large',))
        text=raw.strip();fence=re.search(r'```(?:json)?\s*(.*?)```',text,re.S)
        if fence:text=fence.group(1).strip()
        try:value=json.loads(text)
        except (ValueError,TypeError):
            # Preserve the repository's legacy parser only for that format.
            markers=list(re.finditer(r'Generated\s*Path',raw,re.I))
            if not markers:return StrategicGuidance(source=source,abstain=True,warnings=('unrecognized_text',))
            value=[]
            # A response may repeat a complete route and end with a truncated
            # duplicate. Recover the last COMPLETE marked 2-D array, never a
            # synthetic coordinate or an unmarked partial route.
            for marker_index,marker in reversed(list(enumerate(markers))):
                end=markers[marker_index+1].start() if marker_index+1<len(markers) else len(raw)
                match=re.search(r'\[\s*\[',raw[marker.end():end])
                if match is None:continue
                begin=marker.end()+match.start()
                try:candidate=json.JSONDecoder().raw_decode(raw[begin:end])[0]
                except (ValueError,TypeError):continue
                if isinstance(candidate,list):
                    value=candidate
                    if marker_index!=len(markers)-1:warnings.append('recovered_earlier_complete_route')
                    break
            warnings.append('legacy_response')
    else:value=raw
    if isinstance(value,list):value={'version':1,'strategies':[{'id':'legacy','waypoints':value}]}
    if not isinstance(value,dict) or type(value.get('version',1)) is not int or value.get('version',1)!=1:
        return StrategicGuidance(source=source,abstain=True,warnings=tuple(warnings+['unsupported_structure_or_version']))
    if value.get('abstain') is True:return StrategicGuidance(source=source,abstain=True,warnings=tuple(warnings))
    entries=value.get('strategies',[])
    if not isinstance(entries,list):return StrategicGuidance(source=source,abstain=True,warnings=tuple(warnings+['strategies_not_list']))
    result=[];seen=set()
    for i,entry in enumerate(entries[:max_strategies]):
        if not isinstance(entry,dict):warnings.append(f'candidate_{i}_not_object');continue
        identifier=entry.get('id',f'candidate_{i}')
        if not isinstance(identifier,str) or not identifier or len(identifier)>64 or identifier in seen:
            warnings.append(f'candidate_{i}_bad_id');continue
        confidence=entry.get('confidence')
        if confidence is not None and (type(confidence) not in [int,float] or not 0<=confidence<=1 or not math.isfinite(confidence)):
            warnings.append(f'{identifier}_bad_confidence');confidence=None
        points=[]
        rawpoints=entry.get('waypoints',[])
        if not isinstance(rawpoints,list):warnings.append(f'{identifier}_bad_waypoints');rawpoints=[]
        if len(rawpoints)>max_points:warnings.append(f'{identifier}_point_budget_truncated')
        for p in rawpoints[:max_points]:
            point=_point(p)
            if point is None:warnings.append(f'{identifier}_invalid_point')
            elif not points or point!=points[-1]:points.append(point)
        regions=entry.get('regions',[])
        if not isinstance(regions,list) or any(not isinstance(r,str) or not 0<len(r)<=64 for r in regions[:max_regions]):
            warnings.append(f'{identifier}_bad_regions');regions=[]
        if len(regions)>max_regions:warnings.append(f'{identifier}_region_budget_truncated')
        bypasses=[]
        rawbypasses=entry.get('bypasses',[])
        if not isinstance(rawbypasses,list):rawbypasses=[];warnings.append(f'{identifier}_bad_bypasses')
        if len(rawbypasses)>max_points:warnings.append(f'{identifier}_bypass_budget_truncated')
        for b in rawbypasses[:max_points]:
            if isinstance(b,dict) and isinstance(b.get('obstacle_id'),str) and len(b['obstacle_id'])<=64 and re.fullmatch(r'[hv][0-9]+',b['obstacle_id']) and b.get('side') in ['left','right','above','below']:
                bypasses.append(Bypass(b['obstacle_id'],b['side']))
            else:warnings.append(f'{identifier}_invalid_bypass')
        if points or regions or bypasses:
            result.append(Strategy(identifier,confidence,tuple(points),tuple(regions[:max_regions]),tuple(bypasses)));seen.add(identifier)
    if len(entries)>max_strategies:warnings.append('candidate_budget_truncated')
    return StrategicGuidance(tuple(result),source,not bool(result),tuple(warnings))
