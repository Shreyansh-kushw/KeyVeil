# Importing necessary modules #

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# --------------------------- #

newUser = False

# ---------- Main Funtions ----------#


def getSalt():
    """Gets the salt for generating the key"""

    try:
        f = open("salt.bin", "rb")  # tries opening the salt file if it exists
        salt = f.read()
        f.close()

    except:

        """Generates the salt if not found."""

        salt = os.urandom(16)
        with open("salt.bin", "wb") as f:
            f.write(salt)
        os.chmod("salt.bin", 0o600)

    return salt


def genKey(pin, salt):
    """Generates the key and converts it into base64 (from binary) and return it"""
    """Here we are returning base64 key because FERNET which is used for encryption of the vault requires a base64 key"""

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),  # Secure hash function
        length=32,  # 32-byte key = AES-256
        salt=salt,  # Random salt
        iterations=200000,  # Slows down brute-force
    )

    pin_encoded = pin.encode()  # pin is encoded into binary

    key = kdf.derive(pin_encoded)
    del pin_encoded  # deletes the encoded pin from memory

    return base64.urlsafe_b64encode(key)  # returns the base64 version of the key


# -----------------------------------#
