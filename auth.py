# Importing necessary modules #

import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import uuid
import hashlib
import platform
import os
import subprocess

# --------------------------- #

newUser = False

# ---------- Main Funtions ----------#


def get_machine_id():
    system = platform.system()
    if system == "Windows":
        # Windows MachineGuid
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return value
    elif system == "Linux":
        # Linux machine-id
        with open("/etc/machine-id", "r") as f:
            return f.read().strip()
    elif system == "Darwin":
        # macOS hardware UUID
        return (
            subprocess.check_output(
                "ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID", shell=True
            )
            .decode()
            .split('"')[-2]
        )
    else:
        return str(uuid.getnode())  # fallback to MAC


def get_fingerprint():
    raw_id = get_machine_id()
    return hashlib.sha256(raw_id.encode()).hexdigest()


def getSalt():
    """Gets the salt for generating the key"""

    global Authorised

    try:
        f = open("salt.bin", "rb")  # tries opening the salt file if it exists
        salt = f.read()
        f.close()
        fingerprint = salt[64:]
        if fingerprint != (get_fingerprint()).encode():
            Authorised = False
        else:
            Authorised = True

    except:

        """Generates the salt if not found."""
        fingerprint = (get_fingerprint()).encode()
        salt = os.urandom(64) + fingerprint
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
        iterations=1000000,  # Slows down brute-force
    )

    del salt
    pin_encoded = pin.encode()  # pin is encoded into binary

    del pin
    key = kdf.derive(pin_encoded)
    del pin_encoded  # deletes the encoded pin from memory

    return base64.urlsafe_b64encode(key)  # returns the base64 version of the key


# -----------------------------------#
