[bits 16]

DISK_LBA:   dd 0
DISK_ADDR:  dd 0
DISK_CNT:   dw 0
DISK_ERR:   db 0
GEO_SPT:    db 0
GEO_HEADS:  db 0
CYL:        dw 0
HEAD:       dw 0
SEC:        dw 0

DISK_DAP:
    db 16
    db 0
.dap_cnt: dw 0
.dap_off: dw 0
.dap_seg: dw 0
.dap_lba: dq 0

disk_read:
    pusha
    mov [DISK_LBA], eax
    mov [DISK_ADDR], ebx
    mov [DISK_CNT], cx
.ext_loop:
    movzx ecx, word [DISK_CNT]
    test ecx, ecx
    jz .ok
    mov eax, [DISK_ADDR]
    and eax, 0xFFFF
    mov edx, 0x10000
    sub edx, eax
    shr edx, 9
    cmp ecx, edx
    jbe .ext_lim
    mov ecx, edx
.ext_lim:
    cmp ecx, 128
    jbe .ext_cnt
    mov ecx, 128
.ext_cnt:
    mov [DISK_DAP.dap_cnt], cx
    mov eax, [DISK_ADDR]
    mov edx, eax
    shr eax, 4
    mov [DISK_DAP.dap_seg], ax
    and edx, 0x0F
    mov [DISK_DAP.dap_off], dx
    mov eax, [DISK_LBA]
    mov [DISK_DAP.dap_lba], eax
    mov dword [DISK_DAP.dap_lba+4], 0
    mov dl, [BOOT_DRV]
    mov si, DISK_DAP
    mov ah, 0x42
    int 0x13
    jc .chs
    movzx eax, word [DISK_DAP.dap_cnt]
    mov edx, eax
    shl edx, 9
    add [DISK_ADDR], edx
    add [DISK_LBA], eax
    sub [DISK_CNT], ax
    jmp .ext_loop
.chs:
    call chs_read
    jc .fail
.ok:
    clc
    popa
    ret
.fail:
    mov [DISK_ERR], ah
    stc
    popa
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

chs_read:
    pusha
    call chs_geom
.loop:
    mov ax, [DISK_CNT]
    test ax, ax
    jz .ok
    movzx ecx, byte [GEO_SPT]
    movzx ebx, byte [GEO_HEADS]
    imul ebx, ecx
    mov eax, [DISK_LBA]
    xor edx, edx
    div ebx
    mov [CYL], ax
    mov eax, edx
    xor edx, edx
    div ecx
    mov [HEAD], ax
    inc edx
    mov [SEC], dx
    mov eax, [DISK_ADDR]
    mov edx, eax
    shr eax, 4
    mov es, ax
    and edx, 0x0F
    mov bx, dx
    mov ax, [CYL]
    mov ch, al
    mov ax, [SEC]
    mov cl, al
    mov ax, [HEAD]
    mov dh, al
    mov dl, [BOOT_DRV]
    mov ax, 0x0201
    int 0x13
    jc .fail
    add dword [DISK_ADDR], 512
    inc dword [DISK_LBA]
    dec word [DISK_CNT]
    jmp .loop
.ok:
    clc
    popa
    ret
.fail:
    mov [DISK_ERR], ah
    stc
    popa
    ret