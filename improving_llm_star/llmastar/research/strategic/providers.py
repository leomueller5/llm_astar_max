"""Deterministic/cached provider interface, with an explicit latency ledger."""
from dataclasses import dataclass,field
from time import perf_counter
from .schema import parse_guidance


@dataclass(frozen=True)
class GuidanceContext:
    query:dict
    event:str='initial'
    expanded:int=0
    incumbent_cost:float|None=None
    lower_bound:float|None=None
    failed_strategies:tuple=()
    region_summary:dict=field(default_factory=dict)


class ScriptedProvider:
    """A response is advice, not a trusted map or correctness certificate.

    charged_latency is a simulated budget, never an artificial sleep and never
    reported as measured model latency. There are zero actual API requests.
    """
    def __init__(self,responses,source='synthetic',charged_latency=0.):
        if charged_latency<0:raise ValueError('Nonnegative simulated latency required')
        self.can_revise=True
        self.responses=list(responses);self.source=source;self.charged_latency=charged_latency
        self.calls=0;self.actual_api_calls=0;self.actual_tokens=None;self.actual_cost=0.
        self.events=[];self.processing_seconds=0.;self.simulated_latency_seconds=0.

    def propose(self,context):
        began=perf_counter();index=self.calls;self.calls+=1
        raw=self.responses[index] if index<len(self.responses) else {'version':1,'abstain':True}
        guidance=parse_guidance(raw,self.source)
        self.processing_seconds+=perf_counter()-began;self.simulated_latency_seconds+=self.charged_latency
        self.events.append({'event':context.event,'expanded':context.expanded,'candidate_ids':[s.identifier for s in guidance.strategies],'warnings':list(guidance.warnings)})
        return guidance


class StaticProvider(ScriptedProvider):
    def __init__(self,response,source='cached_real',charged_latency=0.):
        super().__init__([response],source,charged_latency);self.can_revise=False
