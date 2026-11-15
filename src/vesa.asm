vbe_lfb:   dd 0
vbe_width: dd 0
vbe_height: dd 0
vbe_bpp:   dd 0
vbe_pitch: dd 0

detect_vesa:
    push es
    push di
    mov ax, VBE_INFO_ADDR >> 4
    mov es, ax
    mov di, 0
    mov ax, 0x4f00
    int 0x10
    cmp ax, 0x004f
    jne .no_vesa
    clc
    pop di
    pop es
    ret
.no_vesa:
    stc
    pop di
    pop es
    ret

set_vesa_mode:
    push es
    push di
    mov ax, VBE_INFO_ADDR >> 4
    mov es, ax
    mov di, 0
    mov cx, VESA_MODE
    mov ax, 0x4f01
    int 0x10
    cmp ax, 0x004f
    jne .fail

    mov eax, [es:di + 40]
    mov [vbe_lfb], eax
    mov ax, [es:di + 18]
    mov [vbe_width], ax
    mov ax, [es:di + 20]
    mov [vbe_height], ax
    mov al, [es:di + 25]
    movzx eax, al
    mov [vbe_bpp], eax
    mov ax, [es:di + 16]
    mov [vbe_pitch], ax

    mov bx, VESA_MODE | 0x4000
    mov ax, 0x4f02
    int 0x10
    cmp ax, 0x004f
    jne .fail

    clc
    pop di
    pop es
    ret
.fail:
    stc
    pop di
    pop es
    ret