import os
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, 
    QHBoxLayout, QLineEdit, QTextEdit, QProgressBar, QDialog
)
from PyQt5.QtCore import Qt
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

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

class AnsysReportWidget(QWidget):
    def __init__(self, back_callback=None):
        super().__init__()
        self.back_callback = back_callback
        self.html_path = None
        self.base_folder = None
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(12)

        self.title_label = QLabel("Ansys Report Generator")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")
        self.main_layout.addWidget(self.title_label)

        # Selezione File
        file_layout = QHBoxLayout()
        self.btn_html = QPushButton("📁 Seleziona HTML")
        self.btn_html.setStyleSheet(button_style("#2196F3", "#1976D2"))
        self.btn_html.clicked.connect(self.select_html)
        
        self.btn_folder = QPushButton("📂 Cartella Immagini")
        self.btn_folder.setStyleSheet(button_style("#2196F3", "#1976D2"))
        self.btn_folder.clicked.connect(self.select_folder)
        
        file_layout.addWidget(self.btn_html)
        file_layout.addWidget(self.btn_folder)
        self.main_layout.addLayout(file_layout)

        self.path_label = QLabel("Seleziona i file per iniziare...")
        self.main_layout.addWidget(self.path_label)

        # Campi Input
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("Titolo Report")
        self.main_layout.addWidget(QLabel("Titolo:"))
        self.main_layout.addWidget(self.input_title)

        self.input_author = QLineEdit()
        self.input_author.setPlaceholderText("Nome e Cognome")
        self.main_layout.addWidget(QLabel("Autore:"))
        self.main_layout.addWidget(self.input_author)

        self.input_config = QLineEdit()
        self.input_config.setPlaceholderText("Esempio : Naca4412 + S1223 + S1223")
        self.main_layout.addWidget(QLabel("Configurazione"))
        self.main_layout.addWidget(self.input_config)

        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("Eventuali annotazione")
        self.main_layout.addWidget(QLabel("Note"))
        self.main_layout.addWidget(self.input_note)


        # Generazione
        self.btn_generate = QPushButton("GENERA PDF")
        self.btn_generate.setStyleSheet(button_style("#4CAF50", "#45A049"))
        self.btn_generate.setFixedHeight(60)
        self.btn_generate.clicked.connect(self.generate_report)
        self.main_layout.addWidget(self.btn_generate)

        if self.back_callback:
            self.back_btn = QPushButton("⬅️ Torna al menu")
            self.back_btn.setStyleSheet(button_style("#9E9E9E", "#757575"))
            self.back_btn.clicked.connect(self.back_callback)
            self.main_layout.addWidget(self.back_btn)

    def select_html(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona HTML", "", "HTML Files (*.html)")
        if path: self.html_path = path
        self.update_label()

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Seleziona cartella immagini")
        if path: self.base_folder = path
        self.update_label()

    def update_label(self):
        h = "OK" if self.html_path else "NO"
        f = "OK" if self.base_folder else "NO"
        self.path_label.setText(f"Stato: HTML {h} | Folder {f}")

    def generate_report(self):
        if not self.html_path or not self.base_folder:
            return

        author_name = self.input_author.text().strip() or "Autore"
        default_filename = f"Ansys - Report - {author_name}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Salva PDF", default_filename, "PDF Files (*.pdf)")

        if not save_path: 
            return

        try:
            from PyQt5.QtWidgets import QApplication
            from datetime import datetime
            with open(self.html_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')

            dp_label = soup.find(lambda tag: tag.name == "span" and "Design Points" in tag.text)
            dp_table_html = dp_label.find_next('table')

            rows = []
            for tr in dp_table_html.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
                if cells: 
                    rows.append(cells)

            total_dps = len(rows) - 2  # tolgo header + eventuale riga totale

            # --- POP-UP PROGRESSO ---
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Esportazione Report")
            progress_dialog.setFixedSize(350, 150)
            pg_layout = QVBoxLayout(progress_dialog)
            pg_label = QLabel("Preparazione dati...")
            pg_bar = QProgressBar()
            pg_bar.setMaximum(total_dps if total_dps > 0 else 1)
            pg_layout.addWidget(pg_label)
            pg_layout.addWidget(pg_bar)
            progress_dialog.show()
            QApplication.processEvents()

            doc = SimpleDocTemplate(save_path, pagesize=landscape(A4), 
                                    rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
            elements = []
            styles = getSampleStyleSheet()
            from reportlab.lib.styles import ParagraphStyle
            cell_style = ParagraphStyle(name='CellStyle', fontSize=4, leading=5, alignment=1)

            # --- SEZIONE INFO (senza striscia blu / testo reparto) ---
            elements.append(Paragraph(f"<b>{self.input_title.text()}</b>", styles['Title']))
            elements.append(Spacer(1, 12))

            info_data = [
                ['Autore', self.input_author.text()],
                ['Data', datetime.now().strftime('%d/%m/%Y')],
                ['Configurazione', self.input_config.text()],
                ['Note', self.input_note.text()]
            ]
            info_table = Table(info_data, colWidths=[120, 400])
            info_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 20))

            # --- TABELLA DESIGN POINTS CON LINK ---
            if rows:
                elements.append(Paragraph('<a name="tabella_dps"/>', cell_style))
                elements.append(Paragraph("Tabella Parametri Design Points", styles['Heading2']))
                formatted_rows = []
                for row_idx, row in enumerate(rows):
                    new_row = []
                    for col_idx, cell in enumerate(row):
                        if col_idx == 0 and str(cell).startswith("DP"):
                            # DP in blu
                            link = Paragraph(f'<a href="#{cell}"><font color="blue">{cell}</font></a>', cell_style)
                            new_row.append(link)
                        else:
                            new_row.append(Paragraph(str(cell), cell_style))
                    formatted_rows.append(new_row)

                num_cols = len(rows[0])
                available_width = 810
                col_w = available_width / num_cols

                t = Table(formatted_rows, colWidths=[col_w]*num_cols, repeatRows=1)
                t.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.2, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0.5),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0.5),
                ]))
                elements.append(t)

            elements.append(PageBreak())

           # --- CICLO DP CON TUTTO SU UNA PAGINA ---  
            count = 0
            header_row = rows[0]  # prima riga tabella (intestazioni colonne)
            for r in rows[1:]:
                name = r[0]
                if not name.startswith("DP"): 
                    continue 

                count += 1
                pg_label.setText(f"Aggiunta immagini: {name} ({count} / {total_dps})")
                pg_bar.setValue(count)
                QApplication.processEvents()

                # Titolo più piccolo
                elements.append(Paragraph(f'<a name="{name}"/> {name}', styles['Heading3']))
                elements.append(Spacer(1, 5))

                # Link "Torna alla tabella"
                # Link "Torna alla tabella" in blu
                elements.append(Paragraph('<a href="#tabella_dps"><font color="blue">Torna alla tabella</font></a>', styles['Normal']))
                elements.append(Spacer(1, 5))

                # --- COPIA RIGA HEADER + RIGA PARAMETRI DEL DP ---
                small_cell_style = ParagraphStyle(
                    name='SmallCell', fontSize=6, leading=7, alignment=1
                )
                formatted_rows = []
                for row_to_copy in [header_row, r]:
                    formatted_row = [Paragraph(str(cell), small_cell_style) for cell in row_to_copy]
                    formatted_rows.append(formatted_row)
                dp_table_copy = Table(formatted_rows, colWidths=[col_w]*len(header_row))
                dp_table_copy.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.2, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 1),
                    ('RIGHTPADDING', (0,0), (-1,-1), 1),
                ]))
                elements.append(dp_table_copy)
                elements.append(Spacer(1, 5))

                # Aggiunta immagini una sotto l'altra sulla stessa pagina
                folder_name = name.lower().replace(" ", "")
                img_dir = os.path.join(self.base_folder, "FluentObjects", folder_name, "FFF")

                found = False
                for img_name in ["velocity.png", "y+.png"]:
                    img_path = os.path.join(img_dir, img_name)
                    if os.path.exists(img_path):
                        img = Image(img_path, width=380, height=190)  # ridotte per stare su pagina
                        elements.append(img)
                        elements.append(Spacer(1, 5))
                        found = True

                if not found:
                    elements.append(Paragraph(f"Nessun dato grafico per {name}", styles['Italic']))

                # PageBreak alla fine del DP, così tutto rimane su una pagina
                elements.append(PageBreak())



            # --- FASE DI SCRITTURA ---
            pg_label.setText("🔥 Scrittura file PDF in corso... (Attendere)")
            pg_bar.setRange(0, 0)
            QApplication.processEvents()
            doc.build(elements)

            # --- FINE OPERAZIONE ---
            pg_bar.setRange(0, 100)
            pg_bar.setValue(100)
            pg_label.setText("✅ Scrittura completata con successo!")
            btn_close = QPushButton("OK")
            btn_close.clicked.connect(progress_dialog.close)
            pg_layout.addWidget(btn_close)

        except Exception as e:
            print(f"ERRORE: {e}")
            if 'progress_dialog' in locals(): 
                progress_dialog.close()
