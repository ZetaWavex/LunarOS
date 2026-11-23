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
    sub rsp, 48

    mov eax, [abs PARAM_BLOCK + 20]
    mov [rsp + 32], rax

    mov rcx, [abs PARAM_BLOCK + 0]
    mov edx, [abs PARAM_BLOCK + 8]
    mov r8d, [abs PARAM_BLOCK + 12]
    mov r9d, [abs PARAM_BLOCK + 16]

    call kernel_main

.halt:
    cli
    hlt
    jmp .halt

delay_asm:
    mov eax, ecx
.loop:
    dec eax
    jnz .loop
    ret