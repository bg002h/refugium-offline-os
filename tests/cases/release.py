import hashlib
import json
import sys


def check(root, work, command, require, blocked):
    image = work / 'candidate.img'
    image.write_bytes(bytes(range(256))*16)
    raw = image.read_bytes()
    manifest = work / 'release.json'
    sig = work / 'release.minisig'
    key, secret = work/'test.pub', work/'test.sec'
    generated = command(['minisign','-G','-W','-p',key,'-s',secret])
    if generated.returncode != 0:
        raise blocked('test signing key could not be created')
    def sign(role='sitting-stick', version='test-1', length=len(raw), digest=hashlib.sha256(raw).hexdigest()):
        manifest.write_text(json.dumps(dict(role=role,version=version,bytes=length,sha256=digest))+'\n')
        signed = command(['minisign','-S','-s',secret,'-m',manifest,'-x',sig,'-q'])
        if signed.returncode != 0: raise blocked('test signature could not be created')

    target = root/'scripts/verify-image.py'
    def verify(mode, path, expected_role='sitting-stick',expected_version='test-1'):
        return command([sys.executable,'-B',target,mode,'--key',key,'--signature',sig,'--manifest',manifest,
                        '--role',expected_role,'--version',expected_version,path])
    sign('node')
    # Contrast with the real hash-only verification a plain image download provides.
    checked = command(['sha256sum','--check','--status'],input=(hashlib.sha256(raw).hexdigest()+'  '+str(image)+'\n').encode())
    if checked.returncode != 0: raise blocked('baseline checksum tool failed')
    if not target.exists():
        require(checked.returncode != 0,'wrong release role accepted')
    rejected=b'Image verification failed. No drive was written.\n'
    readback=b'The written drive could not be verified. Keep the previous stick.\n'
    def refuses(result, text=rejected):
        require(result.returncode==1 and result.stderr==text,'wrong release role accepted')
    refuses(verify('image',image))
    sign()
    require(verify('image', image).returncode==0,'valid image refused')
    refuses(verify('image',image,expected_version='test-2'))
    short=work/'short.img'
    short.write_bytes(raw[:-1])
    refuses(verify('image',short))
    extended=work/'long.img'
    extended.write_bytes(raw+b'extra bytes outside the copied extent')
    refuses(verify('image',extended))
    require(verify('readback',extended).returncode==0,'readback used bytes outside the declared extent')
    refuses(verify('readback',short),readback)
    damaged=bytearray(raw); damaged[-1]^=1
    short.write_bytes(damaged)
    refuses(verify('image',short))
    refuses(verify('readback',short),readback)
    sig.write_bytes(sig.read_bytes().replace(b'R',b'Z'))
    refuses(verify('image',image))
    sign()
    other_key,other_secret=work/'other.pub',work/'other.sec'
    if command(['minisign','-G','-W','-p',other_key,'-s',other_secret]).returncode!=0: raise blocked('second test key unavailable')
    key.write_bytes(other_key.read_bytes())
    refuses(verify('image',image))
