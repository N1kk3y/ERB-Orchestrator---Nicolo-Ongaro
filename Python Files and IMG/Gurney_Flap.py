import os
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
    QGroupBox, QSpacerItem, QSizePolicy, QFileDialog, QSlider
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
        self.setWindowTitle("Gurney Flap Plotter")
        self.resize(1200, 800)

        # Parametri da salvare e rendere accessibili
        self.file_path = None
        self.points = None              # Array coordinate originali (Punto 1 richiesto)
        self.all_coordinates = None     # Alias esplicito per chiarezza
        
        self.select_mode = None
        self.idx_p1 = None              # Indice Punto TE
        self.idx_p2 = None              # Indice Punto 2
        
        # Dati estratti e salvati per accesso globale (Punto 2 richiesto)
        self.point_te = None            # Coordinate Punto TE
        self.point_2 = None             # Coordinate Punto 2
        self.slider_pos_idx = None      # Posizione slider relativa ai 50 punti
        self.slider_points_50 = []      # Array con i 50 punti del profilo
        self.gurney_interp_points = []  # Array con tutti i punti interpolati del Gurney
        
        self.interp_points = []         # Backup interno per calcoli
        self.gurney_items = []
        self.interp_gurney_item = None

        # Layout principale
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5,5,5,5)
        self.main_layout.setSpacing(10)

        # Top bar
        top_layout = QHBoxLayout()
        self.select_file_btn = QPushButton("📄 Seleziona file TXT")
        self.select_file_btn.setStyleSheet(button_style("#4CAF50","#45A049"))
        self.select_file_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.select_file_btn.clicked.connect(self.select_file_dialog)
        top_layout.addWidget(self.select_file_btn, alignment=Qt.AlignLeft)

        self.title_label = QLabel("Gurney Flap Plotter")
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

        # Pulsanti Punto 1 e Punto 2
        self.btn_p1 = QPushButton("Punto 1 TE")
        self.btn_p1.setStyleSheet(button_style("#29B6F6","#03A9F4"))
        self.btn_p1.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_p1.clicked.connect(lambda: self.set_mode("P1"))
        self.control_layout.addWidget(self.btn_p1)

        self.btn_p2 = QPushButton("Punto 2")
        self.btn_p2.setStyleSheet(button_style("#29B6F6","#03A9F4"))
        self.btn_p2.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_p2.clicked.connect(lambda: self.set_mode("P2"))
        self.control_layout.addWidget(self.btn_p2)

        # Altezza Gurney
        self.height_entry = self.create_labeled_entry("Altezza:", "0.01")
        self.height_entry.textChanged.connect(self.update_gurney)

        # Slider per lato verticale Punto2
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(2, 50)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.update_gurney)
        self.control_layout.addWidget(QLabel("Estendi lato Punto2"))
        self.control_layout.addWidget(self.slider)

        # Interpola gurney
        self.interpolation_entry = self.create_labeled_entry("Interpolazione:", "10")
        self.interp_btn = QPushButton("Genera punti interpolati")
        self.interp_btn.setStyleSheet(button_style("#FF9800","#FB8C00"))
        self.interp_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.interp_btn.clicked.connect(self.interpolate_gurney_points)
        self.control_layout.addWidget(self.interp_btn)

        # Pulsante reset selezioni/Gurney
        self.reset_btn = QPushButton("Reset Gurney/Selezioni")
        self.reset_btn.setStyleSheet(button_style("#f44336","#d32f2f"))
        self.reset_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.reset_btn.clicked.connect(self.reset_gurney)
        self.control_layout.addWidget(self.reset_btn)

        # Pulsante esporta file
        self.export_btn = QPushButton("Esporta profilo + Gurney")
        self.export_btn.setStyleSheet(button_style("#8E24AA","#6A1B9A"))
        self.export_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.export_btn.clicked.connect(self.export_profile_with_gurney)
        self.control_layout.addWidget(self.export_btn)

        self.control_layout.addSpacerItem(QSpacerItem(20,20,QSizePolicy.Minimum,QSizePolicy.Expanding))

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_layout.addWidget(self.plot_widget)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.addLegend()
        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)

        if self.back_callback:
            back_btn = QPushButton("⬅️ Torna al menu")
            back_btn.setFixedHeight(40)
            back_btn.setStyleSheet(button_style("#9E9E9E","#757575"))
            back_btn.setCursor(QCursor(Qt.PointingHandCursor))
            back_btn.clicked.connect(self.back_callback)
            self.control_layout.addWidget(back_btn)

    def create_labeled_entry(self, label_text, default_value):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Arial",10))
        entry = QLineEdit()
        entry.setText(default_value)
        layout.addWidget(label)
        layout.addWidget(entry)
        self.control_layout.addLayout(layout)
        return entry

    def reset_gurney(self):
        for item in self.gurney_items:
            self.plot_widget.removeItem(item)
        self.gurney_items.clear()
        self.interp_points = []
        self.slider_points_50 = []
        self.gurney_interp_points = []
        self.idx_p1 = None
        self.idx_p2 = None
        self.point_te = None
        self.point_2 = None
        self.btn_p1.setStyleSheet(button_style("#29B6F6","#03A9F4"))
        self.btn_p2.setStyleSheet(button_style("#29B6F6","#03A9F4"))
        self.plot_widget.clear()
        if self.points is not None:
            self.plot_widget.plot(self.points[:,0], self.points[:,1],
                                  pen=pg.mkPen('b', width=2),
                                  symbol='o', symbolBrush='b', name="Profilo")

    def set_mode(self, mode):
        self.select_mode = mode
        if mode == "P1":
            self.btn_p1.setStyleSheet(button_style("#0D47A1","#1565C0"))
            if self.idx_p2 is None:
                self.btn_p2.setStyleSheet(button_style("#29B6F6","#03A9F4"))
            else:
                self.btn_p2.setStyleSheet(button_style("#4CAF50","#45A049"))
        elif mode == "P2":
            self.btn_p2.setStyleSheet(button_style("#0D47A1","#1565C0"))
            if self.idx_p1 is None:
                self.btn_p1.setStyleSheet(button_style("#29B6F6","#03A9F4"))
            else:
                self.btn_p1.setStyleSheet(button_style("#4CAF50","#45A049"))

    def select_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file TXT", "", "TXT Files (*.txt)")
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        self.file_path = file_path
        pts_list = []
        with open(file_path,'r') as f:
            lines = [line.strip() for line in f if line.strip() != "" and not line.startswith("#")]
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        x = float(parts[2].replace(',', '.'))
                        y = float(parts[3].replace(',', '.'))
                        pts_list.append([x, y])
                    except:
                        continue
        # Punto 1 richiesto: salvataggio array completo coordinate
        self.all_coordinates = np.array(pts_list)
        self.points = self.all_coordinates 
        
        self.plot_widget.clear()
        self.plot_widget.plot(self.points[:,0], self.points[:,1],
                              pen=pg.mkPen('b', width=2),
                              symbol='o', symbolBrush='b', name="Profilo")

    def mouse_clicked(self, event):
        if self.points is None or self.select_mode is None:
            return
        pos = self.plot_widget.plotItem.vb.mapSceneToView(event.scenePos())
        distances = np.linalg.norm(self.points - np.array([pos.x(), pos.y()]), axis=1)
        idx = np.argmin(distances)

        if self.select_mode == "P1":
            self.idx_p1 = idx
            self.point_te = self.points[idx] # Salva Punto TE
            self.btn_p1.setStyleSheet(button_style("#4CAF50","#45A049"))
        elif self.select_mode == "P2":
            self.idx_p2 = idx
            self.point_2 = self.points[idx] # Salva Punto 2
            self.btn_p2.setStyleSheet(button_style("#4CAF50","#45A049"))

        p = self.points[idx]
        self.plot_widget.plot(np.array([p[0]]), np.array([p[1]]),
                              pen=None, symbol='o', symbolBrush='r', symbolSize=8)
        self.select_mode = None

        if self.idx_p1 is not None and self.idx_p2 is not None:
            self.interpolate_profile()

    def interpolate_profile(self):
        """Estrae Punto TE, Punto 2 e l'array dei 50 punti del profilo."""
        i1, i2 = sorted([self.idx_p1, self.idx_p2])
        segment = self.points[i1:i2+1] if i1 < i2 else self.points[i2:i1+1][::-1]

        s = np.cumsum(np.r_[0, np.linalg.norm(np.diff(segment, axis=0), axis=1)])
        t = np.linspace(0, s[-1], 50)
        interp = []
        for ti in t:
            j = np.searchsorted(s, ti) - 1
            j = np.clip(j, 0, len(segment)-2)
            u = (ti - s[j]) / (s[j+1]-s[j])
            interp.append(segment[j]*(1-u)+segment[j+1]*u)
        
        # Punto 2 richiesto: salvataggio array 50 punti
        self.slider_points_50 = np.array(interp)
        self.interp_points = self.slider_points_50

        for p in self.interp_points:
            self.plot_widget.plot(np.array([p[0]]), np.array([p[1]]),
                                  pen=None, symbol='o', symbolBrush='g', symbolSize=5)
        self.update_gurney()
        
        return self.point_te, self.point_2, self.slider_points_50

    def update_gurney(self):
        for item in self.gurney_items:
            self.plot_widget.removeItem(item)
        self.gurney_items.clear()

        if hasattr(self, "interp_gurney_item") and self.interp_gurney_item is not None:
            self.plot_widget.removeItem(self.interp_gurney_item)
            self.interp_gurney_item = None

        if len(self.interp_points) == 0 or self.idx_p1 is None or self.idx_p2 is None:
            return

        try:
            h = float(self.height_entry.text())
        except:
            return

        # Punto 2 richiesto: Slider Position
        self.slider_pos_idx = self.slider.value()
        count = self.slider_pos_idx
        
        base_pts = self.interp_points[-count:]
        if len(base_pts) < 2:
            return

        vec_TE = self.points[self.idx_p2] - self.points[self.idx_p1]
        n = np.array([-vec_TE[1], vec_TE[0]])
        n /= np.linalg.norm(n)

        top_pts = np.array(base_pts) + n*h

        self.gurney_items.append(pg.PlotDataItem([p[0] for p in base_pts], [p[1] for p in base_pts], pen=pg.mkPen('r', width=2)))
        self.gurney_items.append(pg.PlotDataItem([p[0] for p in top_pts], [p[1] for p in top_pts], pen=pg.mkPen('r', width=2)))
        self.gurney_items.append(pg.PlotDataItem([base_pts[0][0], top_pts[0][0]], [base_pts[0][1], top_pts[0][1]], pen=pg.mkPen('r', width=2)))
        self.gurney_items.append(pg.PlotDataItem([base_pts[-1][0], top_pts[-1][0]], [base_pts[-1][1], top_pts[-1][1]], pen=pg.mkPen('r', width=2)))

        for item in self.gurney_items:
            self.plot_widget.addItem(item)

    def interpolate_gurney_points(self):
        """Estrae e restituisce l'array con tutti i punti interpolati del Gurney."""
        if len(self.interp_points) == 0 or self.idx_p1 is None or self.idx_p2 is None:
            return None

        try:
            N = int(self.interpolation_entry.text())
            h = float(self.height_entry.text())
        except:
            return None
        
        if N < 2: return None

        if self.interp_gurney_item is not None:
            self.plot_widget.removeItem(self.interp_gurney_item)

        count = self.slider.value()
        base_pts = self.interp_points[-count:]
        vec_TE = self.points[self.idx_p2] - self.points[self.idx_p1]
        n = np.array([-vec_TE[1], vec_TE[0]])
        n /= np.linalg.norm(n)
        top_pts = np.array(base_pts) + n*h

        left_side = np.array([base_pts[0], top_pts[0]])
        right_side = np.array([base_pts[-1], top_pts[-1]])
        top_side = top_pts[1:-1] if len(top_pts) > 2 else np.empty((0,2))

        gurney_perimeter = np.vstack([left_side, top_side, right_side[::-1]])

        s = np.cumsum(np.r_[0, np.linalg.norm(np.diff(gurney_perimeter, axis=0), axis=1)])
        t = np.linspace(0, s[-1], N)

        interp_pts = []
        for ti in t:
            j = np.searchsorted(s, ti) - 1
            j = np.clip(j, 0, len(gurney_perimeter)-2)
            u = (ti - s[j]) / (s[j+1] - s[j])
            interp_pts.append(gurney_perimeter[j]*(1-u) + gurney_perimeter[j+1]*u)
        
        # Punto 2 richiesto: salvataggio array punti interpolati gurney
        self.gurney_interp_points = np.array(interp_pts)

        self.interp_gurney_item = pg.PlotDataItem(
            self.gurney_interp_points[:,0], self.gurney_interp_points[:,1],
            pen=None, symbol='o', symbolBrush='b', symbolSize=6,
            name="Interpolazione Gurney"
        )
        self.plot_widget.addItem(self.interp_gurney_item)
        
        return self.gurney_interp_points

    def export_profile_with_gurney(self):
        """Mostra a terminale tutti i dati estratti e salvati."""
        print("\n" + "="*50)
        print("DEBUG: DATI SALVATI NEL SISTEMA")
        print("="*50)

        # 1) Array coordinate totali dal file
        if self.all_coordinates is not None:
            print(f"1) Coordinate totali (da file): {len(self.all_coordinates)} punti caricati.")
            print(f"   Esempio prime 2 righe: \n{self.all_coordinates[:2]}")
        else:
            print("1) Coordinate totali: NESSUN FILE CARICATO")

        print("-" * 30)

        # 2) Parametri estratti dalla logica Gurney
        print(f"2) Punto TE (P1): {self.point_te}")
        print(f"3) Punto 2 (P2): {self.point_2}")
        print(f"4) Posizione Slider (Indice): {self.slider_pos_idx}")
        
        if self.slider_points_50 is not None and len(self.slider_points_50) > 0:
            print(f"5) Array 50 punti profilo: {len(self.slider_points_50)} punti generati.")
        else:
            print("5) Array 50 punti profilo: NON ANCORA GENERATO")

        if len(self.gurney_interp_points) > 0:
            print(f"6) Array Gurney interpolato: {len(self.gurney_interp_points)} punti calcolati.")
            print(f"   Ultimo punto Gurney: {self.gurney_interp_points[-1]}")
        else:
            print("6) Array Gurney interpolato: NON ANCORA GENERATO (clicca 'Genera punti interpolati')")

        print("="*50 + "\n")