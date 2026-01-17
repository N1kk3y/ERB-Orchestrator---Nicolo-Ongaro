import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QStackedWidget
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QSize

# Helper per risorse (icone, immagini, ecc.)
def resource_path(relative_path):
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Helper per icone arrotondate
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

class AppLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D CFD Toolkit")
        self.resize(800, 500)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Stacked widget per le varie pagine
        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.pages)

        # Pagina menu principale
        self.menu_page = QWidget()
        menu_layout = QVBoxLayout(self.menu_page)
        menu_layout.setAlignment(Qt.AlignCenter)

        # Titolo
        title_label = QLabel("CFD Toolkit")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 40px; font-weight: bold;")
        menu_layout.addWidget(title_label)
        # Sub Titolo
        title_label2 = QLabel("Seleziona il software da eseguire")
        title_label2.setAlignment(Qt.AlignCenter)
        title_label2.setStyleSheet("font-size: 20px; font-weight: bold;")
        menu_layout.addWidget(title_label2)

        # Layout bottoni centrato
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(40)
        buttons_layout.setAlignment(Qt.AlignCenter)  # mantiene centrato il gruppo
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

        self.pages.addWidget(self.menu_page)

        # --- Etichetta versione in basso a destra ---
        version_label = QLabel("Versione 2.1.5")
        version_label.setAlignment(Qt.AlignRight)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        self.main_layout.addWidget(version_label)
        version_label = QLabel("Last Update : 07/11/2025 - Nicolò Ongaro ")
        version_label.setAlignment(Qt.AlignRight)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        self.main_layout.addWidget(version_label)

    # Helper per creare bottoni con icone arrotondate
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

    # Torna al menu principale
    def show_menu(self):
        self.pages.setCurrentWidget(self.menu_page)


# --- MAIN ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppLauncher()
    window.show()
    sys.exit(app.exec_())
