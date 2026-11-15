[org 0x7c00]
[bits 16]

STAGE2_OFF equ 0x9000
STAGE2_SECTORS equ 10
BOOT_DRV   equ 0x7DFE

mov [BOOT_DRV], dl

mov bp, 0x9000
mov sp, bp

call serial_init

mov bx, msg
call print16
call serial_print

mov dl, [BOOT_DRV]
mov ah, 0x42
mov si, DAPACK
mov [DAPACK.addr], word STAGE2_OFF
mov [DAPACK.addr+2], word 0
mov [DAPACK.lba], dword 1
mov [DAPACK.count], word STAGE2_SECTORS
int 0x13
jc disk_err

mov bx, msg_ld_ok
call serial_print

mov bx, STAGE2_OFF
jmp bx

disk_err:
    mov bx, msg_err
    call print16
    jmp $

print16:
    pusha
    mov ah, 0x0e
.n: mov al, [bx]
    cmp al, 0
    je .d
    int 0x10
    inc bx
    jmp .n
.d: popa
    ret

serial_init:
    mov dx, 0x3f8
    mov al, 0x03
    out dx, al
    mov al, 0x18
    out dx, al
    mov al, 0x01
    out dx, al
    mov al, 0x00
    out dx, al
    ret

serial_print:
    pusha
.sn:
    mov al, [bx]
    cmp al, 0
    je .sd
    mov dx, 0x3fd
.sw: in al, dx
    test al, 0x20
    jz .sw
    mov dx, 0x3f8
    mov al, [bx]
    out dx, al
    inc bx
    jmp .sn
.sd: popa
    ret

msg:     db "LunarOS MBR", 13, 10, 0
msg_ld_ok: db "Stage2 loaded", 13, 10, 0
msg_err: db "Disk fail!", 0

DAPACK:
    db 16
    db 0
.count: dw 0
.addr:  dd 0
.lba:   dq 0

times 510 - ($ - $$) db 0
dw 0xaa55