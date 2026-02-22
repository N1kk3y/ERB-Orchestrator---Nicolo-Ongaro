import os
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QGroupBox, QSpacerItem, QSizePolicy, QFileDialog
)
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt
import pyqtgraph as pg

# Stile pulsanti coerente
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

class AirfoilsPlotterWidget(QWidget):
    def __init__(self, back_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.setWindowTitle("Airfoils Plotter")
        self.resize(1200, 800)

        self.file_path = None
        self.points = None
        self.scale_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.angle_deg = 0.0
        self.origin_point = None
        self.min_y = None
        self.vertical_distance = None

        self.advanced_view = False  # inizialmente off
        self.advanced_labels = []   # lista per tenere traccia dei TextItem


        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5,5,5,5)
        self.main_layout.setSpacing(10)

        # ----- Top bar con titolo e pulsante verde -----
        top_layout = QHBoxLayout()
        self.select_file_btn = QPushButton("📄 Seleziona file TXT")
        self.select_file_btn.setStyleSheet(button_style("#4CAF50","#45A049"))
        self.select_file_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.select_file_btn.clicked.connect(self.select_file_dialog)
        top_layout.addWidget(self.select_file_btn, alignment=Qt.AlignLeft)

        self.title_label = QLabel("Airfoils Plotter")
        self.title_label.setFont(QFont("Arial",14,QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.title_label, stretch=1)

        top_layout.addStretch()
        self.main_layout.addLayout(top_layout)

        # Layout contenitore controlli + plot
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        self.main_layout.addLayout(content_layout)

        # Controlli
        self.control_frame = QGroupBox("Controlli")
        self.control_frame.setFont(QFont("Arial", 10, QFont.Bold))
        self.control_layout = QVBoxLayout(self.control_frame)
        self.control_layout.setContentsMargins(5,5,5,5)
        self.control_layout.setSpacing(5)
        content_layout.addWidget(self.control_frame, 1)

        # Plot
        self.plot_layout = QVBoxLayout()
        content_layout.addLayout(self.plot_layout, 3)

        # Creazione controlli
        self.create_controls()

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_layout.addWidget(self.plot_widget)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.addLegend()

        # Label info sotto il plot
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Arial",10))
        self.info_label.setAlignment(Qt.AlignLeft)
        self.info_label.setTextFormat(Qt.RichText)
        self.plot_layout.addWidget(self.info_label)

        # Pulsante Indietro
        if self.back_callback:
            back_btn = QPushButton("⬅️ Torna al menu")
            back_btn.setFixedHeight(40)
            back_btn.setStyleSheet(button_style("#9E9E9E","#757575"))
            back_btn.setCursor(QCursor(Qt.PointingHandCursor))
            back_btn.clicked.connect(self.back_callback)
            self.control_layout.addWidget(back_btn)

    def select_file_path(self, file_path):
        self.load_file(file_path)

    # -----------------------------
    # CREAZIONE CONTROLLI
    # -----------------------------
    def create_controls(self):
        # Parametri
        self.angle_entry = self.create_labeled_entry("Angolo (°):", "0.0")
        self.scale_entry = self.create_labeled_entry("Scala globale:", "1.0")
        self.scale_x_entry = self.create_labeled_entry("Scala X:", "1.0")
        self.scale_y_entry = self.create_labeled_entry("Scala Y:", "1.0")

        # Pulsanti Aggiorna / Reset
        buttons_layout = QHBoxLayout()
        self.update_btn = QPushButton("Aggiorna")
        self.update_btn.setStyleSheet(button_style("#2196F3","#1976D2"))
        self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_btn.clicked.connect(self.update_plot)
        buttons_layout.addWidget(self.update_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet(button_style("#f44336","#d32f2f"))
        self.reset_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.reset_btn.clicked.connect(self.reset_parameters)
        buttons_layout.addWidget(self.reset_btn)

        self.view_export_btn = QPushButton("Visualizzazione Avanzata")
        self.view_export_btn.setStyleSheet(button_style("#FF5722","#F4511E"))
        self.view_export_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.view_export_btn.clicked.connect(self.toggle_advanced_view)
        self.control_layout.addWidget(self.view_export_btn)

        self.control_layout.addLayout(buttons_layout)

        # Spacer
        self.control_layout.addSpacerItem(QSpacerItem(20,20,QSizePolicy.Minimum,QSizePolicy.Expanding))

    def create_labeled_entry(self,label_text,default_value):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Arial",10))
        entry = QLineEdit()
        entry.setText(default_value)
        entry.returnPressed.connect(self.update_plot)
        layout.addWidget(label)
        layout.addWidget(entry)
        self.control_layout.addLayout(layout)
        return entry

    # -----------------------------
    # SELEZIONE FILE
    # -----------------------------
    def select_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file TXT", "", "TXT Files (*.txt)")
        if file_path:
            self.load_file(file_path)

    # -----------------------------
    # CARICAMENTO FILE
    # -----------------------------
    def load_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        self.file_path = file_path
        points = []
        self.draw_extra_line = False  # flag per linea extra
        with open(file_path,'r') as f:
            lines = [line.strip() for line in f if line.strip() != "" and not line.startswith("#")]
            for line in lines:
                parts = line.split()
                # controlla se è la riga finale speciale "1 0"
                if len(parts) == 2 and parts[0] == "1" and parts[1] == "0":
                    self.draw_extra_line = True
                    continue  # non aggiungere ai punti
                if len(parts) >= 4:
                    try:
                        x = float(parts[2].replace(',', '.'))
                        y = float(parts[3].replace(',', '.'))
                        points.append([x, y])
                    except:
                        continue

        self.points = np.array(points)
        self.update_plot()

    # -----------------------------
    # RESET PARAMETRI
    # -----------------------------
    def reset_parameters(self):
        self.scale_factor=self.scale_x=self.scale_y=1.0
        self.angle_deg=0.0
        self.angle_entry.setText("0.0")
        self.scale_entry.setText("1.0")
        self.scale_x_entry.setText("1.0")
        self.scale_y_entry.setText("1.0")
        self.update_plot(reset_view=True)

    # -----------------------------
    # UPDATE PLOT
    # -----------------------------
    def update_plot(self, reset_view=False):
        if self.points is None:
            return
        try:
            self.angle_deg = float(self.angle_entry.text())
            self.scale_factor = float(self.scale_entry.text())
            self.scale_x = float(self.scale_x_entry.text())
            self.scale_y = float(self.scale_y_entry.text())
        except:
            return

        points = self.points.copy()
        points[:, 0] *= self.scale_factor * self.scale_x
        points[:, 1] *= self.scale_factor * self.scale_y
        points = self.rotate_profile(points, self.angle_deg)

        upper, lower = self.split_upper_lower(points)
        self.min_y = np.min(points[:, 1])
        idx_origin = np.argmin(np.linalg.norm(points, axis=1))
        self.origin_point = points[idx_origin]
        self.vertical_distance = self.origin_point[1] - self.min_y

        self.plot_widget.clear()
        self.plot_widget.addLegend()

        # Disegna spline superiore e inferiore
        if len(upper) > 0:
            self.plot_widget.plot(
                upper[:, 0], upper[:, 1],
                pen=pg.mkPen('b', width=2),
                symbol='o', symbolBrush='b',
                name="Spline Superiore"
            )
        if len(lower) > 0:
            self.plot_widget.plot(
                lower[:, 0], lower[:, 1],
                pen=pg.mkPen('r', width=2),
                symbol='o', symbolBrush='r',
                name="Spline Inferiore"
            )

        # Linea base e origine
        self.plot_widget.addLine(y=self.min_y, pen=pg.mkPen('w', width=2))
        self.plot_widget.plot(
            [self.origin_point[0], self.origin_point[0]],
            [self.origin_point[1], self.min_y],
            pen=pg.mkPen('y', width=2)
        )
        self.plot_widget.plot(
            [self.origin_point[0]], [self.origin_point[1]],
            pen=None, symbol='x', symbolSize=12, symbolBrush='k'
        )

        # Disegna linea di chiusura del profilo
        if getattr(self, 'draw_extra_line', False) and len(upper) > 0 and len(lower) > 0:
            self.plot_widget.plot(
                [lower[-1, 0], upper[0, 0]],  # <- collegamento corretto
                [lower[-1, 1], upper[0, 1]],  # <- collegamento corretto
                pen=pg.mkPen('m', width=2, style=Qt.DashLine),
                name="Linea Chiusura Profilo"
            )

        # Info label
        info_text = (
            f"Origine: ({self.origin_point[0]:.3f}, {self.origin_point[1]:.3f})<br>"
            f"Distanza verticale: <b>{self.vertical_distance:.3f}</b><br>"
            f"Punti totali: {len(points)}<br>"
            f"Spline superiore: {len(upper)} punti, Spline inferiore: {len(lower)} punti"
        )
        self.info_label.setText(info_text)

        # Titolo plot
        if self.file_path:
            file_name = os.path.splitext(os.path.basename(self.file_path))[0]
            self.plot_widget.setTitle(
                f"{file_name} | Angolo: {self.angle_deg}° | "
                f"ScalaGlobale: {self.scale_factor} | ScalaX: {self.scale_x} | ScalaY: {self.scale_y}"
            )

        self.plot_widget.setLabel('left', 'Y [mm]')
        self.plot_widget.setLabel('bottom', 'X [mm]')

        if reset_view:
            self.plot_widget.enableAutoRange()


    # -----------------------------
    # ROTAZIONE & SPLIT
    # -----------------------------
    def rotate_profile(self,points,angle_deg):
        angle_rad=np.deg2rad(angle_deg)
        rot=np.array([[np.cos(angle_rad),-np.sin(angle_rad)],
                      [np.sin(angle_rad),np.cos(angle_rad)]])
        return points @ rot.T

    def split_upper_lower(self,points):
        mid=len(points)//2
        search=5
        start=max(0,mid-search)
        end=min(len(points)-1,mid+search)
        min_dist=np.inf
        split_index=mid
        for i in range(start,end+1):
            dist=np.linalg.norm(points[i])
            if dist<min_dist:
                min_dist=dist
                split_index=i
        return points[:split_index], points[split_index:]

    def toggle_advanced_view(self):
        if self.points is None:
            return

        if not self.advanced_view:
            # MOSTRA numerazione punti
            self.advanced_labels = []  # reset lista
            for idx, (x, y) in enumerate(self.points, start=1):
                text = f"{idx}\n({x:.3f}, {y:.3f})"
                label = pg.TextItem(text, anchor=(0,1), color='w')
                label.setFont(QFont("Arial", 8))
                label.setPos(x, y)
                self.plot_widget.addItem(label)
                self.advanced_labels.append(label)

            self.advanced_view = True
        else:
            # NASCONDI numerazione punti
            for label in self.advanced_labels:
                self.plot_widget.removeItem(label)
            self.advanced_labels = []
            self.advanced_view = False
