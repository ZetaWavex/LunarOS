disk_fail:
    mov si, msg_disk
    call print16
    jmp $
msg_disk: db "Disk I/O error!", 13, 10, 0

load_kernel:
    pusha
    mov si, DAPACK
    mov [DAPACK.addr], word KERNEL_OFFSET
    mov [DAPACK.addr+2], word 0
    mov [DAPACK.lba], dword 1
    mov [DAPACK.count], word KERNEL_SECTORS
    mov dl, [BOOT_DRIVE]
    mov ah, 0x42
    int 0x13
    jc disk_fail
    popa
    ret

DAPACK:
    db 16
    db 0
.count: dw 0
.addr:  dd 0
.lba:   dq 0