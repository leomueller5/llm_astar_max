"""Compile untrusted strategic/legacy advice into soft, connected region corridors."""
from collections import deque
from dataclasses import dataclass
from .schema import Strategy


@dataclass(frozen=True)
class CompiledStrategy:
    identifier:str
    route:tuple
    confidence:float|None
    warnings:tuple=()


def bridge_regions(hierarchy,a,b):
    if a==b:return [a]
    queue=deque([a]);parent={a:None}
    while queue:
        node=queue.popleft()
        for other in sorted(hierarchy.region_neighbors.get(node,())):
            if other in parent:continue
            parent[other]=node
            if other==b:
                path=[b]
                while path[-1]!=a:path.append(parent[path[-1]])
                return list(reversed(path))
            queue.append(other)
    return []


def compile_strategy(strategy,hierarchy,start,goal,candidates=None):
    warnings=[];start_region=hierarchy.region_of(start);goal_region=hierarchy.region_of(goal)
    if start_region<0 or goal_region<0:return CompiledStrategy(strategy.identifier,(),strategy.confidence,('invalid_endpoints',))
    targets=[]
    if candidates and strategy.identifier in candidates and not(strategy.regions or strategy.waypoints or strategy.bypasses):
        targets=list(candidates[strategy.identifier])
    for region in strategy.regions:
        if region in hierarchy.names:targets.append(hierarchy.names[region])
        else:warnings.append('unknown_region')
    points=list(strategy.waypoints)
    query_walls={'h':hierarchy.graph.horizontal,'v':hierarchy.graph.vertical}
    for bypass in strategy.bypasses:
        kind=bypass.obstacle_id[0];i=int(bypass.obstacle_id[1:]);walls=query_walls[kind]
        if i>=len(walls):warnings.append('unknown_obstacle');continue
        coordinate,lo,hi=walls[i]
        if kind=='h' and bypass.side in ['left','right']:
            points.append((lo-1 if bypass.side=='left' else hi+1,coordinate))
        elif kind=='v' and bypass.side in ['below','above']:
            points.append((coordinate,lo-1 if bypass.side=='below' else hi+1))
        else:warnings.append('orientation_incompatible_bypass')
    for point in points:
        region=hierarchy.region_of(point)
        if region<0:warnings.append('invalid_point')
        else:targets.append(region)
    if not targets:return CompiledStrategy(strategy.identifier,(),strategy.confidence,tuple(warnings+['empty_strategy']))
    route=[start_region]
    for target in targets+[goal_region]:
        if target==route[-1]:continue
        bridge=bridge_regions(hierarchy,route[-1],target)
        if not bridge:return CompiledStrategy(strategy.identifier,(),strategy.confidence,tuple(warnings+['disconnected_strategy']))
        route.extend(bridge[1:])
    return CompiledStrategy(strategy.identifier,tuple(route),strategy.confidence,tuple(warnings))


def region_trace(hierarchy,path):
    result=[]
    for point in path:
        region=hierarchy.region_of(point)
        if region>=0 and (not result or result[-1]!=region):result.append(region)
    return result
