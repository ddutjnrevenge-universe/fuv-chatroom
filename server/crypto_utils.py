# crypto_utils.py
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import os
import base64
from dotenv import load_dotenv

# Load from .env
load_dotenv()

AES_KEY_HEX = os.getenv("AES_KEY")
if not AES_KEY_HEX:
    raise ValueError("AES_KEY not found in environment variables.")

AES_KEY = bytes.fromhex(AES_KEY_HEX)
if len(AES_KEY) != 32:
    raise ValueError("AES_KEY must be 32 bytes (256-bit).")

def encrypt_message(message: str) -> str:
    iv = os.urandom(16)  # AES block size is 16 bytes
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return base64.b64encode(iv + ciphertext).decode()

def decrypt_message(ciphertext_b64: str) -> str:
    data = base64.b64decode(ciphertext_b64.encode())
    iv = data[:16]
    ciphertext = data[16:]

    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext.decode()
