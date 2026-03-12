import os
import csv
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, 
    QSpacerItem, QSizePolicy, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QPixmap

# --- Stili CSS ---
def get_button_style(color, hover_color):
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
def resource_path(relative_path):
    """ Ottiene il percorso assoluto delle risorse, compatibile con PyInstaller """
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_toggle_style(active=False):
    if active:
        return get_button_style("#4CAF50", "#45A049") # Verde
    return get_button_style("#9E9E9E", "#757575")     # Grigio

class CSVProcessorWidget(QWidget):
    def __init__(self, back_callback=None, send_to_plotter_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.send_to_plotter_callback = send_to_plotter_callback
        self.output_folder_path = None
        self.last_output_path = None # Sarà il percorso del file .txt
        
        # DEFAULT: Profilo Aperto attivo
        self.profile_open = True  
        self.selected_file_path = None 

        self.setWindowTitle("Airfoil CSV Converter")
        self.resize(850, 700)

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setSpacing(15)

        # --- 1. PULSANTE "IMPORTA FILE" ---
        self.import_file_btn = QPushButton("Importa file CSV")
        self.import_file_btn.setStyleSheet(get_button_style("#2196F3", "#1976D2"))
        self.import_file_btn.setFixedHeight(50)
        self.import_file_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.import_file_btn.clicked.connect(self.select_file)
        self.main_layout.addWidget(self.import_file_btn)

        self.file_label = QLabel("Nessun file selezionato")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setStyleSheet("color: #757575; font-size: 11px;")
        self.main_layout.addWidget(self.file_label)

        self.main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # --- 2. SEZIONE OPZIONI (VERTICALE) ---
        self.options_container = QVBoxLayout()
        self.options_container.setSpacing(20)

        # --- Riga Profilo Aperto ---
        self.open_row_layout = QHBoxLayout()
        self.open_img_label = QLabel()
        open_pix = QPixmap(resource_path("Aperto.png"))
        if not open_pix.isNull():
            self.open_img_label.setPixmap(open_pix)
            self.open_img_label.setScaledContents(True)
            self.open_img_label.setMaximumHeight(400)
            self.open_img_label.setMaximumWidth(700) 
        else:
            self.open_img_label.setText("📷 Img Aperto")
        
        self.toggle_open_btn = QPushButton("Profilo Aperto")
        self.toggle_open_btn.setCheckable(True)
        self.toggle_open_btn.setFixedSize(160, 50)
        self.toggle_open_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.toggle_open_btn.clicked.connect(lambda: self.set_profile_state(True))
        
        self.open_row_layout.addWidget(self.open_img_label, stretch=4)
        self.open_row_layout.addWidget(self.toggle_open_btn, stretch=0)
        self.open_row_layout.addSpacing(10)
        self.options_container.addLayout(self.open_row_layout)

        # --- Riga Profilo Chiuso ---
        self.close_row_layout = QHBoxLayout()
        self.close_img_label = QLabel()
        close_pix = QPixmap(resource_path("Chiuso.png"))
        if not close_pix.isNull():
            self.close_img_label.setPixmap(close_pix)
            self.close_img_label.setScaledContents(True)
            self.close_img_label.setMaximumHeight(400)
            self.close_img_label.setMaximumWidth(700) 
        else:
            self.close_img_label.setText("📷 Img Chiuso")
        
        self.toggle_close_btn = QPushButton("Profilo Chiuso")
        self.toggle_close_btn.setCheckable(True)
        self.toggle_close_btn.setFixedSize(160, 50)
        self.toggle_close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.toggle_close_btn.clicked.connect(lambda: self.set_profile_state(False))
        
        self.close_row_layout.addWidget(self.close_img_label, stretch=4)
        self.close_row_layout.addWidget(self.toggle_close_btn, stretch=0)
        self.close_row_layout.addSpacing(10)
        self.options_container.addLayout(self.close_row_layout)

        self.main_layout.addLayout(self.options_container)
        
        self.update_toggle_styles()

        # --- 3. PULSANTE "CONVERTI" ---
        self.main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.convert_btn = QPushButton("Converti in TXT")
        self.convert_btn.setStyleSheet(get_button_style("#FF9800", "#FB8C00"))
        self.convert_btn.setFixedHeight(55)
        self.convert_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.convert_btn.clicked.connect(self.convert_file)
        self.main_layout.addWidget(self.convert_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.main_layout.addWidget(self.status_label)

        # --- 4. MENU POST-CONVERSIONE ---
        self.post_conversion_frame = QFrame()
        self.post_layout = QVBoxLayout(self.post_conversion_frame)
        self.post_layout.setContentsMargins(0, 0, 0, 0)
        
        self.open_folder_btn = QPushButton("📂 Apri cartella")
        self.open_folder_btn.setStyleSheet(get_button_style("#607D8B", "#455A64"))
        self.open_folder_btn.setFixedHeight(45)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.post_layout.addWidget(self.open_folder_btn)

        self.send_plot_btn = QPushButton("📈 Invia a Plotter")
        self.send_plot_btn.setStyleSheet(get_button_style("#009688", "#00796B"))
        self.send_plot_btn.setFixedHeight(45)
        self.send_plot_btn.clicked.connect(self.send_to_plotter)
        self.post_layout.addWidget(self.send_plot_btn)

        self.post_conversion_frame.hide()
        self.main_layout.addWidget(self.post_conversion_frame)

        self.main_layout.addStretch()

        if back_callback:
            self.back_btn = QPushButton("⬅️ Torna al menu")
            self.back_btn.setStyleSheet(get_button_style("#37474F", "#263238"))
            self.back_btn.setFixedHeight(40)
            self.back_btn.clicked.connect(back_callback)
            self.main_layout.addWidget(self.back_btn)

    def set_profile_state(self, is_open):
        self.profile_open = is_open
        self.update_toggle_styles()

    def update_toggle_styles(self):
        self.toggle_open_btn.setChecked(self.profile_open)
        self.toggle_close_btn.setChecked(not self.profile_open)
        self.toggle_open_btn.setStyleSheet(get_toggle_style(self.profile_open))
        self.toggle_close_btn.setStyleSheet(get_toggle_style(not self.profile_open))

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.status_label.setText("")
            self.post_conversion_frame.hide()

    def convert_file(self):
        if not self.selected_file_path:
            self.status_label.setText("⚠️ Seleziona prima un file CSV!")
            self.status_label.setStyleSheet("color: #FF9800;")
            return
        self.process_csv(self.selected_file_path)

    def get_decimal_places(self, num_str):
        return len(num_str.split('.')[1]) if '.' in num_str else 0

    def process_csv(self, file_path):
        try:
            with open(file_path, 'r') as infile:
                lines = infile.readlines()

            start_index = next((i + 1 for i, l in enumerate(lines) if "X(mm),Y(mm)" in l), -1)
            end_index = next((i - 2 for i, l in enumerate(lines[start_index:], start_index) if "Camber line" in l), -1)
            
            if start_index == -1 or end_index == -1:
                raise ValueError("Formato CSV non valido.")

            processed_data = []
            max_x_dec = max_y_dec = 0

            for line in lines[start_index:end_index]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    x_str, y_str = parts[0].replace(',', '.'), parts[1].replace(',', '.')
                    max_x_dec = max(max_x_dec, self.get_decimal_places(x_str))
                    max_y_dec = max(max_y_dec, self.get_decimal_places(y_str))

            for line in lines[start_index:end_index]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].replace(',', '.')) / 100
                        y = float(parts[1].replace(',', '.')) / 100
                        processed_data.append((f"{x:.{max_x_dec + 3}f}", f"{y:.{max_y_dec + 3}f}"))
                    except: continue

            output_dir = os.path.dirname(file_path)
            base_name = os.path.basename(file_path).replace('-il.csv', '')
            suffix = "open" if self.profile_open else "close"
            txt_path = os.path.join(output_dir, f"{base_name}-converted-{suffix}.txt")

            # --- Scrittura SOLO TXT per Plotter ---
            with open(txt_path, 'w') as tf:
                tf.write(f"{'#Group':<8} {'Point':<6} {'X_cord':<15} {'Y_cord':<15} {'Z_cord':<6}\n")
                for i, (x, y) in enumerate(processed_data, 1):
                    tf.write(f"{1:<8} {i:<6} {x.replace('.', ','):<15} {y.replace('.', ','):<15} {0:<6}\n")
                if not self.profile_open:
                    tf.write("1 0\n")

            self.last_output_path = txt_path # Salviamo il percorso del TXT
            self.output_folder_path = output_dir
            self.status_label.setText("✅ Conversione in TXT riuscita!")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.post_conversion_frame.show()

        except Exception as e:
            self.status_label.setText(f"❌ Errore: {e}")
            self.status_label.setStyleSheet("color: #F44336;")

    def open_output_folder(self):
        if self.output_folder_path:
            os.startfile(self.output_folder_path)

    def send_to_plotter(self):
        if self.last_output_path and os.path.exists(self.last_output_path):
            if self.send_to_plotter_callback:
                self.send_to_plotter_callback(file_to_plot=self.last_output_path)
                self.status_label.setText("✅ Inviato al Plotter!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = CSVProcessorWidget(back_callback=lambda: print("Back"), send_to_plotter_callback=lambda f: print(f))
    widget.show()
    sys.exit(app.exec_())