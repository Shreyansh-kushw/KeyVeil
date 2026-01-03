# === Standard Imports ===
import sys
import os
import subprocess
import datetime
import csv
import logging
import time

from PyQt6.QtCore import QCoreApplication, Qt

# ✅ Set OpenGL sharing context before QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

# === PyQt6 Imports ===
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QLabel,
)
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QEvent

# === Modules Imports ===
from UI.login_ui import Ui_LoginWindow
from UI.signUp_ui import Ui_SignUp
from UI.PasswordGen_ui import Ui_PassGenerator
from UI.PINchange_ui import Ui_PINChangeWindow
from UI.SiteData_ui import Ui_SiteDetailsWIndow
from UI.AddPassword_ui import Ui_AddPasswordWindow
from version import __version__

import auth
import vault
import vault_ops as vos
import webview
import pyperclip

logger = logging.getLogger(__name__)
logging.basicConfig(filename='Keyveil.log', level=logging.INFO)


class BackupRestoreDialog(QDialog):
    def __init__(self, backup_files=None):
        super().__init__()
        self.setWindowTitle("Restore from Backup")
        self.setMinimumSize(400, 300)

        self.selected_backup = None
        layout = QVBoxLayout(self)

        self.label = QLabel("Available Backups:")
        layout.addWidget(self.label)

        self.backup_list = QListWidget(self)

        if backup_files:
            self.backup_list.addItems(backup_files)
        layout.addWidget(self.backup_list)

        button_layout = QHBoxLayout(self)

        self.browse_button = QPushButton("Browse Backup...")
        self.restore_button = QPushButton("Restore")
        self.cancel_button = QPushButton("Cancel")

        self.restore_button.setEnabled(False)

        button_layout.addWidget(self.browse_button)
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Connections
        self.backup_list.itemSelectionChanged.connect(self.enable_restore_button)
        self.browse_button.clicked.connect(self.browse_backup)
        self.restore_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def enable_restore_button(self):
        selected = self.backup_list.selectedItems()
        self.restore_button.setEnabled(bool(selected))

    def browse_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", "", "Backup Files (*.zip)"
        )
        if file_path:
            self.selected_backup = file_path
            self.accept()

    def get_selected_backup(self):
        selected = self.backup_list.selectedItems()
        if selected:
            return selected[0].text()
        return self.selected_backup


