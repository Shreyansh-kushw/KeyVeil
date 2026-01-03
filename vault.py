"""Takes care of the all tasks related to opening and saving the vault"""

from cryptography.fernet import Fernet
import json
import os


def openVault(key: bytes):
    # Create Fernet object using the provided key
    fernet = Fernet(key)
    del key  # Remove key reference from memory

    # If vault file does not exist, return empty vault
    if not os.path.exists("vault.enc"):
        return {}

    else:
        try:
            # Open encrypted vault file
            vaultData = open("vault.enc", "rb")

            # Read encrypted data
            encryptedData = vaultData.read()

            # Decrypt the data
            decrypted = fernet.decrypt(encryptedData)
            del encryptedData  # Clear encrypted data from memory

            vaultData.close()

            # Convert decrypted JSON string back to dictionary
            return json.loads(decrypted.decode())

        except Exception as e:
            # Return None if decryption or loading fails
            return None


def saveVault(key: bytes, vaultData: dict):
    # Create Fernet object using the provided key
    fernet = Fernet(key)
    del key  # Remove key reference from memory

    # Convert vault data to JSON string
    jsonString = json.dumps(vaultData)
    del vaultData  # Remove vault data reference

    # Encrypt the JSON string
    encryptedData = fernet.encrypt(jsonString.encode())
    del jsonString  # Clear plaintext JSON from memory

    try:
        # Write encrypted data to vault file
        with open("vault.enc", "wb") as file:
            file.write(encryptedData)

        del encryptedData  # Clear encrypted data from memory

    except Exception as e:
        # Print error if writing to file fails
        print(f"Error loading vault.\n{e}")
