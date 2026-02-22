import sys
import os
import shutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog

class DownloadFusionScript(QWidget):
    def __init__(self, back_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.setWindowTitle("Download Sezione")
        self.resize(600, 450)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # Titolo
        title_label = QLabel("Scarica File ZIP")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.main_layout.addWidget(title_label)

        # Pulsante download subito sotto il titolo
        self.download_btn = QPushButton("⬇️ Download ZIP")
        self.download_btn.setFixedHeight(50)
        self.download_btn.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
        """)
        self.download_btn.clicked.connect(self.download_zip)
        self.main_layout.addWidget(self.download_btn)

        # Spacer per spingere il pulsante indietro in basso
        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Pulsante indietro
        if self.back_callback:
            back_btn = QPushButton("⬅️ Torna al menu")
            back_btn.setFixedHeight(40)
            back_btn.setStyleSheet("""
                background-color:#9E9E9E;
                color:white;
                font-weight:bold;
                border-radius:10px;
            """)
            back_btn.clicked.connect(self.back_callback)
            self.main_layout.addWidget(back_btn)

        # Label stato subito sopra il pulsante indietro
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.status_label)

    def download_zip(self):
        try:
            zip_path = os.path.join(os.path.dirname(__file__), "resources", "ERB-AERO-Fusion 360 TOOLKIT.zip")
            if not os.path.isfile(zip_path):
                self.status_label.setText("❌ File ZIP non trovato!")
                self.status_label.setStyleSheet("color: red;")
                return

            # Chiede all'utente dove salvare il file
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salva File ZIP",
                os.path.join(os.path.expanduser("~"), "Desktop", "ERB-AERO-Fusion 360 TOOLKIT.zip"),
                "ZIP Files (*.zip)"
            )

            # Se l'utente annulla
            if not save_path:
                return

            shutil.copy(zip_path, save_path)
            self.status_label.setText(f"✅ File salvato in:\n{save_path}")
            self.status_label.setStyleSheet("color: green;")

        except Exception as e:
            self.status_label.setText(f"Errore: {e}")
            self.status_label.setStyleSheet("color: red;")
