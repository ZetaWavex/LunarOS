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

    mov rcx, [PARAM_BLOCK + 0]
    mov rdx, [PARAM_BLOCK + 4]
    mov r8,  [PARAM_BLOCK + 8]
    mov r9,  [PARAM_BLOCK + 12]

    sub rsp, 0x30
    mov eax, [PARAM_BLOCK + 16]
    mov [rsp + 0x20], rax
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