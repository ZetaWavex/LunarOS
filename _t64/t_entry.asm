[BITS 64]
[GLOBAL start]
[EXTERN kernel_main]

section .text.start
start:
    call kernel_main
    jmp $