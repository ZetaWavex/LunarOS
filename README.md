# LunarOS

LunarOS 是一个用于学习和实验的自制 32 位 x86 操作系统。它包含自定义 MBR、两阶段启动流程、保护模式内核，以及一个基于 VESA/VBE 的图形登录界面和桌面。

## 功能

- BIOS MBR 引导及 Stage 2 加载
- 从实模式切换到 32 位保护模式
- VESA/VBE 图形模式与 16/24/32 位色支持
- 自定义启动动画和中文/ASCII 字体绘制
- 数字密码登录，密码以 SHA-256 摘要形式保存在磁盘中
- PS/2 鼠标与键盘输入
- 可缩放的桌面窗口、最大化、最小化和关闭控件
- 屏幕键盘
- 重启和通过 ACPI/QEMU I/O 端口关机
- 串口调试输出到 `COM1`

默认密码是 `1234`。

## 项目结构

```text
src/
  boot.asm          MBR 引导扇区
  stage2.asm        二阶段加载器
  gdt.asm           全局描述符表
  vesa.asm          VBE/VESA 模式查询与设置
  kernel_entry.asm  保护模式内核入口
  kernel.c          登录界面、桌面和设备输入逻辑
  graphics.c        帧缓冲和图形绘制
  *.h               字体、Logo 和图形资源

build.py            编译并生成磁盘镜像
run.py              构建并使用 QEMU 启动
convert.py          将 Logo PNG 转为 C 头文件
generate_*_font.py  字体资源生成脚本
build/              生成的引导区、内核和磁盘镜像
Program/            项目使用的 NASM、MinGW 和 QEMU 工具
```

## 环境要求

- Windows
- Python 3
- NASM
- MinGW-w64 GCC 和 objcopy
- QEMU

仓库已包含常用工具目录，但构建脚本中的编译器和 NASM 路径可能需要按本机环境调整：

```python
NASM = r"d:\NewX\OS\Try 5\Program\NASM\nasm.exe"
MINGW_BIN = r"D:\NewX\OS\Try 5\Program\MinGW64\bin"
```

## 构建

在项目根目录执行：

```powershell
python build.py
```

构建成功后会生成：

```text
build/boot.bin
build/stage2.bin
build/kernel.bin
build/os-image.img
```

## 运行

直接构建并启动：

```powershell
python run.py
```

也可以只启动已经生成的镜像：

```powershell
.\Program\QEMU\qemu-system-i386.exe -vga std -drive format=raw,file=build\os-image.img
```

## 磁盘布局

生成的 `os-image.img` 使用 512 字节扇区：

| 内容 | 起始扇区 |
| --- | --- |
| MBR 引导扇区 | LBA 0 |
| Stage 2 | LBA 1 |
| 内核 | LBA 11 |
| SHA-256 密码摘要 | LBA 256 |

密码摘要由 `build.py` 使用默认密码生成并写入镜像，无需明文存储。

## 修改或设置密码

修改 `build.py` 顶部的：

```python
DEFAULT_PASSWORD = "1234"
```

然后重新运行构建：

```powershell
python build.py
```

登录界面只接受数字输入，密码长度最大为 24 个字符。

## 调试

内核会在串口输出启动、登录和系统事件。常用串口设置为 `COM1`、`115200 8N1`。可在 QEMU 中使用：

```powershell
-serial stdio
```

例如：

```powershell
.\Program\QEMU\qemu-system-i386.exe -vga std -serial stdio -drive format=raw,file=build\os-image.img
```

## 注意事项

- 项目面向 PC BIOS/x86 环境，不是多任务操作系统。
- 内核直接操作硬件，建议优先在虚拟机中运行。
- 关机和重启行为依赖模拟器或主板提供的电源管理接口。
