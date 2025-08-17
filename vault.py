from cryptography.fernet import Fernet
import json
import os
import auth


def openVault(key: bytes):

    fernet = Fernet(key)
    del key

    if not os.path.exists("vault.enc"):

        return {}

    else:

        try:
            vaultData = open("vault.enc", "rb")
            encryptedData = vaultData.read()
            decrypted = fernet.decrypt(encryptedData)
            del encryptedData
            vaultData.close()

            return json.loads(decrypted.decode())

        except Exception as e:

            return None




def saveVault(key: bytes, vaultData: dict):

    fernet = Fernet(key)
    del key
    jsonString = json.dumps(vaultData)
    del vaultData
    encryptedData = fernet.encrypt(jsonString.encode())
    del jsonString

    try:

        with open("vault.enc", "wb") as file:
            file.write(encryptedData)
        del encryptedData

    except Exception as e:

        print(f"Error loading vault.\n{e}")
        # traceback.print_exc()
