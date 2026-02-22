import os
import csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QSpacerItem, QSizePolicy, QHBoxLayout
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

class CSVProcessorWidget(QWidget):
    def __init__(self, back_callback=None, send_to_plotter_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.send_to_plotter_callback = send_to_plotter_callback
        self.output_folder_path = None
        self.last_output_path = None
        self.profile_open = False  # False = chiuso (default), True = aperto

        self.resize(600,450)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # Titolo
        self.title_label = QLabel("Airfoil CSV Converter")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.main_layout.addWidget(self.title_label)

        # --- Layout per pulsanti ---
        button_layout = QHBoxLayout()

        # Bottone selezione file CSV
        self.select_file_btn = QPushButton("Seleziona file CSV")
        self.select_file_btn.setStyleSheet(button_style("#4CAF50", "#45A049"))
        self.select_file_btn.setFixedHeight(50)
        self.select_file_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.select_file_btn.clicked.connect(self.select_file)
        button_layout.addWidget(self.select_file_btn)

        # Toggle profilo aperto/chiuso
        self.toggle_profile_btn = QPushButton("Profilo Chiuso")
        self.toggle_profile_btn.setCheckable(True)
        self.toggle_profile_btn.setChecked(False)
        self.update_toggle_style()
        self.toggle_profile_btn.clicked.connect(self.toggle_profile_state)
        button_layout.addWidget(self.toggle_profile_btn)

        self.main_layout.addLayout(button_layout)

        # Pulsante apri cartella
        self.open_folder_btn = QPushButton("📂 Apri cartella")
        self.open_folder_btn.setStyleSheet(button_style("#2196F3", "#1976D2"))
        self.open_folder_btn.setFixedHeight(50)
        self.open_folder_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.hide()
        self.main_layout.addWidget(self.open_folder_btn)

        # Pulsante Invia a Plotter
        self.send_plotter_btn = QPushButton("📈 Invia a Plotter")
        self.send_plotter_btn.setStyleSheet(button_style("#FF9800", "#FB8C00"))
        self.send_plotter_btn.setFixedHeight(50)
        self.send_plotter_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.send_plotter_btn.clicked.connect(self.send_to_plotter)
        self.send_plotter_btn.hide()
        self.main_layout.addWidget(self.send_plotter_btn)

        # Label stato
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.status_label)

        self.main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Pulsante indietro
        if back_callback:
            self.back_btn = QPushButton("⬅️ Torna al menu")
            self.back_btn.setStyleSheet(button_style("#9E9E9E", "#757575"))
            self.back_btn.setFixedHeight(40)
            self.back_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.back_btn.clicked.connect(back_callback)
            self.main_layout.addWidget(self.back_btn)

    # -----------------------------
    # TOGGLE PROFILO
    # -----------------------------
    def toggle_profile_state(self):
        self.profile_open = not self.profile_open
        self.update_toggle_style()

    def update_toggle_style(self):
        if self.profile_open:
            self.toggle_profile_btn.setText("Profilo Aperto")
            self.toggle_profile_btn.setStyleSheet(button_style("#009688", "#00796B"))
        else:
            self.toggle_profile_btn.setText("Profilo Chiuso")
            self.toggle_profile_btn.setStyleSheet(button_style("#607D8B", "#546E7A"))
        self.toggle_profile_btn.setFixedHeight(50)
        self.toggle_profile_btn.setCursor(QCursor(Qt.PointingHandCursor))

    # -----------------------------
    # SELEZIONE FILE
    # -----------------------------
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.process_csv(file_path)

    # -----------------------------
    # PROCESS CSV
    # -----------------------------
    def get_decimal_places(self, num_str):
        if '.' in num_str:
            return len(num_str.split('.')[1])
        return 0

    def process_csv(self, file_path):
        try:
            # Leggi tutte le linee del CSV
            with open(file_path, 'r') as infile:
                lines = infile.readlines()

            # Trova gli indici di inizio e fine dati
            start_index = next((i + 1 for i, l in enumerate(lines) if "X(mm),Y(mm)" in l), -1)
            end_index = next((i - 2 for i, l in enumerate(lines[start_index:], start_index) if "Camber line" in l), -1)
            if start_index == -1 or end_index == -1:
                raise ValueError("Header o Camber line non trovato.")

            processed_data = []
            max_x_dec = max_y_dec = 0

            # Determina il numero massimo di decimali per X e Y
            for line in lines[start_index:end_index]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    x, y = parts[0].replace(',', '.'), parts[1].replace(',', '.')
                    max_x_dec = max(max_x_dec, self.get_decimal_places(x))
                    max_y_dec = max(max_y_dec, self.get_decimal_places(y))

            # Converte e normalizza i dati
            for line in lines[start_index:end_index]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(',', '.')) / 100
                        y = float(parts[1].replace(',', '.')) / 100
                        x_fmt = f"{x:.{max_x_dec + 3}f}"
                        y_fmt = f"{y:.{max_y_dec + 3}f}"
                        processed_data.append((x_fmt, y_fmt))
                    except:
                        continue

            # Costruisci il nome del file in base allo stato del profilo
            output_dir = os.path.dirname(file_path)
            base_name = os.path.basename(file_path).replace('-il.csv', '')
            if self.profile_open:
                output_filename = f"{base_name}-converted-open.csv"
            else:
                output_filename = f"{base_name}-converted-close.csv"
            output_path = os.path.join(output_dir, output_filename)

            self.last_output_path = output_path
            self.output_folder_path = output_dir

            # --- Scrivi CSV ---
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["#Group", "Point", "X_cord", "Y_cord", "Z_cord"])
                for i, (x, y) in enumerate(processed_data, 1):
                    writer.writerow([1, i, x.replace('.', ','), y.replace('.', ','), 0])
                if not self.profile_open:
                    writer.writerow([1, 0, "", "", ""])  # solo se profilo chiuso

            # --- Scrivi TXT ---
            txt_output_path = output_path.replace(".csv", ".txt")
            with open(txt_output_path, 'w') as txtfile:
                txtfile.write(f"{'#Group':<8} {'Point':<6} {'X_cord':<15} {'Y_cord':<15} {'Z_cord':<6}\n")
                for i, (x, y) in enumerate(processed_data, 1):
                    txtfile.write(f"{1:<8} {i:<6} {x.replace('.', ','):<15} {y.replace('.', ','):<15} {0:<6}\n")
                if not self.profile_open:
                    txtfile.write("1 0\n")  # solo se profilo chiuso

            # Mostra stato positivo
            self.status_label.setText("✅ File convertiti con successo!")
            self.status_label.setStyleSheet("color: green;")
            self.open_folder_btn.show()
            self.send_plotter_btn.show()

        except Exception as e:
            self.status_label.setText(f"Errore: {e}")
            self.status_label.setStyleSheet("color: red;")

    # -----------------------------
    # APRI CARTELLA
    # -----------------------------
    def open_output_folder(self):
        if self.output_folder_path and os.path.isdir(self.output_folder_path):
            import subprocess
            subprocess.Popen(["explorer", os.path.normpath(self.output_folder_path)])

    # -----------------------------
    # INVIA A PLOTTER
    # -----------------------------
    def send_to_plotter(self):
        if self.last_output_path and os.path.isfile(self.last_output_path.replace(".csv", ".txt")):
            txt_file = self.last_output_path.replace(".csv", ".txt")
            if self.send_to_plotter_callback:
                self.send_to_plotter_callback(file_to_plot=txt_file)
            self.status_label.setText(f"✅ File inviato al Plotter!")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Errore: file TXT non trovato.")
            self.status_label.setStyleSheet("color: red;")
