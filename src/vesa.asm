VBE_MODE_INFO_ADDR equ 0x7000
VBE_FALLBACK_MODE  equ 0x114
TARGET_AREA        equ 2073600
BPP24_PENALTY      equ 500000

vbe_lfb:   dd 0
vbe_width: dd 0
vbe_height: dd 0
vbe_bpp:   dd 0
vbe_pitch: dd 0

mode_list_off: dw 0
mode_list_seg: dw 0
mode_cursor:   dw 0

cur_mode:  dw 0
cur_w:     dw 0
cur_h:     dw 0
cur_score: dd 0

best_mode:  dw 0
best_w:     dw 0
best_h:     dw 0
best_bpp:   dw 0
best_pitch: dw 0
best_lfb:   dd 0
best_score: dd 0

msg_vbe_mode: db "VBE mode ", 0
msg_vbe_x:    db "x", 0
msg_vbe_bpp:  db " bpp ", 0
msg_vbe_none: db "VBE no match, fallback", 13, 10, 0

detect_vesa:
    push es
    push di
    mov ax, VBE_INFO_ADDR >> 4
    mov es, ax
    xor di, di
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

serial_char:
    push dx
    push ax
    mov dx, 0x3fd
.sb:
    in al, dx
    test al, 0x20
    jz .sb
    mov dx, 0x3f8
    pop ax
    out dx, al
    pop dx
    ret

serial_num16:
    pusha
    movzx eax, ax
    xor cx, cx
.digit:
    xor edx, edx
    mov ebx, 10
    div ebx
    push edx
    inc cx
    test eax, eax
    jnz .digit
.emit:
    pop eax
    add al, '0'
    call serial_char
    loop .emit
    popa
    ret

mode_pitch:
    mov ax, [VBE_INFO_ADDR + 4]
    cmp ax, 0x0300
    jb .legacy
    mov ax, [es:di + 50]
    test ax, ax
    jz .legacy
    ret
.legacy:
    mov ax, [es:di + 16]
    ret

set_vesa_mode:
    pusha
    push es

    mov ax, [VBE_INFO_ADDR + 14]
    mov [mode_list_off], ax
    mov ax, [VBE_INFO_ADDR + 16]
    mov [mode_list_seg], ax

    mov dword [best_score], 0x7FFFFFFF
    mov word [best_mode], 0xFFFF
    mov word [best_w], 0
    mov word [best_h], 0
    mov word [best_bpp], 0
    mov word [best_pitch], 0
    mov dword [best_lfb], 0

    mov si, [mode_list_off]
    mov word [mode_cursor], 0

.next:
    mov ax, [mode_list_seg]
    mov es, ax
    mov ax, [es:si]
    add si, 2
    mov [mode_cursor], si
    cmp ax, 0xFFFF
    je .scan_done
    mov [cur_mode], ax

    mov ax, VBE_MODE_INFO_ADDR >> 4
    mov es, ax
    xor di, di
    mov cx, [cur_mode]
    mov ax, 0x4f01
    int 0x10
    mov si, [mode_cursor]
    cmp ax, 0x004f
    jne .next

    mov ax, [es:di + 0]
    test ax, 0x0001
    jz .next
    test ax, 0x0010
    jz .next
    test ax, 0x0080
    jz .next

    movzx eax, byte [es:di + 25]
    cmp eax, 24
    jb .next
    cmp eax, 32
    ja .next

    mov ax, [es:di + 18]
    mov [cur_w], ax
    mov ax, [es:di + 20]
    mov [cur_h], ax
    cmp word [cur_w], 640
    jb .next
    cmp word [cur_h], 480
    jb .next

    movzx eax, word [cur_w]
    imul eax, 9
    movzx ebx, word [cur_h]
    imul ebx, 16
    sub eax, ebx
    jns .ar_ok
    neg eax
.ar_ok:
    imul eax, 1000

    movzx ecx, word [cur_w]
    movzx edx, word [cur_h]
    imul ecx, edx
    sub ecx, TARGET_AREA
    jns .ar2_ok
    neg ecx
.ar2_ok:
    add eax, ecx
    mov [cur_score], eax

    cmp eax, [best_score]
    jae .next

    mov [best_score], eax
    mov ax, [cur_mode]
    mov [best_mode], ax
    mov ax, [cur_w]
    mov [best_w], ax
    mov ax, [cur_h]
    mov [best_h], ax
    mov al, [es:di + 25]
    movzx eax, al
    mov [best_bpp], ax
    call mode_pitch
    mov [best_pitch], ax
    mov eax, [es:di + 40]
    mov [best_lfb], eax
    jmp .next

.scan_done:
    cmp word [best_mode], 0xFFFF
    jne .apply

    mov bx, msg_vbe_none
    call serial_print
    mov word [best_mode], VBE_FALLBACK_MODE
    mov ax, VBE_MODE_INFO_ADDR >> 4
    mov es, ax
    xor di, di
    mov cx, VBE_FALLBACK_MODE
    mov ax, 0x4f01
    int 0x10
    cmp ax, 0x004f
    jne .fail
    mov ax, [es:di + 18]
    mov [best_w], ax
    mov ax, [es:di + 20]
    mov [best_h], ax
    mov al, [es:di + 25]
    movzx eax, al
    mov [best_bpp], ax
    call mode_pitch
    mov [best_pitch], ax
    mov eax, [es:di + 40]
    mov [best_lfb], eax

.apply:
    mov bx, [best_mode]
    or bx, 0x4000
    xor cx, cx
    mov ax, 0x4f02
    int 0x10
    cmp ax, 0x004f
    jne .fail

    mov eax, [best_lfb]
    mov [vbe_lfb], eax
    mov ax, [best_w]
    mov [vbe_width], ax
    mov ax, [best_h]
    mov [vbe_height], ax
    movzx eax, word [best_bpp]
    mov [vbe_bpp], eax
    mov ax, [best_pitch]
    mov [vbe_pitch], ax

    pop es

    mov bx, msg_vbe_mode
    call serial_print
    mov ax, [best_w]
    call serial_num16
    mov bx, msg_vbe_x
    call serial_print
    mov ax, [best_h]
    call serial_num16
    mov al, ' '
    call serial_char
    mov ax, [best_bpp]
    call serial_num16
    mov bx, msg_vbe_bpp
    call serial_print
    mov al, 13
    call serial_char
    mov al, 10
    call serial_char

    popa
    clc
    ret

.fail:
    pop es
    popa
    stc
    ret