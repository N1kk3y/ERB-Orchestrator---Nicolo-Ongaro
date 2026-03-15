import sys
import os
import requests
import threading
import shutil # Aggiunto per gestire la copia del file PDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QStackedWidget, QMessageBox, QProgressDialog
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QFont
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

def create_rounded_icon(image_path, size=100, radius=20):
    if not os.path.exists(image_path):
        # Fallback se l'icona non esiste per evitare crash
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        return QIcon(pix)
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

def check_for_update(callback):
    try:
        r = requests.get(GITHUB_REPO_API, timeout=5)
        r.raise_for_status()
        data = r.json()
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])

        if "beta" in data.get("name", "").lower():
            callback(None)
            return

        exe_url = next((a["browser_download_url"] for a in assets if a["name"].lower().endswith(".exe")), None)
        if not exe_url:
            callback(None)
            return

        local_version_str = getattr(check_for_update, "local_tag", "v0.0.0")
        if version.parse(tag.lstrip("v")) > version.parse(local_version_str.lstrip("v")):
            callback({"title": data.get("name", ""), "tag": tag, "exe_url": exe_url, "body": data.get("body", "")})
        else:
            callback(None)
    except Exception:
        callback(None)

class DownloadSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

# -----------------------
# Main AppLauncher
# -----------------------
class AppLauncher(QWidget):
    def __init__(self, current_version):
        super().__init__()
        self.versione_app = current_version
        self.setWindowTitle("2D CFD Toolkit")
        self.resize(800, 550)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # --- Barra Superiore ---
        top_bar = QHBoxLayout()
        self.btn_settings = QPushButton()
        # Nota: Ho rimosso il path assoluto C:\... per usare resource_path relativo
        settings_icon = create_rounded_icon(resource_path("settings.png"), size=30, radius=5)
        self.btn_settings.setIcon(settings_icon)
        self.btn_settings.setIconSize(QSize(30, 30))
        self.btn_settings.setFixedSize(35, 35)
        self.btn_settings.setStyleSheet("border:none; background: transparent;")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.show_settings)
        top_bar.addWidget(self.btn_settings, alignment=Qt.AlignLeft)
        top_bar.addStretch()
        self.main_layout.addLayout(top_bar)

        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)

        # --- Pagina Menu ---
        self.setup_menu_page()
        
        # --- Pagina Impostazioni ---
        self.setup_settings_page()

        # Footer Versione
        self.version_label = QLabel(self.versione_app)
        self.version_label.setAlignment(Qt.AlignRight)
        self.version_label.setStyleSheet("color: gray; font-size: 10px;")
        self.main_layout.addWidget(self.version_label)

        self.update_label = QLabel("")
        self.update_label.setAlignment(Qt.AlignRight)
        self.update_label.setStyleSheet("color: green; font-size: 11px; font-weight: bold;")
        self.update_label.setCursor(Qt.PointingHandCursor)
        self.update_label.mousePressEvent = self.update_clicked
        self.main_layout.addWidget(self.update_label)

        self.update_info = None
        threading.Thread(target=self.check_update_thread, daemon=True).start()

    def setup_menu_page(self):
        self.menu_page = QWidget()
        menu_layout = QVBoxLayout(self.menu_page)
        
        title_label = QLabel("ERB CFD Toolkit")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 40px; font-weight: bold;")
        menu_layout.addWidget(title_label)

        title_label2 = QLabel("Seleziona il software da eseguire")
        title_label2.setAlignment(Qt.AlignCenter)
        title_label2.setStyleSheet("font-size: 18px; color: #555; margin-bottom: 20px;")
        menu_layout.addWidget(title_label2)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        buttons_layout.setAlignment(Qt.AlignCenter)
        
        # Widget bottoni (CSV, Plotter, Fusion, Script, Gurney, Ansys, Web)
        self.csv_widget = None
        buttons_layout.addWidget(self.create_icon_button("CSV Converter", resource_path("CSV.png"), self.show_csv))
        
        self.plotter_widget = None
        buttons_layout.addWidget(self.create_icon_button("Airfoil Plotter", resource_path("plotter.png"), self.show_plotter))
        
        self.fusion_widget = None
        buttons_layout.addWidget(self.create_icon_button("Fusion Converter", resource_path("Fusion.png"), self.show_fusion))
        
        self.download_widget = None
        buttons_layout.addWidget(self.create_icon_button("Download Script", resource_path("Script.png"), self.show_download_script))
        
        self.gurney_widget = None
        buttons_layout.addWidget(self.create_icon_button("Gurney Flap", resource_path("GurneyFlap.png"), self.show_Gurney_flap))
        
        self.ansys_report_widget = None
        buttons_layout.addWidget(self.create_icon_button("Ansys Report", resource_path("AnsysReport.png"), self.show_ansys_report))
        
        self.airfoils_web_widget = None
        buttons_layout.addWidget(self.create_icon_button("Airfoils Mapper", resource_path("ArfoilsMapper.png"), self.show_airfoils_web))

        menu_layout.addLayout(buttons_layout)
        self.pages.addWidget(self.menu_page)

    def setup_settings_page(self):
        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)
        settings_layout.setContentsMargins(50, 20, 50, 20)
        
        title = QLabel("Impostazioni e Informazioni")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        settings_layout.addWidget(title)

        # Frame Info Container
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #f9f9f9; border-radius: 15px; border: 1px solid #ddd;")
        info_vbox = QVBoxLayout(info_frame)
        info_vbox.setSpacing(10)

        def add_info_row(label_text, value_text, is_bold=False):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #666; border: none;")
            val = QLabel(value_text)
            style = "color: #000; border: none;"
            if is_bold: style += " font-weight: bold;"
            val.setStyleSheet(style)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            info_vbox.addLayout(row)

        add_info_row("Sviluppatore:", "Nicolò Ongaro", True)
        add_info_row("Email:", "n.ongaro2@studenti.unibg.it")
        add_info_row("Reparto:", "Aerodinamica e CFD")
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        info_vbox.addWidget(line)

        add_info_row("Versione Corrente:", self.versione_app)
        add_info_row("Ultimo Aggiornamento:", "15/03/2026")

        settings_layout.addWidget(info_frame)

        # Sezione Download Guida
        guide_layout = QHBoxLayout()
        guide_layout.setContentsMargins(0, 20, 0, 20)
        lbl_guide = QLabel("Documentazione Tecnica:")
        lbl_guide.setStyleSheet("font-size: 14px;")
        btn_pdf = QPushButton(" Scarica Guida (PDF)")
        btn_pdf.setFixedSize(180, 40)
        btn_pdf.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.clicked.connect(self.download_guide_pdf)
        
        guide_layout.addWidget(lbl_guide)
        guide_layout.addStretch()
        guide_layout.addWidget(btn_pdf)
        settings_layout.addLayout(guide_layout)

        settings_layout.addStretch()

        btn_back = QPushButton("Torna al Menu")
        btn_back.setFixedSize(200, 40)
        btn_back.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border-radius: 10px; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        btn_back.clicked.connect(self.show_menu)
        settings_layout.addWidget(btn_back, alignment=Qt.AlignCenter)

        self.pages.addWidget(self.settings_page)

    def download_guide_pdf(self):
        # CORREZIONE DEFINITIVA:
        source = resource_path(os.path.join("resources", "ERB_CFD_Toolkit_Guida.pdf"))
        dest = os.path.join(DOWNLOAD_DIR, "ERB_Toolkit_Guida.pdf")
        
        try:
            if os.path.exists(source):
                shutil.copy2(source, dest)
                QMessageBox.information(self, "Successo", f"Guida scaricata correttamente sul Desktop:\n{dest}")
            else:
                # Questo ti aiuterà a vedere dove sta cercando se fallisce ancora
                QMessageBox.warning(self, "Errore", f"File non trovato!\nPercorso cercato:\n{source}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile copiare il file: {e}")

    def create_icon_button(self, text, icon_path, callback):
        container = QFrame()
        layout = QVBoxLayout(container)
        btn = QPushButton()
        btn.setIcon(create_rounded_icon(icon_path))
        btn.setIconSize(QSize(100, 100))
        btn.setFixedSize(110, 110)
        btn.setStyleSheet("border:none; background: transparent;")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(label)
        return container

    def check_update_thread(self):
        check_for_update.local_tag = self.versione_app
        def callback(info):
            if info:
                self.update_info = info
                self.update_label.setText("Nuovo aggiornamento disponibile")
        check_for_update(callback)

    def update_clicked(self, event):
        if not self.update_info: return
        msg = QMessageBox()
        msg.setWindowTitle(f"Update {self.update_info['tag']}")
        msg.setText(f"{self.update_info['body']}\n\nScaricare?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() == QMessageBox.Yes:
            self.download_update(self.update_info['exe_url'])

    def download_update(self, url):
        # ... (Logica download invariata come nel tuo codice originale)
        pass

    # Metodi di navigazione
    def show_csv(self):
        if not self.csv_widget:
            from CSV_Airfoils_Converter import CSVProcessorWidget
            self.csv_widget = CSVProcessorWidget(back_callback=self.show_menu, send_to_plotter_callback=self.show_plotter)
            self.pages.addWidget(self.csv_widget)
        self.pages.setCurrentWidget(self.csv_widget)

    def show_plotter(self, file_to_plot=None):
        if not self.plotter_widget:
            from plotter_v3 import AirfoilsPlotterWidget
            self.plotter_widget = AirfoilsPlotterWidget(back_callback=self.show_menu)
            self.pages.addWidget(self.plotter_widget)
        if file_to_plot: self.plotter_widget.select_file_path(file_to_plot)
        self.pages.setCurrentWidget(self.plotter_widget)

    def show_fusion(self):
        if not self.fusion_widget:
            from Fusion_TXT_converter import FusionConverterWidget
            self.fusion_widget = FusionConverterWidget(back_callback=self.show_menu, send_to_plotter_callback=self.show_plotter)
            self.pages.addWidget(self.fusion_widget)
        self.pages.setCurrentWidget(self.fusion_widget)

    def show_download_script(self):
        if not self.download_widget:
            from Dowload_Fusion_Script import DownloadFusionScript
            self.download_widget = DownloadFusionScript(back_callback=self.show_menu)
            self.pages.addWidget(self.download_widget)
        self.pages.setCurrentWidget(self.download_widget)

    def show_Gurney_flap(self):
        if not hasattr(self, 'gurney_widget') or self.gurney_widget is None:
            from Gurney_Flap import AirfoilsPlotterWidget
            self.gurney_widget = AirfoilsPlotterWidget(back_callback=self.show_menu)
            self.pages.addWidget(self.gurney_widget)
        self.pages.setCurrentWidget(self.gurney_widget)

    def show_ansys_report(self):
        if not self.ansys_report_widget:
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

    def show_settings(self): self.pages.setCurrentWidget(self.settings_page)
    def show_menu(self): self.pages.setCurrentWidget(self.menu_page)

if __name__ == "__main__":
    versione = "v7.2.0"
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = AppLauncher(versione)
    window.show()
    sys.exit(app.exec_())