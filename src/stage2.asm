KERNEL_OFFSET  equ 0x10000
VBE_INFO_ADDR  equ 0x8000
PWD_SRC_SEG    equ 0x2700
PWD_SRC_OFF    equ 0x0C00
PWD_DST_ADDR   equ 0x1000

PML4_ADDR      equ 0x100000
PDPT_ADDR      equ 0x101000
PD_ADDR        equ 0x102000
PARAM_BLOCK    equ 0x5000

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

setup_page_tables:
    cld
    mov edi, PML4_ADDR
    xor eax, eax
    mov ecx, 6 * 1024
    rep stosd

    mov edi, PML4_ADDR
    mov eax, PDPT_ADDR
    or eax, 0x3
    mov [edi], eax
    mov dword [edi + 4], 0

    mov edi, PDPT_ADDR
    mov eax, PD_ADDR
    or eax, 0x3
    mov ecx, 4
.pdpt:
    mov [edi], eax
    mov dword [edi + 4], 0
    add eax, 0x1000
    add edi, 8
    loop .pdpt

    mov edi, PD_ADDR
    xor eax, eax
    mov ecx, 4 * 512
.pd:
    mov edx, eax
    or edx, 0x83
    mov [edi], edx
    mov dword [edi + 4], 0
    add eax, 0x200000
    add edi, 8
    loop .pd

    mov edi, PD_ADDR + 3 * 0x1000
    mov ecx, 512
.uncached:
    or dword [edi], 0x10
    add edi, 8
    loop .uncached

    ret

enable_long_mode:
    mov esi, msg_lm_req
    call serial32_puts

    lgdt [gdt_descriptor]

    mov eax, cr4
    or eax, 0x620
    mov cr4, eax

    mov eax, PML4_ADDR
    mov cr3, eax

    mov ecx, 0xC0000080
    rdmsr
    or eax, 0x100
    wrmsr

    mov eax, cr0
    or eax, 0x80000001
    mov cr0, eax

    mov esi, msg_lm_ok
    call serial32_puts

    mov edi, PARAM_BLOCK
    mov eax, [vbe_lfb]
    mov [edi + 0], eax
    mov dword [edi + 4], 0
    mov eax, [vbe_width]
    mov [edi + 8], eax
    mov eax, [vbe_height]
    mov [edi + 12], eax
    mov eax, [vbe_bpp]
    mov [edi + 16], eax
    mov eax, [vbe_pitch]
    mov [edi + 20], eax

    jmp CODE64_SEG:KERNEL_OFFSET

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

    call setup_page_tables
    call enable_long_mode

    jmp $

msg_pm_ok:  db "PM entered OK", 13, 10, 0
msg_lm_req: db "Switching to long mode...", 13, 10, 0
msg_lm_ok:  db "Long mode active, jumping kernel", 13, 10, 0