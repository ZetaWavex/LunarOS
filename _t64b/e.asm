[BITS 64]
[GLOBAL start]
[EXTERN add]
section .text.start
start:
    mov rsp, 0x90000
    call add
    jmp $
