import os, base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding

# AES part

def generate_aes_key():
    return os.urandom(32)  # 256-bit random key

def encrypt_aes(aes_key, message: str) -> str:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return base64.b64encode(iv + ciphertext).decode()

def decrypt_aes(aes_key, ciphertext_b64: str) -> str:
    data = base64.b64decode(ciphertext_b64.encode())
    iv = data[:16]
    ciphertext = data[16:]

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext.decode()

# RSA part

def load_rsa_public_key(filepath):
    with open(filepath, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    return public_key

def load_rsa_private_key(filepath):
    with open(filepath, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key

def encrypt_rsa(public_key, data: bytes) -> bytes:
    return public_key.encrypt(
        data,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def decrypt_rsa(private_key, ciphertext: bytes) -> bytes:
    return private_key.decrypt(
        ciphertext,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
