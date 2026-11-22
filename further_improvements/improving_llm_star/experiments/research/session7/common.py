"""Session 7 paths and the unchanged cumulative API allowance."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORKSPACE=ROOT.parent
RESULTS=ROOT/'experiments/results/research_session7'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parent/'session6'))
from api import CumulativeLedger,RetryClient,RequestUnavailable,MODEL,load_key
sys.path.insert(0,str(HERE)) # Imported legacy API modules prepend their own script paths.

class Session7Client(RetryClient):
    def __init__(self,**kwargs):
        previous=CumulativeLedger();previous.db.close() # Restore portable Session6 without overwriting it.
        ledger=CumulativeLedger(export_path=RESULTS/'api_export.json')
        super().__init__(ledger=ledger,**kwargs)
    def _structured_chat(self,messages,metadata,max_tokens,response_format,seed,temperature):
        return super()._structured_chat(messages,dict(metadata,session=7),max_tokens,response_format,seed,temperature)
    def chat(self,messages,metadata,max_tokens=1024,response_format=None,seed=20261119,temperature=0):
        if response_format is None:raise ValueError('Session7 requires an explicit structured response schema')
        return super().chat(messages,metadata,max_tokens,response_format,seed,temperature)

def read_cases(path):
    import gzip
    return json.load(gzip.open(path,'rt'))
def dump(path,value):
    import gzip
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.gz':
        with gzip.open(path,'wt') as f:json.dump(value,f)
    else:path.write_text(json.dumps(value,indent=2)+'\n')
