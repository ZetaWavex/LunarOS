[BITS 32]
[GLOBAL start]
[GLOBAL delay_asm]
[EXTERN kernel_main]

start:
    jmp kernel_main

delay_asm:
    push ebx
    mov ebx, [esp+8]
.loop:
    dec ebx
    jnz .loop
    pop ebx
    ret