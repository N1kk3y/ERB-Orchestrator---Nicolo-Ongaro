import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView


def button_style(color, hover_color):
    return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 5px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """


def get_html_path(relative_path):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class AirFoilsVisualizer(QWidget):
    def __init__(self, back_callback=None, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- Header ---
        header_layout = QHBoxLayout()

        btn_back = QPushButton("← Back")
        btn_back.setFixedWidth(100)
        btn_back.setStyleSheet(button_style("#555555", "#333333"))
        btn_back.clicked.connect(self._on_back)
        header_layout.addWidget(btn_back)

        title = QLabel("Airfoils Mapper")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        header_layout.addWidget(title, stretch=1)

        spacer = QLabel()
        spacer.setFixedWidth(100)
        header_layout.addWidget(spacer)

        main_layout.addLayout(header_layout)

        # --- Web View ---
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        html_path = get_html_path(os.path.join("AirfoilsWEB", "index.html"))

        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))
        else:
            self.web_view.setHtml(
                f"<h2 style='color:red;font-family:Arial;'>File non trovato:<br>{html_path}</h2>"
            )

        main_layout.addWidget(self.web_view)

    def _on_back(self):
        if self.back_callback:
            self.back_callback()