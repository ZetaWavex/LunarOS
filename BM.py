def utf8_encode_raw(text: str) -> str:
    data = b""
    for ch in text:
        code = ord(ch)
        if code <= 0x7F:
            data += bytes([code])
        elif code <= 0x7FF:
            b1 = 0xC0 | (code >> 6)
            b2 = 0x80 | (code & 0x3F)
            data += bytes([b1, b2])
        elif code <= 0xFFFF:
            b1 = 0xE0 | (code >> 12)
            b2 = 0x80 | ((code >> 6) & 0x3F)
            b3 = 0x80 | (code & 0x3F)
            data += bytes([b1, b2, b3])
        elif code <= 0x10FFFF:
            b1 = 0xF0 | (code >> 18)
            b2 = 0x80 | ((code >> 12) & 0x3F)
            b3 = 0x80 | ((code >> 6) & 0x3F)
            b4 = 0x80 | (code & 0x3F)
            data += bytes([b1, b2, b3, b4])
        else:
            raise ValueError(f"不支持字符：{ch}，码点超出 Unicode 范围")
    return data.hex(" ").upper()

def utf8_decode_raw(hex_str: str) -> str:
    clean_hex = hex_str.replace(" ", "").replace("\n", "")
    if len(clean_hex) % 2 != 0:
        raise ValueError("十六进制字符长度必须为偶数")
    try:
        byte_data = bytes.fromhex(clean_hex)
        return byte_data.decode("utf-8")
    except ValueError as e:
        raise ValueError(f"非法十六进制数据：{str(e)}")
    except UnicodeDecodeError:
        raise ValueError("不是合法的 UTF-8 字节流，解码失败")

def main():
    print("DFN 编码器")
    print("1. 编码")
    print("2. 解码")
    print("3. 退出")
    choice = input("请输入你的选择：")
    if choice == "1":
        text = input("请输入要编码的文本：")
        res = utf8_encode_raw(text)
        print("编码后的文本：", res)
    elif choice == "2":
        hex_str = input("请输入要解码的十六进制文本：")
        res = utf8_decode_raw(hex_str)
        print("解码后的文本：", res)
    elif choice == "3":
        print("退出DFN编码器")
    else:
        print("请输入正确的选择")

if __name__ == "__main__":
    main()