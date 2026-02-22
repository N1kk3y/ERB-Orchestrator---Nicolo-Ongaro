import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QSpacerItem, QSizePolicy, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor


def button_style(color, hover_color):
    return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 8px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """


class FusionConverterWidget(QWidget):
    def __init__(self, back_callback=None, send_to_plotter_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.send_to_plotter_callback = send_to_plotter_callback
        self.last_output_file = None
        self.output_folder = None
        self.profile_open = False  # False = chiuso (default), True = aperto

        self.resize(600, 450)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # Titolo
        self.title_label = QLabel("Fusion 360 TXT Converter")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.main_layout.addWidget(self.title_label)

        # --- Layout orizzontale per pulsanti ---
        select_layout = QHBoxLayout()

        # Pulsante seleziona file
        self.select_file_btn = QPushButton("Seleziona file TXT esportato da Fusion 360")
        self.setup_button(self.select_file_btn, "#4CAF50", "#45A049")
        self.select_file_btn.clicked.connect(self.select_file)
        select_layout.addWidget(self.select_file_btn)

        # Toggle profilo aperto/chiuso
        self.toggle_profile_btn = QPushButton("Profilo Chiuso")
        self.toggle_profile_btn.setCheckable(True)
        self.toggle_profile_btn.setChecked(False)
        self.update_toggle_style()
        self.toggle_profile_btn.clicked.connect(self.toggle_profile_state)
        select_layout.addWidget(self.toggle_profile_btn)

        self.main_layout.addLayout(select_layout)

        # Pulsante apri cartella
        self.open_folder_btn = QPushButton("📂 Vai alla cartella")
        self.setup_button(self.open_folder_btn, "#2196F3", "#1976D2")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.hide()
        self.main_layout.addWidget(self.open_folder_btn)

        # Pulsante invia a plotter
        self.send_to_plotter_btn = QPushButton("📈 Invia a Plotter")
        self.setup_button(self.send_to_plotter_btn, "#FF9800", "#F57C00")
        self.send_to_plotter_btn.clicked.connect(self.send_to_plotter)
        self.send_to_plotter_btn.hide()
        self.main_layout.addWidget(self.send_to_plotter_btn)

        # Label stato
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.status_label)

        self.main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Pulsante indietro
        if back_callback:
            self.back_btn = QPushButton("⬅️ Torna al menu")
            self.setup_button(self.back_btn, "#9E9E9E", "#757575")
            self.back_btn.clicked.connect(back_callback)
            self.main_layout.addWidget(self.back_btn)

    # -----------------------------
    def setup_button(self, button, color, hover_color):
        button.setFixedHeight(50)
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

    # -----------------------------
    def toggle_profile_state(self):
        """Cambia lo stato tra profilo chiuso e aperto."""
        self.profile_open = not self.profile_open
        self.update_toggle_style()

    def update_toggle_style(self):
        """Aggiorna il testo e lo stile del pulsante toggle."""
        if self.profile_open:
            self.toggle_profile_btn.setText("Profilo Aperto")
            self.toggle_profile_btn.setStyleSheet(button_style("#009688", "#00796B"))
        else:
            self.toggle_profile_btn.setText("Profilo Chiuso")
            self.toggle_profile_btn.setStyleSheet(button_style("#607D8B", "#546E7A"))
        self.toggle_profile_btn.setFixedHeight(50)
        self.toggle_profile_btn.setCursor(QCursor(Qt.PointingHandCursor))

    # -----------------------------
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file Fusion 360", "", "TXT Files (*.txt)")
        if file_path:
            self.convert_file(file_path)

    # -----------------------------
    def convert_file(self, input_file, scale_factor=0.1):
        try:
            group_id = 1
            point_id = 1
            points_list = []

            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line == "" or line.startswith("*"):
                        continue
                    try:
                        x_str, y_str, z_str = line.split(",")
                        x = -float(x_str) * scale_factor
                        y = -float(y_str) * scale_factor
                        z = float(z_str) * scale_factor
                        points_list.append((x, y, z))
                    except:
                        continue

            # Rimuove duplicati seconda metà
            n = len(points_list)
            if n > 1:
                first_half = points_list[:n // 2]
                second_half = points_list[n // 2:]
                first_coords = set((round(x, 9), round(y, 9)) for x, y, z in first_half)
                filtered_second_half = [p for p in second_half if (round(p[0], 9), round(p[1], 9)) not in first_coords]
                points_list = first_half + filtered_second_half

            dir_name = os.path.dirname(input_file)
            base_name = os.path.splitext(os.path.basename(input_file))[0]

            # ✅ Aggiorna il nome del file in base allo stato del profilo
            if self.profile_open:
                output_file = os.path.join(dir_name, base_name + "_converted-open.txt")
            else:
                output_file = os.path.join(dir_name, base_name + "_converted-close.txt")

            self.last_output_file = output_file
            self.output_folder = dir_name

            lines_out = ["#Group   Point  X_cord          Y_cord          Z_cord"]
            for x, y, z in points_list:
                lines_out.append("{:<8} {:<6} {:<15} {:<15} {:<5}".format(
                    group_id, point_id, f"{x:.9f}".replace('.', ','), f"{y:.9f}".replace('.', ','), int(z)
                ))
                point_id += 1

            # ✅ Se profilo CHIUSO → aggiungi "1 0"
            if not self.profile_open:
                lines_out.append("1 0")

            with open(output_file, 'w') as f_out:
                for l in lines_out:
                    f_out.write(l + "\n")

            self.status_label.setText(f"✅ Conversione completata!\nFile salvato in:\n{output_file}")
            self.status_label.setStyleSheet("color: green;")
            self.open_folder_btn.show()
            self.send_to_plotter_btn.show()

        except Exception as e:
            self.status_label.setText(f"Errore: {e}")
            self.status_label.setStyleSheet("color: red;")
            self.open_folder_btn.hide()
            self.send_to_plotter_btn.hide()


    # -----------------------------
    def open_output_folder(self):
        if self.output_folder and os.path.isdir(self.output_folder):
            import subprocess
            subprocess.Popen(["explorer", os.path.normpath(self.output_folder)])

    # -----------------------------
    def send_to_plotter(self):
        if self.last_output_file and os.path.isfile(self.last_output_file):
            if self.send_to_plotter_callback:
                self.send_to_plotter_callback(file_to_plot=self.last_output_file)
            self.status_label.setText("✅ File inviato al Plotter!")
            self.status_label.setStyleSheet("color: green;")