class Authentication(QDialog):

    def __init__(self):
        super().__init__()
        self.login_attempts = 0
        self.max_login_attempts = 5

        if os.path.exists("salt.bin"):
            auth.newUser = False

        else:
            auth.newUser = True

        if not auth.newUser:

            self.login_ui = Ui_LoginWindow()
            self.login_ui.setupUi(self)

            self.login_ui.ok_cancel.accepted.connect(self.authenticate)
            self.login_ui.ok_cancel.rejected.connect(self.exit_code)
            self.login_ui.ResetPIN.clicked.connect(lambda: self.launch_PIN_reset())

        else:

            self.signUp_ui = Ui_SignUp()
            self.signUp_ui.setupUi(self)

            self.signUp_ui.ok_cancel.accepted.connect(self.authenticate)
            self.signUp_ui.ok_cancel.rejected.connect(self.exit_code)
            self.signUp_ui.ImportBackup.clicked.connect(
                lambda: self.restoreBackup("""backup folder""")
            )

    def restoreBackup(self, directory):

        if os.path.isdir(directory):

            available_backups = []
            backups = []
            for filename in os.listdir(directory):
                if filename.startswith("backup") and filename.endswith(".zip"):
                    try:
                        _, datetime_part = filename.split("_", 1)
                        date_part, time_part = datetime_part.split(" ", 1)
                        year, month, day = date_part.split("-")
                        time_components = time_part.replace(".zip", "").split("-")

                        hour, minute, second = time_components[
                            :3
                        ]  # Ignore microseconds
                        month_name = datetime.date(1900, int(month), 1).strftime("%B")
                        backups.append(filename)
                        available_backups.append(
                            f"BACKUP FROM {day}-{month_name}-{year} {hour}:{minute}:{second}"
                        )
                    except Exception as e:

                        pass # No need to raise an error here as if a backup file is not working, it should not hinder the working of the rest of the code

            dialog = BackupRestoreDialog(backup_files=available_backups)

            if dialog.exec():
                try:
                    
                    vos.restoreBackup(
                        directory,
                        backups[available_backups.index(dialog.get_selected_backup())],
                    )
                    logger.info(str(datetime.datetime.now()) + " Backup restored successfully! ")
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Backup Restored")
                    msg.setText("Backup restore successful! The app will now relaunch.")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowModality(Qt.WindowModality.ApplicationModal)
                    msg.exec()

                    # Delay quit slightly to allow cleanup of WebEnginePage
                    # self.restart()
                    QTimer.singleShot(100, self.restart)

                except Exception as error:
                    logger.error(str(datetime.datetime.now()) + " Backup restoration failed! ")
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Operation Failed")
                    msg.setText(
                        "Backup restore aborted! The following error has occured: {}".format(
                            error
                        )
                    )
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowModality(Qt.WindowModality.ApplicationModal)
                    msg.exec()
                    webview.windows[0].destroy()

                    # Delay quit slightly to allow cleanup of WebEnginePage
                    QTimer.singleShot(100, self.restart)

        else:
            QMessageBox.warning(self, "Error", "No backup found!")

    def restart(self):
        logger.info(str(datetime.datetime.now()) + " Restarting.. ")
        if webview.windows:
            webview.windows[0].destroy()
        QApplication.closeAllWindows()
        self._restart_process()
    
    def _restart_process(self):
        print("restart_process")
        subprocess.Popen(
            [sys.executable, "KeyVeil.pyw"], creationflags=subprocess.DETACHED_PROCESS
        )
        QCoreApplication.quit()
    

    def resetPIN(self):

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText("This will wipe all your current data. Continue?")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
        msg_box.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint
        )  # optional: always on top

        response = msg_box.exec()
        if response == QMessageBox.StandardButton.Yes:

            try:

                vos.reset_password()
                logger.info(str(datetime.datetime.now()) + " PIN reset successfully! ")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Password reset successfull")
                msg.setText("Password Reset successfull!. The app will now relaunch.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setWindowModality(Qt.WindowModality.ApplicationModal)
                msg.exec()

                # Delay quit slightly to allow cleanup of WebEnginePage
                # self.restart()
                QTimer.singleShot(100, self.restart)
                # os.execv(sys.executable, ['python'] + sys.argv)

            except Exception as error:
                logger.error(str(datetime.datetime.now()) + " PIN reset failed! ")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Password reset Aborted")
                msg.setText(
                    f"Password Reset Aborted! Following error happened: {error}"
                )
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setWindowModality(Qt.WindowModality.ApplicationModal)
                msg.exec()

    def launch_PIN_reset(self):
        QTimer.singleShot(0, self.resetPIN)

    def authenticate(self):

        if not auth.newUser:

            self.password = self.login_ui.PinEntry.text().strip()
            self.salt = auth.getSalt()

            if not self.password:
                QMessageBox.information(self, "Error", "Enter Your PIN")
                return

            self.key = auth.genKey(self.password, self.salt)
            self.vaultDATA = vault.openVault(self.key)

            if self.vaultDATA == None:  # vault is None or empty

                logger.info(str(datetime.datetime.now()) + " Invalid login attempt! ")
                self.login_attempts += 1

                if self.login_attempts < self.max_login_attempts:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Incorrect PIN OR Vault corrupted. {self.max_login_attempts - self.login_attempts} attempts remaining!",
                    )

                else:
                    logger.critical(str(datetime.datetime.now()) + " All login attempts exhausted! ")
                    QMessageBox.warning(
                        self,
                        "Error",
                        "All login attempts exhausted! KeyVeil will now quit.",
                    )
                    os._exit(0)

                return

            if self.vaultDATA == "Unauthorised":
                logger.critical(str(datetime.datetime.now()) + " Unauthorized device detected! ")
                QMessageBox.warning(
                    self,
                    "Error",
                    "Unauthorised PC!",
                )
                os._exit(0)

            # Valid PIN
            self.accept()
            logger.info(str(datetime.datetime.now()) + " Authentication successfull! ")
            del self.password
            del self.salt

        else:
            pin1 = self.signUp_ui.NewPIN.text().strip()
            pin2 = self.signUp_ui.ConfirmPIN_2.text().strip()

            if not pin1:
                QMessageBox.information(self, "Error", "PIN cannot be empty")
                return

            if pin1 != pin2:
                QMessageBox.warning(self, "Error", "Both PINs do not match!")
                return
            logger.info(str(datetime.datetime.now()) + " PIN reset successfully! ")
            self.password = pin1
            self.salt = auth.getSalt()
            self.key = auth.genKey(self.password, self.salt)
            del self.salt
            del self.password
            self.vaultDATA = vault.openVault(self.key)
            vault.saveVault(self.key, self.vaultDATA)

            if self.vaultDATA is None:
                self.vaultDATA = {}

            self.accept()

    def exit_code(self):

        QApplication.quit()
        self.reject()


