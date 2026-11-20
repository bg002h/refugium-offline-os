import importlib.util


def check(root,work,command,require,blocked,component):
    source=root/'image/stick/media_devices.py'
    rows=[
        {'name':'/dev/base1','maj:min':'8:1','type':'part','pkname':'/dev/base','partuuid':'boot-id','size':16,'fstype':'vfat','fsver':'FAT32'},
        {'name':'/dev/base2','maj:min':'8:2','type':'part','pkname':'/dev/base','partuuid':'data','size':16,'fstype':'vfat','fsver':'FAT32'},
        {'name':'/dev/in1','maj:min':'8:17','type':'part','pkname':'/dev/in','partuuid':'incoming','size':32,'fstype':'vfat','fsver':'FAT32'},
        {'name':'/dev/int1','maj:min':'8:33','type':'part','pkname':'/dev/int','partuuid':'internal','size':64,'fstype':'ext4','fsver':'1.0'},
    ]
    if not source.exists():
        baseline=next(r['name'] for r in rows if r['type']=='part')
        require(baseline!='/dev/base1','wrong or changed device accepted')
    spec=importlib.util.spec_from_file_location('media_devices',source)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def hardware(row):
        if row['pkname']=='/dev/int': return None
        return ('2-1',17,'0000','0001')
    eligible=mod.candidates(rows,'boot-id',hardware)
    require(len(eligible)==1 and eligible[0]['name']=='/dev/in1','wrong or changed device accepted')
    old=eligible[0]['token']
    changed=mod.candidates(rows,'boot-id',lambda row: None if not hardware(row) else ('2-1',18,'0000','0001'))
    require(not mod.select(changed,old),'wrong or changed device accepted')
    require(not mod.candidates(rows,'unknown',hardware),'wrong or changed device accepted')
    require(not mod.candidates(rows+[dict(rows[2],partuuid='boot-id')],'boot-id',hardware),'wrong or changed device accepted')
    require(not mod.candidates(rows,'boot-id',lambda row:('2-1',17,'2e8a','000f')),'wrong or changed device accepted')
    if not component: raise blocked('insertion and device-change tests on a booted image are required')
