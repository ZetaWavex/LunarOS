KERNEL_OFFSET  equ 0x10000
VBE_INFO_ADDR  equ 0x8000
PWD_SRC_SEG    equ 0x2700
PWD_SRC_OFF    equ 0x0C00
PWD_DST_ADDR   equ 0x1000

[org 0x9000]
[bits 16]

jmp main

%include "print16.asm"
%include "vesa.asm"
%include "gdt.asm"

switch_to_pm:
    cli
    lgdt [gdt_descriptor]
    mov eax, cr0
    or eax, 0x1
    mov cr0, eax
    jmp CODE_SEG:init_pm

msg_main:     db "Stage2 OK", 13, 10, 0
msg_pwd:      db "PWD copied", 13, 10, 0
msg_vesa_req: db "Requesting VESA...", 13, 10, 0
msg_vesa_det: db "VESA found", 13, 10, 0
msg_vesa_ok:  db "VESA set OK", 13, 10, 0
msg_no_vesa:  db "VESA missing!", 13, 10, 0
msg_no_mode:  db "VESA mode fail!", 13, 10, 0

main:
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ax, 0x9000
    mov ss, ax
    mov sp, 0xFFFF
    mov bp, sp

    mov bx, msg_main
    call print16
    call serial_print

    mov ax, PWD_SRC_SEG
    mov ds, ax
    mov si, PWD_SRC_OFF
    xor ax, ax
    mov es, ax
    mov di, PWD_DST_ADDR
    mov cx, 512
    rep movsb
    xor ax, ax
    mov ds, ax
    mov es, ax

    mov bx, msg_pwd
    call serial_print

    mov bx, msg_vesa_req
    call serial_print

    call detect_vesa
    jnc .v_ok
    mov bx, msg_no_vesa
    call print16
    call serial_print
    jmp $

.v_ok:
    mov bx, msg_vesa_det
    call serial_print

    call set_vesa_mode
    jnc .m_ok
    mov bx, msg_no_mode
    call print16
    call serial_print
    jmp $

.m_ok:
    mov bx, msg_vesa_ok
    call print16
    call serial_print

    call switch_to_pm

    jmp $

[bits 32]
serial32_write:
    push edx
    push eax
    mov dx, 0x3FD
.wait:
    in al, dx
    test al, 0x20
    jz .wait
    mov dx, 0x3F8
    pop eax
    out dx, al
    pop edx
    ret

serial32_puts:
    push eax
.loop:
    mov al, [esi]
    test al, al
    jz .done
    call serial32_write
    inc esi
    jmp .loop
.done:
    pop eax
    ret

init_pm:
    mov ax, DATA_SEG
    mov ds, ax
    mov ss, ax
    mov es, ax
    mov fs, ax
    mov gs, ax

    mov ebp, 0x90000
    mov esp, ebp

    mov esi, msg_pm_ok
    call serial32_puts

BEGIN_PM:
    mov eax, [vbe_pitch]
    push eax
    mov eax, [vbe_bpp]
    push eax
    mov eax, [vbe_height]
    push eax
    mov eax, [vbe_width]
    push eax
    mov eax, [vbe_lfb]
    push eax

    mov esi, msg_call_kernel
    call serial32_puts

    call KERNEL_OFFSET

    mov esi, msg_kernel_ret
    call serial32_puts

    jmp $

msg_pm_ok:         db "PM entered OK", 13, 10, 0
msg_call_kernel:   db "Calling kernel @0x10000", 13, 10, 0
msg_kernel_ret:    db "Kernel returned!", 13, 10, 0