class SignalEmitter(QObject):

    openDetails = pyqtSignal(str, str)
    openPasswordGenerator = pyqtSignal()
    VaultDeletion = pyqtSignal()
    RestoreBackup = pyqtSignal()
    CreateBackup = pyqtSignal()
    PINchange = pyqtSignal()
    CSVImporter = pyqtSignal()
    restarter = pyqtSignal()
    LogOutInfo = pyqtSignal()
    AddPassword = pyqtSignal()

class ActivityFilter(QObject):

    def __init__(self, function):
        super().__init__()
        self.funct = function
    
    def eventFilter(self, object, event):
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
        ):
            self.funct()

        return False

class KeyVeilAPI(QObject):
    def __init__(self, vaultDATA, key, authenticator):
        super().__init__()

        self.vaultDATA = vaultDATA
        self.signals = SignalEmitter()
        self.signals.openDetails.connect(self.view_site_details)
        self.signals.openPasswordGenerator.connect(self.open_password_generator)
        self.signals.VaultDeletion.connect(self.delete_vault_data)
        self.signals.RestoreBackup.connect(self.restore_backup)
        self.signals.CreateBackup.connect(self.create_backup)
        self.signals.PINchange.connect(self.change_pin)
        self.signals.CSVImporter.connect(self.import_csv_logic)
        self.signals.restarter.connect(self.restart)
        self.signals.LogOutInfo.connect(
            self.LogOutMessage, type=Qt.ConnectionType.BlockingQueuedConnection
        )
        self.signals.AddPassword.connect(self.AddPassword_Logic)
        self.key = key
        self.authenticator = authenticator
        self.editedDetails = False
        self.start_AutoLocker_thread()
        QApplication.instance().installEventFilter(
            ActivityFilter(self.reset_auto_lock_timer)
        )

    def LogOutMessage(self):
        logger.info(str(datetime.datetime.now()) + " Session expired! ")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Info")
        msg.setText("Session Expired! Login Again.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowModality(Qt.WindowModality.ApplicationModal)
        msg.exec()

    def get_entries(self):
        result = []
        for site, creds in self.vaultDATA.items():
            for cred in creds:
                result.append({"site": site, "username": cred.get("username", "")})
        return result

    def restart(self):
        logger.info(str(datetime.datetime.now()) + " Restarting. ")
        
        if webview.windows:
            webview.windows[0].destroy()

        self._restart_process()
    
    def _restart_process(self):
        print("rnning restarter process")
        subprocess.Popen(
            [sys.executable, "KeyVeil.pyw"], creationflags=subprocess.DETACHED_PROCESS
        )
        QCoreApplication.quit()

    def copy_password(self):
        logger.info(str(datetime.datetime.now()) + " Password copied! ")
        pyperclip.copy(self.SiteDetails_ui.PasswordEntry.text().strip())
        QTimer.singleShot(30_000, lambda: pyperclip.copy(" "))

    def view_site_details(self, site_name, username):
        
        site_data = self.vaultDATA.get(site_name)
        if not site_data:
            return
        self.detail_dialog = QDialog()
        self.detail_dialog.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.detail_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.SiteDetails_ui = Ui_SiteDetailsWIndow()
        self.SiteDetails_ui.setupUi(self.detail_dialog)

        for field in [
            self.SiteDetails_ui.SiteName_entry,
            self.SiteDetails_ui.SiteURL_entry,
            self.SiteDetails_ui.UsernameEntry,
            self.SiteDetails_ui.PasswordEntry,
        ]:
            field.setReadOnly(True)
            field.setCursor(QCursor(Qt.CursorShape.IBeamCursor))  # ✅ Use QCursor

        # Set values
        self.siteName = site_name
        self.SiteDetails_ui.SiteName_entry.setText(site_name)

        for creds in site_data:
            if username == (creds["username"]):
                self.SiteDetails_ui.SiteURL_entry.setText(creds.get("url", ""))
                self.SiteDetails_ui.UsernameEntry.setText(creds.get("username", ""))
                self.SiteDetails_ui.PasswordEntry.setText(creds.get("password", ""))

        self.SiteDetails_ui.CopySiteName.clicked.connect(
            lambda: pyperclip.copy(self.SiteDetails_ui.SiteName_entry.text().strip())
        )
        self.SiteDetails_ui.CopySiteURL.clicked.connect(
            lambda: pyperclip.copy(self.SiteDetails_ui.SiteURL_entry.text().strip())
        )
        self.SiteDetails_ui.CopyUsername.clicked.connect(
            lambda: pyperclip.copy(self.SiteDetails_ui.UsernameEntry.text().strip())
        )
        self.SiteDetails_ui.CopyPassword.clicked.connect(
            lambda: self.copy_password()
        )

        self.SiteDetails_ui.EditSiteName.clicked.connect(lambda: self.editSiteName())
        self.SiteDetails_ui.EditURL.clicked.connect(lambda: self.editSiteURL())
        self.SiteDetails_ui.EditUsername.clicked.connect(lambda: self.editUsername())
        self.SiteDetails_ui.EditPassword.clicked.connect(lambda: self.editPassword())

        self.SiteDetails_ui.deleteButton.clicked.connect(
            lambda: self.deleteEntry(self.vaultDATA, username)
        )

        self.SiteDetails_ui.ok_cancel.accepted.connect(
            lambda: self.updateData(self.vaultDATA, username)
        )
        self.SiteDetails_ui.ok_cancel.rejected.connect(lambda: self.detail_dialog.reject())

        self.detail_dialog.exec()
    
    def start_details_thread(self, site_name, username):
        self.signals.openDetails.emit(site_name, username)

    def start_password_thread(self):
        self.signals.openPasswordGenerator.emit()

    def start_deleteVault_thread(self):
        self.signals.VaultDeletion.emit()

    def start_restoreBackup_thread(self):
        self.signals.RestoreBackup.emit()

    def start_createBackup_thread(self):
        self.signals.CreateBackup.emit()

    def start_PINchange_thread(self):
        self.signals.PINchange.emit()

    def start_CSVImport_thread(self):
        self.signals.CSVImporter.emit()

    def start_AutoLocker_thread(self):
        self.auto_lock_timer = QTimer(self)
        self.auto_lock_timer.setSingleShot(True)
        self.auto_lock_timer.timeout.connect(self.handle_timeout)
        self.auto_lock_timer.start(600_000)

    def open_add_password_thread(self):
        self.signals.AddPassword.emit()

    def editSiteName(self):
        self.editedDetails = True
        self.SiteDetails_ui.SiteName_entry.setReadOnly(False)

    def editSiteURL(self):
        self.editedDetails = True
        self.SiteDetails_ui.SiteURL_entry.setReadOnly(False)

    def editUsername(self):
        self.editedDetails = True
        self.SiteDetails_ui.UsernameEntry.setReadOnly(False)

    def editPassword(self):
        self.editedDetails = True
        self.SiteDetails_ui.PasswordEntry.setReadOnly(False)

    def deleteEntry(self, vaultData, username, confirmation=True):
        choice = vos.delete_entry(vaultData, self.siteName, username, confirmation)
        logger.info(str(datetime.datetime.now()) + " Entry deleted. ")

        if choice == True:
            vault.saveVault(self.key, vaultData)
            self.detail_dialog.accept()
            webview.windows[0].load_url(os.path.abspath("frontend/index.html"))

    def handle_timeout(self):
        self.signals.LogOutInfo.emit()
        self.signals.restarter.emit()
    
    def reset_auto_lock_timer(self):
        if self.auto_lock_timer.isActive():
            self.auto_lock_timer.stop()
        
        self.auto_lock_timer.start(600_000)

    def updateData(self, vaultData, username):

        if self.editedDetails:

            if self.SiteDetails_ui.SiteName_entry.text().strip() == self.siteName:

                for creds in vaultData[self.siteName]:

                    if (
                        creds["username"]
                        == self.SiteDetails_ui.UsernameEntry.text().strip()
                    ):
                        creds.update(
                            {
                                "url": self.SiteDetails_ui.SiteURL_entry.text().strip(),
                                "password": self.SiteDetails_ui.PasswordEntry.text().strip(),
                            }
                        )
                        break

                else:
                    (vaultData[self.siteName]).append(
                        {
                            "url": self.SiteDetails_ui.SiteURL_entry.text().strip(),
                            "username": self.SiteDetails_ui.UsernameEntry.text().strip(),
                            "password": self.SiteDetails_ui.PasswordEntry.text().strip(),
                        }
                    )
                    self.deleteEntry(vaultData, username, confirmation=False)

            else:

                newSite = self.SiteDetails_ui.SiteName_entry.text().strip()

                if newSite in vaultData.keys():
                    (vaultData[newSite]).append(
                        {
                            "url": self.SiteDetails_ui.SiteURL_entry.text().strip(),
                            "username": self.SiteDetails_ui.UsernameEntry.text().strip(),
                            "password": self.SiteDetails_ui.PasswordEntry.text().strip(),
                        }
                    )
                    self.deleteEntry(vaultData, username, confirmation=False)

                else:
                    vaultData[newSite] = []
                    (vaultData[newSite]).append(
                        {
                            "url": self.SiteDetails_ui.SiteURL_entry.text().strip(),
                            "username": self.SiteDetails_ui.UsernameEntry.text().strip(),
                            "password": self.SiteDetails_ui.PasswordEntry.text().strip(),
                        }
                    )
                    self.deleteEntry(vaultData, username, confirmation=False)

            vault.saveVault(self.key, vaultData)
            self.detail_dialog.update()
            self.detail_dialog.accept()
            webview.windows[0].load_url(os.path.abspath("frontend/index.html"))

        else:
            self.detail_dialog.reject()
        # self.dialog.close()

    def open_password_generator(self):
        password_dialog = QDialog()  # ✅ persistent + parented

        password_dialog.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        password_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        ui = Ui_PassGenerator()               # ✅ LOCAL UI
        ui.setupUi(password_dialog)

        ui.GenerateButton.clicked.connect(
            lambda: ui.GeneratedPass.setText(
                vos.generate_password(int(ui.LengthEntry.text()))
            )
        )

        ui.CopyVutton.clicked.connect(
            lambda: pyperclip.copy(ui.GeneratedPass.text())
        )

        password_dialog.exec()
        password_dialog.deleteLater()    # ✅ cleanup


    def create_password(self):

        self.PasswordGenerator_ui.GeneratedPass.setText(
            vos.generate_password(int(self.PasswordGenerator_ui.LengthEntry.text()))
        )

    def delete_vault_data(self):

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText("This will wipe all your current data. Continue?")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
        msg_box.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint
        )  # optional: always on top

        response = msg_box.exec()

        if response == QMessageBox.StandardButton.Yes:
            askPIN = Authentication()

            if askPIN.exec():  # if user entered correct PIN
                # print("PIN accepted")
                vos.reset_password()
                logger.fatal(str(datetime.datetime.now()) + " Vault deleted! ")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Confirmation")
                msg.setText("Vault Deleted successfully!")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setWindowModality(Qt.WindowModality.ApplicationModal)
                msg.exec()
                self.restart()
                if webview.windows:
                    webview.windows[0].destroy()
                # Delay quit slightly to allow cleanup of WebEnginePage

            else:
                return

        else:
            return

    def restore_backup(self):

        self.authenticator.restoreBackup("""backup folder""")
        

    def create_backup(self):

        try:

            vos.backUp("""backup folder""")
            logger.info(str(datetime.datetime.now()) + " Backup created successfully! ")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Backup Created!")
            msg.setText("Backup Created successfully!")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowModality(Qt.WindowModality.ApplicationModal)
            msg.exec()

        except Exception as err:
            logger.info(str(datetime.datetime.now()) + " Backup creation failed! ")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Operation failed")
            msg.setText(f"Backup creation failed! Following error happened: {err}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowModality(Qt.WindowModality.ApplicationModal)
            msg.exec()

    def changePIN_logic(self):

        response = vos.change_password(
            self.PINchange_ui.CurrentPIN_Entry.text().strip(),
            self.PINchange_ui.NewPIN_Entry.text().strip(),
            self.PINchange_ui.ConfirmPIN_Entry.text().strip(),
        )
        # print(response)
        if response == "Wrong PIN":

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Operation failed!")
            msg_box.setText("Wrong PIN entered!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
            msg_box.setWindowFlag(
                Qt.WindowType.WindowStaysOnTopHint
            )  # optional: always on top
            msg_box.exec()
            return

        elif response == "Both PIN do not match!":
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Operation failed!")
            msg_box.setText("Both PIN do not match!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
            msg_box.setWindowFlag(
                Qt.WindowType.WindowStaysOnTopHint
            )  # optional: always on top
            msg_box.exec()
            return

        if vos.PINchanged:
            logger.info(str(datetime.datetime.now()) + " PIN changed successfully! ")
            self.PINchange_dialog.accept()

        else:
            self.PINchange_dialog.reject()

    def change_pin(self):

        self.PINchange_dialog = QDialog()
        self.PINchange_dialog.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.PINchange_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.PINchange_ui = Ui_PINChangeWindow()
        self.PINchange_ui.setupUi(self.PINchange_dialog)

        self.PINchange_ui.ok_cancel.rejected.connect(self.PINchange_dialog.reject)
        self.PINchange_ui.ok_cancel.accepted.connect(lambda: self.changePIN_logic())

        PINChanger = self.PINchange_dialog.exec()

        if PINChanger:
            self.restart()
            
            if webview.windows:
                webview.windows[0].destroy()

    def AddCredentials(self):
        vos.add_entry(
            self.vaultDATA,
            self.AddPasswordWindow_ui.SiteName_entry.text(),
            self.AddPasswordWindow_ui.SiteURL_entry.text(),
            self.AddPasswordWindow_ui.UsernameEntry.text(),
            self.AddPasswordWindow_ui.PasswordEntry.text(),
        )
        webview.windows[0].load_url(os.path.abspath("frontend/index.html"))
        self.AddDialog.accept()

    def AddPassword_Logic(self):

        self.AddDialog = QDialog()
        self.AddDialog.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.AddDialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.AddPasswordWindow_ui = Ui_AddPasswordWindow()
        self.AddPasswordWindow_ui.setupUi(self.AddDialog)

        self.AddPasswordWindow_ui.ok_cancel.accepted.connect(
            lambda: self.AddCredentials()
        )

        self.AddPasswordWindow_ui.ok_cancel.rejected.connect(
            lambda: self.AddDialog.reject()
        )
        self.AddDialog.exec()
        vault.saveVault(self.key , self.vaultDATA)

    def choose_csv_file(self):
        """Creates a dialog box to allow user to choose .csv file"""

        file_path, _ = QFileDialog.getOpenFileName(
            parent=None, caption="Select .csv file", filter="CSV Files (*.csv)"
        )
        return file_path

    def import_passwords_from_csv(self, FilePath: str) -> dict:
        """Function responsible for importing passwords from a .csv file"""

        imported = {}

        with open(FilePath, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row["name"].strip().lower()

                if name not in imported:
                    imported[name] = []

                site = row["url"].strip().lower()
                username = row["username"]
                password = row["password"]
                (imported[name]).append(
                    {"url": site, "username": username, "password": password}
                )

        return imported

    def import_csv_logic(self):

        csvPath = self.choose_csv_file()

        if csvPath:

            try:
                for site, creds in (
                    self.import_passwords_from_csv(f"""{csvPath}""")
                ).items():
                    for cred in creds:

                        if site.strip() != "" and (cred["username"]).strip() != "":
                            if site in self.vaultDATA:

                                exists = any(
                                    c["url"] == cred["url"]
                                    and c["username"] == cred["username"]
                                    for c in self.vaultDATA[site]
                                )
                                if not exists:
                                    vos.add_entry(
                                        self.vaultDATA,
                                        site,
                                        cred["url"],
                                        cred["username"],
                                        cred["password"],
                                    )

                            else:
                                vos.add_entry(
                                    self.vaultDATA,
                                    site,
                                    cred["url"],
                                    cred["username"],
                                    cred["password"],
                                )

                vault.saveVault(self.key, self.vaultDATA)
                logger.info(str(datetime.datetime.now()) + " Passwords Imported. ")
                # print("Passwords Imported successfully")
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Import successful!")
                msg_box.setText(
                    "Any entries without a site name or username are not imported. Please add them manually!"
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
                msg_box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
                webview.windows[0].load_url(os.path.abspath("frontend/index.html"))
                msg_box.exec()

            except Exception as e:
                # print("Some error occured while importing passwords:", e)
                raise RuntimeError("Some error occured while importing passwords") from e
        else:
            return


class KeyVeil:

    def closeApp(self):
        print("closing")
        QTimer.singleShot(200, QApplication.quit)
        time.sleep(3)
        self.force_exit()
    
    def force_exit(self):
        print("force closing")
        if QCoreApplication.instance() is not None:
            os._exit(0)

    def run(self, vaultData, key, login):

        api = KeyVeilAPI(vaultData, key, login)
        html_path = os.path.abspath("frontend/index.html")
        window = webview.create_window(
            "KeyVeil",
            html_path,
            js_api=api,
            width=1000,
            height=650,
            min_size=(900, 600),
        )

        def on_window_closed():
            self.closeApp()

        window.events.closed += on_window_closed
        webview.start(http_server=True, gui="qt", icon="UI/Assets/password.png")


def main():

    app = QApplication(sys.argv)

    login = Authentication()

    if login.exec():  # if user entered correct PIN

        # print("Login success — ready to load dashboard")
        keyveil = KeyVeil()
        keyveil.run(login.vaultDATA, login.key, login)

    else:
        # print("Login failed or cancelled.")
        sys.exit()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()