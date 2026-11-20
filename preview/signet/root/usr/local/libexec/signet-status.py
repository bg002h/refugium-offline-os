#!/usr/bin/python3 -B
"""Report public chain status and wallet RPC readiness on the guest serial console."""
import json,os,subprocess,time
args=['/usr/local/bin/bitcoin-cli','-signet','-datadir=/home/live/.bitcoin','-rpcconnect=127.0.0.1','-rpcport=38332']
def call(method):
    p=subprocess.run(args+[method],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=6)
    if p.returncode:
        raise ValueError('RPC not ready')
    return json.loads(p.stdout)
prev=None
while True:
    try:
        chain=call('getblockchaininfo')
        net=call('getnetworkinfo')
        peers=call('getpeerinfo')
        row={'chain':chain['chain'],'blocks':chain['blocks'],'headers':chain['headers'],'hash':chain['bestblockhash'],'initial_sync':chain['initialblockdownload'],'pruned':chain['pruned'],'tip_time':chain['time'],'version':net['version'],'peers':len(peers),'peer_heights':[p.get('synced_headers',-1) for p in peers],'wallet_rpc':isinstance(call('listwallets'),list),'wallet_uid':os.getuid()}
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):
        row={'ready':False}
    if row!=prev:
        print('SIGNET-VM '+json.dumps(row),flush=True)
        prev=row
    time.sleep(5)
