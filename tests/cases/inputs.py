import hashlib
import json
import sys


def check(root,work,command,require,blocked,component):
    package=work/'mr-sitting'
    package.write_bytes(b'public candidate')
    locked=hashlib.sha256(package.read_bytes()).hexdigest()
    source=work/'source.tar';source.write_bytes(b'public source fixture')
    codehash=hashlib.sha256(source.read_bytes()).hexdigest()
    name='mr-sitting'
    entry={'name':name,'revision':'a'*40,'source':'source.tar','source_sha256':codehash,'artifact':name,
           'artifact_sha256':locked,'license':'fixture','recipe_sha256':'b'*64,'lockfile_sha256':'c'*64,'policy':'strict'}
    manifest=work/'inputs.json'
    manifest.write_text(json.dumps({'role':'sitting-stick','applications':[entry]})+'\n')
    bound=hashlib.sha256(manifest.read_bytes()).hexdigest()
    package.write_bytes(b'changed after download')
    verifier=root/'scripts/check-inputs.py'
    if not verifier.exists():
        require(hashlib.sha256(package.read_bytes()).hexdigest()==locked,'required input failed authentication')
    # A genuine restricted application set is the subject of this component test.
    import importlib.util
    spec=importlib.util.spec_from_file_location('input_validation',verifier)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def passed():
        try: mod.verify(work,manifest,bound,'sitting-stick',{name}); return True
        except (ValueError,OSError): return False
    require(not passed(),'required input failed authentication')
    package.write_bytes(b'public candidate')
    require(passed(),'valid pinned input refused')
    source.write_bytes(b'wrong source');require(not passed(),'required input failed authentication')
    source.write_bytes(b'public source fixture')
    entry['policy']='ordinary'
    manifest.write_text(json.dumps({'role':'sitting-stick','applications':[entry]}))
    bound=hashlib.sha256(manifest.read_bytes()).hexdigest()
    require(not passed(),'required input failed authentication')
    if not component: raise blocked('authenticated full release input bundle and archives are required')
