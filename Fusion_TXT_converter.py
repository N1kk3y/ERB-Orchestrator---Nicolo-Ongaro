import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, 
    QSpacerItem, QSizePolicy, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QPixmap

# --- Stili CSS (Esattamente dal primo script) ---
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

def get_toggle_style(active=False):
    if active:
        return get_button_style("#4CAF50", "#45A049") # Verde
    return get_button_style("#9E9E9E", "#757575")     # Grigio

class FusionConverterWidget(QWidget):
    def __init__(self, back_callback=None, send_to_plotter_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.send_to_plotter_callback = send_to_plotter_callback
        self.last_output_file = None
        self.output_folder = None
        
        # DEFAULT: Profilo Chiuso (come da tua logica Fusion)
        self.profile_open = False  
        self.selected_file_path = None 

        self.setWindowTitle("Fusion 360 TXT Converter")
        self.resize(850, 700) # Dimensione identica al primo script

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setSpacing(15)

        # --- 1. PULSANTE "IMPORTA FILE" ---
        self.import_file_btn = QPushButton("Seleziona file TXT da Fusion 360")
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

        # --- 2. SEZIONE OPZIONI (VERTICALE - CLONATA) ---
        self.options_container = QVBoxLayout()
        self.options_container.setSpacing(20)

        # --- Riga Profilo Aperto ---
        self.open_row_layout = QHBoxLayout()
        self.open_img_label = QLabel()
        open_pix = QPixmap("Aperto.png")
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
        close_pix = QPixmap("Chiuso.png")
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

        # --- 3. PULSANTE "CONVERTI" (IDENTICO) ---
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

        # --- 4. MENU POST-CONVERSIONE (IDENTICO) ---
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

    # --- METODI LOGICA (RIPRISTINATI) ---
    def set_profile_state(self, is_open):
        self.profile_open = is_open
        self.update_toggle_styles()

    def update_toggle_styles(self):
        self.toggle_open_btn.setChecked(self.profile_open)
        self.toggle_close_btn.setChecked(not self.profile_open)
        self.toggle_open_btn.setStyleSheet(get_toggle_style(self.profile_open))
        self.toggle_close_btn.setStyleSheet(get_toggle_style(not self.profile_open))

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file Fusion 360", "", "TXT Files (*.txt)")
        if file_path:
            self.selected_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.status_label.setText("")
            self.post_conversion_frame.hide()

    def convert_file(self):
        if not self.selected_file_path:
            self.status_label.setText("⚠️ Seleziona prima un file TXT!")
            self.status_label.setStyleSheet("color: #FF9800;")
            return
        
        input_file = self.selected_file_path
        scale_factor = 0.1 # Come nel tuo script originale Fusion

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

            # Rimuove duplicati seconda metà (Tua Logica Specifica)
            n = len(points_list)
            if n > 1:
                first_half = points_list[:n // 2]
                second_half = points_list[n // 2:]
                first_coords = set((round(x, 9), round(y, 9)) for x, y, z in first_half)
                filtered_second_half = [p for p in second_half if (round(p[0], 9), round(p[1], 9)) not in first_coords]
                points_list = first_half + filtered_second_half

            dir_name = os.path.dirname(input_file)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            suffix = "open" if self.profile_open else "close"
            output_file = os.path.join(dir_name, f"{base_name}_converted-{suffix}.txt")

            self.last_output_file = output_file
            self.output_folder = dir_name

            lines_out = ["#Group   Point   X_cord          Y_cord          Z_cord"]
            for x, y, z in points_list:
                lines_out.append("{:<8} {:<6} {:<15} {:<15} {:<5}".format(
                    group_id, point_id, f"{x:.9f}".replace('.', ','), f"{y:.9f}".replace('.', ','), int(z)
                ))
                point_id += 1

            if not self.profile_open:
                lines_out.append("1 0")

            with open(output_file, 'w') as f_out:
                for l in lines_out:
                    f_out.write(l + "\n")

            self.status_label.setText("✅ Conversione in TXT riuscita!")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.post_conversion_frame.show()

        except Exception as e:
            self.status_label.setText(f"❌ Errore: {e}")
            self.status_label.setStyleSheet("color: #F44336;")

    def open_output_folder(self):
        if self.output_folder and os.path.isdir(self.output_folder):
            subprocess.Popen(["explorer", os.path.normpath(self.output_folder)])

    def send_to_plotter(self):
        if self.last_output_file and os.path.isfile(self.last_output_file):
            if self.send_to_plotter_callback:
                self.send_to_plotter_callback(file_to_plot=self.last_output_file)
                self.status_label.setText("✅ Inviato al Plotter!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = FusionConverterWidget(back_callback=lambda: print("Back"), send_to_plotter_callback=lambda f: print(f))
    widget.show()
    sys.exit(app.exec_())