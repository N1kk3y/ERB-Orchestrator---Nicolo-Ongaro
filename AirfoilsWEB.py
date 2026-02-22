import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSizePolicy, QFileDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QUrl, QObject, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel

# Rimuovi questa riga quando tutto funziona
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"


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


class FileBridge(QObject):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    @pyqtSlot()
    def requestFile(self):
        self._callback()


class AirFoilsVisualizer(QWidget):
    def __init__(self, back_callback=None, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Header
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

        # WebChannel
        self._bridge = FileBridge(self._open_file_dialog)
        self._channel = QWebChannel()
        self._channel.registerObject("pyBridge", self._bridge)

        # Web View
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_view.page().setWebChannel(self._channel)

        s = self.web_view.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        html_path = get_html_path(os.path.join("AirfoilsWEB", "index.html"))
        if os.path.exists(html_path):
            self.web_view.load(QUrl.fromLocalFile(html_path))
        else:
            self.web_view.setHtml(
                f"<h2 style='color:red;'>File non trovato:<br>{html_path}</h2>"
            )

        self.web_view.loadFinished.connect(self._on_load_finished)
        main_layout.addWidget(self.web_view)

    def _on_load_finished(self, ok):
        print(f"Pagina caricata: {ok}")
        if not ok:
            return
        js = """
        new QWebChannel(qt.webChannelTransport, function(channel) {
            console.log("QWebChannel OK");
            window._pyBridge = channel.objects.pyBridge;
            var label = document.querySelector('label.import-btn');
            if (label) {
                label.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    window._pyBridge.requestFile();
                }, true);
            }
        });
        """
        self.web_view.page().runJavaScript(js)

    def _open_file_dialog(self):
        print("_open_file_dialog chiamata!")
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Airfoil Profile", "", "Text Files (*.txt)"
        )
        print(f"File selezionato: {path}")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(path)
            js = f"window.loadProfileFromPython({json.dumps(filename)}, {json.dumps(content)});"
            self.web_view.page().runJavaScript(js, lambda r: print("JS result:", r))
        except Exception as e:
            print(f"Errore lettura file: {e}")

    def _on_back(self):
        if self.back_callback:
            self.back_callback()