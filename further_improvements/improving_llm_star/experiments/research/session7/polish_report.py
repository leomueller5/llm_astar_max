"""Mechanical prose spacing only; preserve code, links, identifiers and results."""
import re
from common import RESULTS
p=RESULTS/'REPORT.md';lines=[];code=False
prefix='on|at|versus|of|in|to|up|before|after|around|every|than|and|with|from|bound|alpha|pops|size|weight|weighted|input|output|queries|maps|instances|regions|tokens|seconds|image|text|Image|Oracle|uniform|validation|development|main|cap|coefficient|scenario|cut|graph|median|mean|confidence|exactly|samples|All|all|become|verifies|final|pointwise|key|about|only|delta|originalalpha|legacyconstantalpha'
suffix='instances|maps|queries|cases|pops|unique|output|input|waypoints|tokens|seconds|records|regions|new|different|distinct|additional|fixed|free|requested|successful|scalar|geometries|independent|responses|times|cost|bounds|and|or|before|after|for|from|versus|primary|stress|frozen|profile|set|field|matched|on|at|by|to|of|confidence|uniform|measured|global|sample|search|goal|models|actual|reported|tests|passed|mean|samples|validated|quality|when|query|map|gives|has|a|in|bound|envelope|historical|reachable|few|with|labels|calls|requests|forward|means|cached|under|per|audit'
for line in p.read_text().splitlines():
 if line.startswith('```'):code=not code;lines.append(line);continue
 if not code:
  parts=re.split(r'(`[^`]*`|\]\([^)]*\))',line)
  for i,part in enumerate(parts):
   if part.startswith(('`','](')):continue
   part=re.sub(r'\bSession([0-9]+)',r'Session \1',part)
   part=re.sub(r'\b('+prefix+r')(?=[0-9])',r'\1 ',part)
   part=re.sub(r'(?<=[0-9])('+suffix+r')\b',r' \1',part)
   part=re.sub(r'(?<=[0-9])(and|or)(?=[0-9])',r' \1 ',part)
   part=part.replace('originalalpha','original alpha').replace('legacyconstantalpha','legacy constant alpha').replace('Few-shotRH','Few-shot RH')
   part=part.replace('8x8780.15','8x8: 780.15').replace('16x16498.5','16x16: 498.5').replace('few-shot1.05','few-shot 1.05').replace('4x4grid','4x4 grid').replace('zero-shot1.05','zero-shot 1.05')
   parts[i]=part
  line=''.join(parts)
 lines.append(line.rstrip())
p.write_text('\n'.join(lines).rstrip()+'\n')
