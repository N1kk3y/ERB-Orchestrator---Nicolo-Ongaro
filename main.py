import sys
import os
import requests
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QStackedWidget, QMessageBox, QProgressDialog
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QObject
from packaging import version
# -----------------------
# Configurazione GitHub
# -----------------------
GITHUB_REPO_API = "https://api.github.com/repos/N1kk3y/ERB-Orchestrator---Nicolo-Ongaro/releases/latest"
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
LOCAL_EXE_PATH = sys.argv[0]

# -----------------------
# Helper per risorse
# -----------------------
def resource_path(relative_path):
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# -----------------------
# Helper per icone arrotondate
# -----------------------
def create_rounded_icon(image_path, size=100, radius=20):
    pixmap = QPixmap(image_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    rounded = QPixmap(size, size)
    rounded.fill(Qt.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QIcon(rounded)

# -----------------------
# Funzioni per auto-update
# -----------------------
def check_for_update(callback):
    try:
        r = requests.get(GITHUB_REPO_API, timeout=5)
        r.raise_for_status()
        data = r.json()

        title = data.get("name", "")
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])

        # Se è una beta, ignoriamo
        if "beta" in title.lower().replace(" ", ""):
            callback(None)
            return

        # Cerco l'asset exe
        exe_url = None
        for asset in assets:
            if asset["name"].lower().endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break
        if exe_url is None:
            callback(None)
            return

        # Versione locale
        local_version_str = getattr(check_for_update, "local_tag", "v0.0.0")
        local_version = version.parse(local_version_str.lstrip("v"))
        remote_version = version.parse(tag.lstrip("v"))

        # Confronto semantico
        if remote_version > local_version:
            callback({
                "title": title,
                "tag": tag,
                "exe_url": exe_url,
                "body": data.get("body", "")
            })
        else:
            callback(None)

    except Exception as e:
        print(f"[Update Check Error] {e}")
        callback(None)

# Segnale per progress update
class DownloadSignals(QObject):
    progress = pyqtSignal(int)  # percentuale
    finished = pyqtSignal(str)  # path del file scaricato

