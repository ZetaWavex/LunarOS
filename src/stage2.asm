KERNEL_OFFSET  equ 0x10000
VBE_INFO_ADDR  equ 0x8000
VESA_MODE      equ 0x114
BOOT_DRV       equ 0x7DFE

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
msg_lba:      db "Reading kernel...", 13, 10, 0
msg_kern_ok:  db "Kernel loaded", 13, 10, 0
msg_kern_fail: db "Kernel load FAIL err=", 0
msg_vesa_req: db "Requesting VESA...", 13, 10, 0
msg_vesa_det: db "VESA found", 13, 10, 0
msg_vesa_ok:  db "VESA set OK", 13, 10, 0
msg_no_vesa:  db "VESA missing!", 13, 10, 0
msg_no_mode:  db "VESA mode fail!", 13, 10, 0

boot_err: db 0

read_lba:   dd 0
read_addr:  dd 0
read_count: dw 0

kDAPACK:
    db 16
    db 0
.count: dw 0
.addr:  dd 0
.lba:   dq 0

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

    mov bx, msg_lba
    call serial_print

    mov dl, [BOOT_DRV]

    mov word [read_lba], K_LBA
    mov word [read_lba+2], 0
    mov word [read_addr], KERNEL_OFFSET & 0xFFFF
    mov word [read_addr+2], KERNEL_OFFSET >> 16
    mov ecx, KERNEL_SECTORS

.read_loop:
    cmp ecx, 128
    jbe .read_tail
    mov word [read_count], 128
    sub ecx, 128
    jmp .read_do

.read_tail:
    mov [read_count], cx
    xor ecx, ecx

.read_do:
    mov si, kDAPACK
    mov eax, [read_addr]
    mov edx, eax
    shr eax, 4
    mov [kDAPACK.addr+2], ax
    and edx, 0x0F
    mov [kDAPACK.addr], dx
    mov eax, [read_lba]
    mov [kDAPACK.lba], eax
    mov ax, [read_count]
    mov [kDAPACK.count], ax
    mov dl, [BOOT_DRV]
    mov ah, 0x42
    int 0x13
    jnc .read_next

    mov [boot_err], ah
    mov bx, msg_kern_fail
    call print16
    call serial_print
    jmp $

.read_next:
    movzx ax, word [read_count]
    movzx edx, ax
    shl edx, 9
    add [read_addr], edx
    adc word [read_addr+2], 0
    movzx eax, word [read_count]
    add [read_lba], eax
    adc word [read_lba+2], 0
    or ecx, ecx
    jnz .read_loop

.k_ok:
    mov bx, msg_kern_ok
    call print16
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