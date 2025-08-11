from cryptography.fernet import Fernet
import json
import os

def openVault(key: bytes):

    fernet = Fernet(key)

    if not os.path.exists("vault.enc"):
    
        return {}

    else:
        try:
            
            vaultData = open("vault.enc","rb") 
            encryptedData = vaultData.read()
            decrypted = fernet.decrypt(encryptedData)
            vaultData.close()
            
            return json.loads(decrypted.decode())
        
        except Exception as e:

            # print(f"Error loading vault.\n{e}")
            # print("Incorrect password or vault corrupted!")  
            # traceback.print_exc()
            # print("no vaulting")
            return None
        
    
def saveVault(key: bytes, vaultData: dict):

    fernet = Fernet(key)
    jsonString = json.dumps(vaultData)
    encryptedData = fernet.encrypt(jsonString.encode())

    try:

        with open("vault.enc", "wb") as file:
            file.write(encryptedData)
    
    except Exception as e:      

            print(f"Error loading vault.\n{e}")
            # traceback.print_exc()