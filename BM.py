import random
import hashlib

def dfn_encode(text, key):
    # 生成随机 salt 值
    salt = random.randint(1, 100)
    # 使用 SHA-256 进行散列
    hashed_text = hashlib.sha256(text.encode()).hexdigest()
    # 使用 salt 值进行加密
    encrypted_text = hashed_text + str(salt)
    return encrypted_text

def dfn_decode(encrypted_text):
    # 分离 salt 值
    salt = int(encrypted_text[-1])
    # 使用 SHA-256 进行反散列
    hashed_text = encrypted_text[:-1]
    decoded_text = hashlib.sha256(hashed_text.encode()).hexdigest()
    return decoded_text

def main():
    text = input("请输入要编码的文本：")
    key = int(input("请输入编码密钥："))
    encrypted_text = dfn_encode(text, key)
    print("编码后的文本：", encrypted_text)
    decoded_text = dfn_decode(encrypted_text)
    print("解码后的文本：", decoded_text)

if __name__ == "__main__":
    main()