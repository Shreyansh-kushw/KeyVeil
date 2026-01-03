"""Takes care of all the CRUD operations, backup and restore operations to be performed on the vault"""

# Importing modules

import traceback
import secrets
import string
import os
import datetime
import questionary
import zipfile
import auth
import vault
import pydoc

from pyautogui import confirm, alert
from tabulate import tabulate


PINchanged = False

# ----------- All Main Functions -------------- #


def add_entry(vault: dict, name: str, site: str, username: str, password: str) -> None:
    """Adds entry to the vault"""

    name = name.lower()
    if name not in vault:
        vault[name] = []  # Initialize as a list

    (vault[name]).append({"url": site, "username": username, "password": password})


def restoreBackup(directory, backup_file):
    """Restores the backup selected"""

    response = confirm(
        text="This will overwrite the current vault",
        title="Confirmation",
        buttons=["Yes", "No"],
    )
    if response == "Yes":
        with zipfile.ZipFile(f"""{directory}\{backup_file}""", "r") as zip_ref:
            for member in zip_ref.namelist():
                target_path = os.path.join(member)

                # Extract and overwrite
                with zip_ref.open(member) as source_file, open(
                    target_path, "wb"
                ) as target_file:
                    target_file.write(source_file.read())

        return

    else:
        return


def backUp(destination="""backup folder""") -> None:
    """Creates a backup"""

    if not os.path.exists(destination):
        os.makedirs(destination)

    time = ((str(datetime.datetime.now())).replace(":", "-")).replace(".", "-")

    # Create a new zip file
    with zipfile.ZipFile(
        os.path.join(destination, f"""backup_{time}.zip"""), "w", zipfile.ZIP_DEFLATED
    ) as myzip:
        # Add an existing file
        myzip.write("vault.enc")
        myzip.write("salt.bin")

    print(f"Backup successful in {destination}/")


def delete_entry(vault: dict, site: str, username: str, confirmation=True) -> bool:
    """Deletes an entry from the vault"""

    site = site.lower()

    if confirmation:
        choice = confirm(
            text="This action is irreversible.",
            title="Warning!",
            buttons=["OK", "Cancel"],
        )

    else:
        choice = "OK"

    if choice == "OK":

        if site in vault.keys():

            # del vault[site]
            for index, creds in enumerate(vault[site]):

                if creds["username"] == username:
                    (vault[site]).pop(index)
                    print("deleted")
                    break

            return True

        else:
            # print("Site not in entries.")
            return False

    else:
        return False


def edit_entry(vault: dict, site: str, username: str = None, password: str = None):
    """Edits and updates the entry in the vault"""

    site = site.lower()

    if site in vault.keys():

        try:
            if username != None:
                vault[site].update({"username": username})
            if password != None:
                vault[site].update({"password": password})

            return True

        except Exception as e:

            # print("Error occurred in editing entries!\n{}".format(e))
            traceback.print_exc()

    else:

        alert(text="No such entry in database.", title="Error", button="OK")


def search_entries(vault: dict, keyword: str) -> dict:
    """Searching among all the entries in the vault"""

    keyword = keyword.lower()
    search_results = {}

    for site in list(vault.keys()):
        if keyword in site:
            search_results.update({site: vault[site]})

    return search_results


def show_search_passwords(vault, search_results):
    """Returns the seach results"""

    serial = 1
    search_Data = []

    for site, creds in search_results.items():
        search_Data.append([serial, site, creds["username"]])
        serial += 1

    pydoc.pager(
        tabulate(
            search_Data, headers=["S. No", "Site", "Username"], tablefmt="fancy_grid"
        )
    )
    print("\nKindly press ctrl + - for better view.\n")

    choice = questionary.select(
        "Choose an option", choices=["Access password", "Back to menu"], qmark=""
    ).ask()

    if choice == "Access password":
        while True:

            try:

                password_code = int(input("Enter S. No of the password to access:"))
                if password_code > serial or password_code < 1:
                    print("Please enter a valid number")
                    continue
                else:
                    break
            except ValueError:
                print("Please enter a valid number")
                continue

            except Exception as e:
                print("The following error occured", e)
                return

        os.system("cls")

        site_name = (search_Data[password_code - 1])[1]
        site_data = search_entries(vault, site_name)
        site_DATA = []
        for site, creds in site_data.items():
            site_DATA.append([site, creds["username"], creds["password"]])

        print(
            tabulate(
                site_DATA,
                headers=["Site", "Username", "Password"],
                tablefmt="fancy_grid",
            )
        )
        input("Press enter to continue:")
        os.system("cls")

        return

    else:
        os.system("cls")
        return


def show_entries(vault) -> None:

    os.system("cls")
    if not vault:
        print("The vault is empty! Add some stuff in there!")

    else:
        access_code = 1
        table_data = []
        for site, creds in vault.items():
            table_data.append([access_code, site, creds["username"]])
            access_code += 1

        pydoc.pager(
            tabulate(
                table_data, headers=["S. No", "Site", "Username"], tablefmt="fancy_grid"
            )
        )

        print("\nKindly press ctrl + - for better view.\n")

        choice = questionary.select(
            "Choose an option", choices=["Access password", "Back to menu"], qmark=""
        ).ask()

        if choice == "Access password":

            while True:

                try:

                    password_code = int(input("Enter S. No of the password to access:"))
                    if password_code > access_code or password_code < 1:
                        print("Please enter a valid number")
                        continue
                    else:
                        break
                except ValueError:
                    print("Please enter a valid number")
                    continue

                except Exception as e:
                    print("The following error occured", e)
                    return

            os.system("cls")

            site_name = (table_data[password_code - 1])[1]
            site_data = search_entries(vault, site_name)
            site_DATA = []
            for site, creds in site_data.items():
                site_DATA.append([site, creds["username"], creds["password"]])

            print(
                tabulate(
                    site_DATA,
                    headers=["Site", "Username", "Password"],
                    tablefmt="fancy_grid",
                )
            )
            input("Press enter to continue:")
            os.system("cls")

            return

        else:
            os.system("cls")
            return


def generate_password(length: int = 16) -> str:
    """Generates a password of specified length"""

    characters = string.ascii_letters + string.digits + string.punctuation

    password = ""

    for i in range(length):
        password = password + secrets.choice(characters)

    return password


def change_password(current_password, new_pin, confirm_pin):
    """Responsible for changing the PIN of the vault"""

    global PINchanged

    salt = auth.getSalt()
    key = auth.genKey(current_password, salt)
    del current_password
    del salt
    vaultDATA = vault.openVault(key)
    del key

    if vaultDATA == None:
        return "Wrong PIN"

    if new_pin != confirm_pin:
        return "Both PIN do not match!"

    response = confirm(
        text="Continue with PIN Change?", title="Confirmation", buttons=["Yes", "No"]
    )

    if response == "Yes":

        os.remove("salt.bin")
        os.remove("vault.enc")

        new_salt = auth.getSalt()
        new_key = auth.genKey(new_pin, new_salt)
        del new_salt, new_pin, confirm_pin

        vault.saveVault(new_key, vaultDATA)
        del new_key
        alert("PIN Changed!", title="Success")
        PINchanged = True
        return

    else:
        PINchanged = False
        return


def reset_password():
    """Responsible for resetting the password of the vault"""

    try:
        backUp()
        os.remove("salt.bin")
        os.remove("vault.enc")

    except:
        pass

    print("PIN Reset!")
    return
