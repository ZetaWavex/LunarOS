OUTPUT_FORMAT("pe-x86-64")
ENTRY(start)
SECTIONS
{
    . = 0x10000;
    .text : { *(.text.start) *(.text*) }
    .rdata : { *(.rdata*) *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) *(COMMON) }
}