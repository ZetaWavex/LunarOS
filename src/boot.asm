[org 0x7c00]
[bits 16]

STAGE2_OFF     equ 0x9000
STAGE2_SECTORS equ 10
BOOT_DRV       equ 0x7DFE

cli
xor ax, ax
mov ds, ax
mov es, ax
mov ss, ax
mov sp, 0x7C00
sti

mov [BOOT_DRV], dl

call serial_init

mov bx, msg
call print16
call serial_print

call chs_geom

mov dword [CUR_LBA], 1
mov cx, STAGE2_SECTORS
mov bx, STAGE2_OFF

.read_one:
    push cx
    push bx
    call lba_to_chs
    mov dl, [BOOT_DRV]
    mov ax, 0x0201
    int 0x13
    pop bx
    pop cx
    jc disk_err
    add bx, 512
    inc dword [CUR_LBA]
    loop .read_one

mov bx, msg_ld_ok
call print16
call serial_print

mov dl, [BOOT_DRV]
mov bx, STAGE2_OFF
jmp bx

disk_err:
    mov [err_code], ah
    mov bx, msg_err
    call print16
    call serial_print
    mov al, [err_code]
    call print_hex
    call serial_hex

halt_err:
    jmp halt_err

serial_hex:
    pusha
    mov bl, al
    shr al, 4
    call .emit
    mov al, bl
    call .emit
    popa
    ret
.emit:
    and al, 0x0F
    cmp al, 10
    jb .dig
    add al, 'A' - 10
    jmp .put
.dig:
    add al, '0'
.put:
    mov ah, al
    mov dx, 0x3fd
.sw: in al, dx
    test al, 0x20
    jz .sw
    mov dx, 0x3f8
    mov al, ah
    out dx, al
    ret

chs_geom:
    pusha
    mov byte [GEO_SPT], 18
    mov byte [GEO_HEADS], 2
    mov dl, [BOOT_DRV]
    mov ah, 0x08
    int 0x13
    jc .out
    movzx eax, cl
    and eax, 0x3F
    jz .out
    mov [GEO_SPT], al
    movzx eax, dh
    inc eax
    mov [GEO_HEADS], al
.out:
    popa
    ret

lba_to_chs:
    movzx ecx, byte [GEO_SPT]
    movzx ebx, byte [GEO_HEADS]
    imul ebx, ecx
    mov eax, [CUR_LBA]
    xor edx, edx
    div ebx
    mov ch, al
    mov eax, edx
    xor edx, edx
    div ecx
    mov dh, al
    mov cl, dl
    inc cl
    ret

print_hex:
    pusha
    mov ah, 0x0e
    mov cl, al
    shr al, 4
    call .nib
    mov al, cl
    call .nib
    popa
    ret
.nib:
    and al, 0x0F
    cmp al, 10
    jb .d
    add al, 'A' - 10 - '0'
.d: add al, '0'
    int 0x10
    ret

err_code: db 0
GEO_SPT:   db 18
GEO_HEADS: db 2
CUR_LBA:   dd 1

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

msg:       db "LunarOS MBR", 13, 10, 0
msg_ld_ok: db "Stage2 loaded", 13, 10, 0
msg_err:   db "Disk fail! code 0x", 0

times 510 - ($ - $$) db 0
dw 0xaa55