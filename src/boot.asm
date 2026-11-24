[org 0x7c00]
[bits 16]

STAGE2_SEG   equ 0x0900
STAGE2_LBA   equ 10
STAGE2_SECT  equ 10

KERNEL_DST   equ 0x10000
KERNEL_LBA   equ 66
KERNEL_SECT  equ 190

PWD_DST      equ 0x27C00
PWD_LBA      equ 256
PWD_SECT     equ 1

cli
xor ax, ax
mov ds, ax
mov es, ax
mov ss, ax
mov sp, 0x7C00
sti

mov [boot_drive], dl

mov ax, STAGE2_SEG
mov es, ax
mov bx, 0x10
mov ax, [es:bx]
cmp ax, 0x4E4C
je .loaded

xor ax, ax
mov es, ax

mov eax, STAGE2_LBA
mov cx, STAGE2_SECT
mov edi, STAGE2_SEG << 4
call load_linear

mov eax, KERNEL_LBA
mov cx, KERNEL_SECT
mov edi, KERNEL_DST
call load_linear

mov eax, PWD_LBA
mov cx, PWD_SECT
mov edi, PWD_DST
call load_linear

.loaded:
mov dl, [boot_drive]
jmp STAGE2_SEG:0x0000

load_linear:
    mov [ld_lba], eax
    mov [ld_cnt], cx
    mov [ld_dst], edi
.loop:
    mov cx, [ld_cnt]
    test cx, cx
    jz .done

    mov ebx, [ld_dst]
    and ebx, 0xFFFF
    mov edx, 0x10000
    sub edx, ebx
    shr edx, 9
    cmp cx, dx
    jbe .page_ok
    mov cx, dx
.page_ok:
    cmp cx, 64
    jbe .chunk_ok
    mov cx, 64
.chunk_ok:
    mov [dap_cnt], cx

    mov eax, [ld_dst]
    mov edx, eax
    shr eax, 4
    mov [dap_seg], ax
    and edx, 0x0F
    mov [dap_off], dx

    mov eax, [ld_lba]
    mov [dap_lba], eax
    mov dword [dap_lba + 4], 0

    mov si, dap
    mov dl, [boot_drive]
    mov ah, 0x42
    int 0x13
    jc .err

    movzx eax, word [dap_cnt]
    mov edx, eax
    shl edx, 9
    add [ld_dst], edx
    add [ld_lba], eax
    sub [ld_cnt], ax
    jmp .loop
.done:
    ret
.err:
    mov si, msg_err
    call print
    jmp $

print:
    pusha
    mov ah, 0x0E
.next:
    mov al, [si]
    test al, al
    jz .end
    int 0x10
    inc si
    jmp .next
.end:
    popa
    ret

boot_drive: db 0
ld_lba:     dd 0
ld_cnt:     dw 0
ld_dst:     dd 0

dap:
    db 16
    db 0
dap_cnt:    dw 0
dap_off:    dw 0
dap_seg:    dw 0
dap_lba:    dq 0

msg_err: db "Disk read error!", 13, 10, 0

times 510 - ($ - $$) db 0
dw 0xaa55