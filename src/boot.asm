[org 0x7c00]
[bits 16]

BOOT_DRV equ 0x7DFE

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
call serial_print

mov al, dl
call serial_hex
mov al, ' '
call serial_putc

mov ah, 0x48
mov si, edd_buf
mov dl, [BOOT_DRV]
int 0x13
jc .no_edd
mov bx, msg_edd
call serial_print
mov al, [edd_buf+1]
call serial_hex
mov al, ' '
call serial_putc
mov ax, [edd_buf+2]
call serial_hex16
mov al, ' '
call serial_putc
mov ax, [edd_buf+24]
call serial_hex16
mov al, 13
call serial_putc
mov al, 10
call serial_putc
jmp .read
.no_edd:
mov bx, msg_no_edd
call serial_print
mov al, ah
call serial_hex
mov al, 13
call serial_putc
mov al, 10
call serial_putc

.read:
mov dword [dap_lba], 23
mov word [dap_count], 1
mov word [dap_off], 0x3000
mov word [dap_seg], 0
mov si, dap
mov dl, [BOOT_DRV]
mov ah, 0x42
int 0x13
jc .fail

mov bx, msg_ok
call serial_print
mov si, 0x3000
mov cx, 8
call dump_hex

mov bx, msg_kern
call serial_print
mov si, 0x9200
mov cx, 16
call dump_hex

mov bx, msg_pwd
call serial_print
mov si, 0x27C00
mov cx, 16
call dump_hex

jmp $

.fail:
mov bx, msg_fail
call serial_print
mov al, ah
call serial_hex
mov al, 13
call serial_putc
mov al, 10
call serial_putc
jmp $

dump_hex:
    pusha
.dh_loop:
    mov al, [si]
    call serial_hex
    mov al, ' '
    call serial_putc
    inc si
    loop .dh_loop
    mov al, 13
    call serial_putc
    mov al, 10
    call serial_putc
    popa
    ret

serial_putc:
    pusha
    mov ah, al
    mov dx, 0x3fd
.sw: in al, dx
    test al, 0x20
    jz .sw
    mov dx, 0x3f8
    mov al, ah
    out dx, al
    popa
    ret

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
    call serial_putc
    ret

serial_hex16:
    pusha
    mov bx, ax
    mov al, bh
    call serial_hex
    mov al, bl
    call serial_hex
    popa
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
    call serial_putc
    inc bx
    jmp .sn
.sd: popa
    ret

edd_buf: times 32 db 0

dap:
    db 16
    db 0
dap_count: dw 1
dap_off:   dw 0
dap_seg:   dw 0
dap_lba:   dq 23

msg:     db "LunarOS MBR drv=", 0
msg_edd: db "EDD size=0x", 0
msg_no_edd: db "EDD FAIL 0x", 0
msg_ok:  db "READ OK: ", 0
msg_kern: db "mem 9200: ", 0
msg_pwd:  db "mem 27C00: ", 0
msg_fail: db "READ FAIL 0x", 0

times 510 - ($ - $$) db 0
dw 0xaa55