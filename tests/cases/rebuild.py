import hashlib
from pathlib import Path
import os


def check(root,work,command,require,blocked,component):
    locations=[os.environ.get('W3_BUILD_A'),os.environ.get('W3_BUILD_B')]
    if not all(locations):
        raise blocked('two independent build output directories are required')
    digests={}
    def hash_file(p):
        with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
    for role in ('sitting-stick','node'):
        p,q=[Path(d)/(role+'.img') for d in locations]
        if not p.is_file() or not q.is_file(): raise blocked('both complete artifacts for each image role are required')
        require(p.stat().st_size>0 and p.stat().st_size==q.stat().st_size and hash_file(p)==hash_file(q),'clean builds differ')
        digests[role]=hash_file(p)
    require(digests['sitting-stick']!=digests['node'],'clean builds differ')
    if not component:
        raise blocked('independent VM provenance and successful boots of both roles are required')
