"""Create and flush a new public file without replacing a previous transfer."""
from contextlib import contextmanager
import ctypes
import errno
import os
import secrets

RENAME_NOREPLACE=1


@contextmanager
def open_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        yield fd
    finally:
        os.close(fd)


def publish(directory,name,blocks):
    if not name or name in ('.','..') or '/' in name or '\x00' in name:
        raise ValueError('invalid transfer name')
    staging='.w3-'+secrets.token_hex(12)+'.part'
    fd=os.open(staging,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
    try:
        with os.fdopen(fd,'wb') as target:
            for chunk in blocks:
                if not chunk: continue
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        libc=ctypes.CDLL(None,use_errno=True)
        rename=libc.renameat2
        rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        rename.restype=ctypes.c_int
        if rename(directory,os.fsencode(staging),directory,os.fsencode(name),RENAME_NOREPLACE)!=0:
            error=ctypes.get_errno()
            raise OSError(error,os.strerror(error))
        os.fsync(directory)
    finally:
        try: os.unlink(staging,dir_fd=directory)
        except FileNotFoundError: pass
