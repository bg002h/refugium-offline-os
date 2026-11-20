import importlib.util
import os
import sys


def check(root,work,command,require,blocked,component):
    module=root/'image/stick/public_copy.py'
    previous=work/'public.txt';previous.write_bytes(b'previous public record')
    if not module.exists():
        # The baseline leaves a truncated final filename across an interrupted write.
        with previous.open('wb') as f: f.write(b'incomplete')
        require(previous.read_bytes()==b'previous public record','incomplete transfer reported success')
    spec=importlib.util.spec_from_file_location('public_copy',module)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    with mod.open_directory(work) as directory:
        try:
            mod.publish(directory,'public.txt',[b'new file'])
        except FileExistsError: pass
        else: require(False,'incomplete transfer reported success')
        require(previous.read_bytes()==b'previous public record','incomplete transfer reported success')
        def interrupted():
            yield b'public prefix'
            raise OSError('simulated removal')
        try: mod.publish(directory,'new.txt',interrupted())
        except OSError: pass
        else: require(False,'incomplete transfer reported success')
        require(not (work/'new.txt').exists(),'incomplete transfer reported success')
        mod.publish(directory,'new.txt',[b'complete'])
        require((work/'new.txt').read_bytes()==b'complete','incomplete transfer reported success')
    if not component: raise blocked('power loss and FAT32 eject in the guest are required')
