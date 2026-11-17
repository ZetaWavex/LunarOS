import random
import hashlib

def dfn_encode(text, salt):
    hashed_text = hashlib.sha256(text.encode()).hexdigest()
    encrypted_text = hashed_text + str(salt)
    return encrypted_text

def dfn_decode(encrypted_text):
    salt = int(encrypted_text[-1])
    hashed_text = encrypted_text[:-1]
    decoded_text = hashlib.sha256(hashed_text.encode()).hexdigest()
    return decoded_text

def main():
    while True:
        print("DFN 编码器")
        print("1. 编码")
        print("2. 解码")
        print("3. 退出")
        choice = input("请输入你的选择：")
        if choice == "1":
            text = input("请输入要编码的文本：")
            salt = random.randint(1, 100)
            encrypted_text = dfn_encode(text, salt)
            print("编码后的文本：", encrypted_text)
        elif choice == "2":
            encrypted_text = input("请输入要解码的文本：")
            decoded_text = dfn_decode(encrypted_text)
            print("解码后的文本：", decoded_text)
        elif choice == "3":
            print("退出DFN编码器")
            break
        else:
            print("请输入正确的选择")

if __name__ == "__main__":
    main()