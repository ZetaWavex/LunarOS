[BITS 64]
[GLOBAL start]
[GLOBAL delay_asm]
[EXTERN kernel_main]

PARAM_BLOCK equ 0x5000

section .text.start
start:
    cli
    mov ax, 0x20
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov fs, ax
    mov gs, ax

    mov rsp, 0x90000
    xor rbp, rbp

    mov rdi, [PARAM_BLOCK + 0]
    mov esi, [PARAM_BLOCK + 8]
    mov edx, [PARAM_BLOCK + 12]
    mov ecx, [PARAM_BLOCK + 16]
    mov r8d, [PARAM_BLOCK + 20]

    call kernel_main

.halt:
    cli
    hlt
    jmp .halt

delay_asm:
    mov ecx, edi
.loop:
    dec ecx
    jnz .loop
    ret