[org 0x7c00]
[bits 16]

STAGE2_SEG equ 0x0900

cli
xor ax, ax
mov ds, ax
mov es, ax
mov ss, ax
mov sp, 0x7C00
sti

mov dl, 0x80

jmp STAGE2_SEG:0x0000

times 510 - ($ - $$) db 0
dw 0xaa55