# -----------------------
# Main AppLauncher
# -----------------------
class AppLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D CFD Toolkit")
        self.resize(800, 500)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.pages)

        self.menu_page = QWidget()
        menu_layout = QVBoxLayout(self.menu_page)
        menu_layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel("ERB CFD Toolkit")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 40px; font-weight: bold;")
        menu_layout.addWidget(title_label)

        title_label2 = QLabel("Seleziona il software da eseguire")
        title_label2.setAlignment(Qt.AlignCenter)
        title_label2.setStyleSheet("font-size: 20px; font-weight: bold;")
        menu_layout.addWidget(title_label2)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(40)
        buttons_layout.setAlignment(Qt.AlignCenter)
        menu_layout.addLayout(buttons_layout)

        # --- Bottoni Menu ---
        self.csv_widget = None
        btn_csv = self.create_icon_button("CSV Converter",
                                          resource_path("CSV.png"),
                                          lambda: self.show_csv())
        buttons_layout.addWidget(btn_csv)

        self.plotter_widget = None
        btn_plotter = self.create_icon_button("Airfoil Plotter",
                                              resource_path("plotter.png"),
                                              lambda: self.show_plotter())
        buttons_layout.addWidget(btn_plotter)

        self.fusion_widget = None
        btn_fusion = self.create_icon_button("Fusion Converter",
                                             resource_path("Fusion.png"),
                                             lambda: self.show_fusion())
        buttons_layout.addWidget(btn_fusion)

        self.download_widget = None
        btn_download = self.create_icon_button(
            "Download Fusion Script",
            resource_path("Script.png"),
            lambda: self.show_download_script()
        )
        buttons_layout.addWidget(btn_download)

        # --- NUOVO PULSANTE GURNEY FLAP ---
        self.gurney_widget = None
        btn_gurney = self.create_icon_button(
            "Gurney Flap",
            resource_path("GurneyFlap.png"),  
            lambda: self.show_Gurney_flap()
        )
        buttons_layout.addWidget(btn_gurney)

        # --- BOTTONE ANSYS REPORT ---
        self.ansys_report_widget = None
        btn_ansys = self.create_icon_button(
            "Ansys Report",
            resource_path("AnsysReport.png"),  
            lambda: self.show_ansys_report()
        )
        buttons_layout.addWidget(btn_ansys)

        self.airfoils_web_widget = None
        btn_airfoils_web = self.create_icon_button(
            "Airfoils Mapper ",
            resource_path("ArfoilsMapper.png"),   # <-- sostituisci con la tua icona se ne hai una
            lambda: self.show_airfoils_web()
        )
        buttons_layout.addWidget(btn_airfoils_web)

        self.pages.addWidget(self.menu_page)

        version_label = QLabel("Versione 6.7.2")
        version_label.setAlignment(Qt.AlignRight)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        self.main_layout.addWidget(version_label)
        version_label2 = QLabel("Last Update : 07/11/2025 - Nicolò Ongaro ")
        version_label2.setAlignment(Qt.AlignRight)
        version_label2.setStyleSheet("color: gray; font-size: 10px;")
        self.main_layout.addWidget(version_label2)

        # --- Scritta aggiornamento ---
        self.update_label = QLabel("")
        self.update_label.setAlignment(Qt.AlignRight)
        self.update_label.setStyleSheet("color: green; font-size: 12px; font-weight: bold;")
        self.update_label.setCursor(Qt.PointingHandCursor)
        self.update_label.mousePressEvent = self.update_clicked
        self.main_layout.addWidget(self.update_label)

        self.update_info = None

        threading.Thread(target=self.check_update_thread, daemon=True).start()

    def create_icon_button(self, text, icon_path, callback):
        frame_layout = QVBoxLayout()
        btn = QPushButton()
        btn.setIcon(create_rounded_icon(icon_path))
        btn.setIconSize(QSize(100, 100))
        btn.setFixedSize(110, 110)
        btn.setStyleSheet("border:none;")
        btn.clicked.connect(callback)
        frame_layout.addWidget(btn, alignment=Qt.AlignCenter)

        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 14px;")
        frame_layout.addWidget(label)

        container = QFrame()
        container.setLayout(frame_layout)
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        return container

    # Thread controllo update
    def check_update_thread(self):
        def callback(info):
            if info:
                self.update_info = info
                self.update_label.setText("Nuovo aggiornamento disponibile")
        try:
            check_for_update(callback)
        except Exception:
            pass

    # Click scritta aggiornamento
    def update_clicked(self, event):
        if not self.update_info:
            return
        title = self.update_info.get("title","")
        body = self.update_info.get("body","")
        exe_url = self.update_info.get("exe_url","")

        msg = QMessageBox()
        msg.setWindowTitle(f"Aggiornamento disponibile: {title}")
        msg.setText(f"{body}\n\nVuoi scaricare l'aggiornamento?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.download_update(exe_url)

    # Download fluido con progress bar thread-safe
    def download_update(self, url):
        progress = QProgressDialog("Scaricando aggiornamento...", "Annulla", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)

        signals = DownloadSignals()
        signals.progress.connect(progress.setValue)
        signals.finished.connect(lambda path: self.download_finished(path))

        def download_thread():
            try:
                local_path = os.path.join(DOWNLOAD_DIR, os.path.basename(url))
                r = requests.get(url, stream=True)
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 1024*1024
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = int(downloaded / total * 100)
                            signals.progress.emit(percent)
                signals.progress.emit(100)
                signals.finished.emit(local_path)
            except Exception as e:
                progress.close()
                QMessageBox.warning(self, "Errore", f"Download fallito:\n{str(e)}")

        threading.Thread(target=download_thread, daemon=True).start()

    def download_finished(self, local_path):
        progress = self.findChild(QProgressDialog)
        if progress:
            progress.close()

        msg = QMessageBox(self)
        msg.setWindowTitle("Download completato")
        msg.setText(f"Aggiornamento scaricato in:\n{local_path}\n\nCosa vuoi fare ora?")
        chiudi_btn = msg.addButton("Chiudi applicazione", QMessageBox.AcceptRole)
        msg.exec_()

        if msg.clickedButton() == chiudi_btn:
            QApplication.quit()


    # -----------------------------
    # Mostra CSV Converter
    # -----------------------------
    def show_csv(self):
        if not self.csv_widget:
            from CSV_Airfoils_Converter import CSVProcessorWidget
            self.csv_widget = CSVProcessorWidget(
                back_callback=self.show_menu,
                send_to_plotter_callback=self.show_plotter
            )
            self.pages.addWidget(self.csv_widget)
        self.pages.setCurrentWidget(self.csv_widget)

    # -----------------------------
    # Mostra Plotter
    # -----------------------------
    def show_plotter(self, file_to_plot=None):
        if not self.plotter_widget:
            from plotter_v3 import AirfoilsPlotterWidget
            self.plotter_widget = AirfoilsPlotterWidget(back_callback=self.show_menu)
            self.pages.addWidget(self.plotter_widget)
        if file_to_plot:
            self.plotter_widget.select_file_path(file_to_plot)
        self.pages.setCurrentWidget(self.plotter_widget)

    # -----------------------------
    # Mostra Fusion Converter
    # -----------------------------
    def show_fusion(self):
        if not self.fusion_widget:
            from Fusion_TXT_converter import FusionConverterWidget
            self.fusion_widget = FusionConverterWidget(
                back_callback=self.show_menu,
                send_to_plotter_callback=self.show_plotter
            )
            self.pages.addWidget(self.fusion_widget)
        self.pages.setCurrentWidget(self.fusion_widget)

    # -----------------------------
    # Mostra Download Script
    # -----------------------------
    def show_download_script(self):
        if not self.download_widget:
            from Dowload_Fusion_Script import DownloadFusionScript
            self.download_widget = DownloadFusionScript(back_callback=self.show_menu)
            self.pages.addWidget(self.download_widget)
        self.pages.setCurrentWidget(self.download_widget)

    # -----------------------------
    # Mostra Gurney Flap
    # -----------------------------
    def show_Gurney_flap(self):
        if not hasattr(self, 'gurney_widget') or self.gurney_widget is None:
            # Importa direttamente il nuovo widget
            from Gurney_Flap import AirfoilsPlotterWidget  # oppure GurneyFlapWidget se rinominata
            self.gurney_widget = AirfoilsPlotterWidget(back_callback=self.show_menu)
            self.pages.addWidget(self.gurney_widget)
        self.pages.setCurrentWidget(self.gurney_widget)

    # -----------------------------
    # Mostra Ansys Report Generator
    # -----------------------------
    def show_ansys_report(self):
        if not self.ansys_report_widget:
            # Ora che il file si chiama Ansys_Report.py, questo funzionerà
            from Ansys_Report import AnsysReportWidget
            self.ansys_report_widget = AnsysReportWidget(back_callback=self.show_menu)
            self.pages.addWidget(self.ansys_report_widget)
        
        self.pages.setCurrentWidget(self.ansys_report_widget)

    def show_airfoils_web(self):
        if not self.airfoils_web_widget:
            from AirfoilsWEB import AirFoilsVisualizer
            self.airfoils_web_widget = AirFoilsVisualizer(back_callback=self.show_menu)
            self.pages.addWidget(self.airfoils_web_widget)
        self.pages.setCurrentWidget(self.airfoils_web_widget)

    # Torna al menu
    def show_menu(self):
        self.pages.setCurrentWidget(self.menu_page)


# --- MAIN ---
if __name__ == "__main__":
    check_for_update.local_tag = "v6.7.2"
    from PyQt5.QtCore import Qt
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = AppLauncher()
    window.show()
    sys.exit(app.exec_())
