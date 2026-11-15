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
    mov dx, 0x3f8
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