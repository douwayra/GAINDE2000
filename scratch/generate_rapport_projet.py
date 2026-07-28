#!/usr/bin/env python3
"""
Rapport Projet GAINDE2000 / Orbus Sentinel
Generateur PDF professionnel complet avec schemas et logo
"""

import os
import sys
import tempfile
from datetime import datetime

# Make sure we run from the project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm, mm
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.legends import Legend
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# ─────────────────────────────────────────────────────────────
# PALETTE COULEURS ORBUS SENTINEL
# ─────────────────────────────────────────────────────────────
C_NAVY       = colors.HexColor('#0f172a')
C_BLUE       = colors.HexColor('#0891b2')
C_BLUE_DARK  = colors.HexColor('#0369a1')
C_BLUE_LIGHT = colors.HexColor('#e0f2fe')
C_SLATE      = colors.HexColor('#475569')
C_SLATE_LT   = colors.HexColor('#94a3b8')
C_BORDER     = colors.HexColor('#cbd5e1')
C_BG         = colors.HexColor('#f8fafc')
C_WHITE      = colors.white
C_RED        = colors.HexColor('#dc2626')
C_RED_LT     = colors.HexColor('#fee2e2')
C_GREEN      = colors.HexColor('#16a34a')
C_GREEN_LT   = colors.HexColor('#dcfce7')
C_AMBER      = colors.HexColor('#d97706')
C_AMBER_LT   = colors.HexColor('#fef3c7')
C_INDIGO     = colors.HexColor('#4f46e5')
C_TEAL       = colors.HexColor('#0d9488')
C_PURPLE     = colors.HexColor('#7c3aed')

# ─────────────────────────────────────────────────────────────
# CANVAS NUMEROTE AVEC EN-TETE ET PIED DE PAGE
# ─────────────────────────────────────────────────────────────
class OrbusCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, page_count):
        W, H = A4

        # ── PAGE DE COUVERTURE : pas d'en-tete/pied ──
        if self._pageNumber == 1:
            return

        self.saveState()

        # Bande bleue en haut
        self.setFillColor(C_NAVY)
        self.rect(0, H - 36, W, 36, fill=1, stroke=0)

        # Logo Orbus Sentinel dans la bande
        logo_path = "orbus_sentinel_logo.png"
        if os.path.exists(logo_path):
            try:
                self.drawImage(logo_path, 20, H - 30, width=90, height=20, mask='auto')
            except Exception:
                self.setFont("Helvetica-Bold", 9)
                self.setFillColor(C_WHITE)
                self.drawString(20, H - 22, "ORBUS SENTINEL")
        else:
            self.setFont("Helvetica-Bold", 9)
            self.setFillColor(C_WHITE)
            self.drawString(20, H - 22, "ORBUS SENTINEL")

        # Titre courant dans la bande
        self.setFont("Helvetica", 8)
        self.setFillColor(C_SLATE_LT)
        self.drawRightString(W - 20, H - 22, "Rapport Projet GAINDE2000  |  Confidentiel")

        # Pied de page
        self.setFillColor(C_NAVY)
        self.rect(0, 0, W, 26, fill=1, stroke=0)

        self.setFont("Helvetica", 7)
        self.setFillColor(C_SLATE_LT)
        self.drawString(20, 9, "CONFIDENTIEL  --  Direction Generale des Douanes du Senegal  --  Orbus Infinity")
        self.setFillColor(C_WHITE)
        self.setFont("Helvetica-Bold", 7)
        self.drawRightString(W - 20, 9, f"Page {self._pageNumber} / {page_count}")

        self.restoreState()


# ─────────────────────────────────────────────────────────────
# STYLES TYPOGRAPHIQUES
# ─────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['cover_title'] = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=C_WHITE,
        leading=34,
        spaceAfter=8,
        alignment=TA_LEFT
    )
    styles['cover_sub'] = ParagraphStyle(
        'CoverSub',
        fontName='Helvetica',
        fontSize=13,
        textColor=colors.HexColor('#bfdbfe'),
        leading=18,
        spaceAfter=4,
        alignment=TA_LEFT
    )
    styles['cover_meta'] = ParagraphStyle(
        'CoverMeta',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#94a3b8'),
        leading=13,
        spaceAfter=3,
        alignment=TA_LEFT
    )
    styles['section'] = ParagraphStyle(
        'Section',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=C_NAVY,
        spaceBefore=18,
        spaceAfter=8,
        leading=16,
        borderPadding=(0, 0, 4, 0)
    )
    styles['subsection'] = ParagraphStyle(
        'Subsection',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=C_BLUE_DARK,
        spaceBefore=10,
        spaceAfter=5,
        leading=13
    )
    styles['body'] = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=9,
        textColor=C_SLATE,
        leading=13,
        spaceAfter=5,
        alignment=TA_JUSTIFY
    )
    styles['bullet'] = ParagraphStyle(
        'Bullet',
        fontName='Helvetica',
        fontSize=9,
        textColor=C_SLATE,
        leading=13,
        spaceAfter=3,
        leftIndent=14,
        firstLineIndent=-10,
        alignment=TA_LEFT
    )
    styles['bold'] = ParagraphStyle(
        'Bold',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=C_NAVY,
        leading=13,
        spaceAfter=4
    )
    styles['th'] = ParagraphStyle(
        'TH',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=C_WHITE,
        leading=11
    )
    styles['td'] = ParagraphStyle(
        'TD',
        fontName='Helvetica',
        fontSize=8,
        textColor=C_SLATE,
        leading=11
    )
    styles['td_bold'] = ParagraphStyle(
        'TDBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=C_NAVY,
        leading=11
    )
    styles['caption'] = ParagraphStyle(
        'Caption',
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        textColor=C_SLATE_LT,
        leading=10,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    styles['toc'] = ParagraphStyle(
        'TOC',
        fontName='Helvetica',
        fontSize=9.5,
        textColor=C_NAVY,
        leading=16,
        spaceAfter=0,
        leftIndent=0
    )
    styles['toc_num'] = ParagraphStyle(
        'TOCNum',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=C_BLUE,
        leading=16,
        spaceAfter=0
    )
    styles['chapter_num'] = ParagraphStyle(
        'ChapterNum',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=C_BLUE,
        leading=12,
        spaceAfter=2
    )
    styles['callout'] = ParagraphStyle(
        'Callout',
        fontName='Helvetica',
        fontSize=8.5,
        textColor=C_NAVY,
        leading=13,
        leftIndent=10,
        rightIndent=10
    )
    styles['note'] = ParagraphStyle(
        'Note',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=C_AMBER,
        leading=11,
        spaceAfter=4
    )

    return styles


# ─────────────────────────────────────────────────────────────
# BLOCS UTILITAIRES
# ─────────────────────────────────────────────────────────────
def section_rule(story, s):
    """Ligne decorative sous un titre de section"""
    story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=8))

def callout_box(story, text, s, bg=None, border=None):
    """Encadre un texte dans un bloc colore"""
    bg = bg or C_BLUE_LIGHT
    border = border or C_BLUE
    data = [[Paragraph(text, s['callout'])]]
    t = Table(data, colWidths=[16.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEAFTER', (0,0), (0,-1), 3, border),  # bord gauche epais
        ('LINEBEFORE', (0,0), (0,-1), 3, border),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

def kpi_band(story, kpis):
    """
    Bande de 4 KPIs sur une ligne.
    kpis = [(label, valeur, couleur_fond, couleur_texte), ...]
    """
    cells = []
    for label, val, bg, fg in kpis:
        inner = [
            [Paragraph(f'<b>{val}</b>', ParagraphStyle('kv', fontName='Helvetica-Bold', fontSize=16, textColor=fg, leading=18, alignment=TA_CENTER))],
            [Paragraph(label, ParagraphStyle('kl', fontName='Helvetica', fontSize=7.5, textColor=fg, leading=10, alignment=TA_CENTER))]
        ]
        inner_t = Table(inner, colWidths=[3.9*cm])
        inner_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('ROUNDEDCORNERS', [4,4,4,4]),
        ]))
        cells.append(inner_t)

    row = Table([cells], colWidths=[4.05*cm]*len(kpis))
    row.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(row)
    story.append(Spacer(1, 10))

def std_table(story, headers, rows, s, col_widths=None, zebra=True):
    """Table standard avec en-tete bleue"""
    data = [[Paragraph(h, s['th']) for h in headers]]
    for i, row in enumerate(rows):
        data.append([Paragraph(str(c), s['td']) for c in row])

    if col_widths is None:
        total = 16.5 * cm
        col_widths = [total / len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), C_WHITE),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.4, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_BG] if zebra else [C_WHITE]),
    ]
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 6))

# ─────────────────────────────────────────────────────────────
# SCHEMAS VECTORIELS
# ─────────────────────────────────────────────────────────────

def draw_architecture_schema():
    """
    Schema d'architecture en couches (style layered diagram)
    Retourne un Drawing ReportLab
    """
    W, H = 480, 280
    d = Drawing(W, H)

    layers = [
        # (y, hauteur, couleur_fond, couleur_bord, titre, sous_titre)
        (220, 44, colors.HexColor('#f0fdf4'), C_GREEN, "SOURCES DE DONNEES",
         "Fichiers CSV historiques (1,8 M lignes)  |  SQL Server MSSQL (192.168.2.138)  |  DOSSIERTPS · FACTURE · CONTENIR"),
        (160, 44, colors.HexColor('#eff6ff'), C_BLUE_DARK, "COUCHE ETL & STOCKAGE",
         "Pipeline Polars (Rust)  |  DuckDB gainde_douane.db  |  SQLite users.db  |  Fallback JSON statique"),
        (100, 44, colors.HexColor('#fdf4ff'), C_PURPLE, "MOTEUR IA & SCORING",
         "Isolation Forest  |  K-Means Clustering  |  Z-Score  |  Score de risque 0-100"),
        (40, 44, colors.HexColor('#fff7ed'), C_AMBER, "API BACKEND (FastAPI / Python)",
         "27 routes REST  |  JWT + RBAC (7 roles)  |  Uvicorn ASGI  |  Traducteur SQL MSSQL"),
        (-20, 44, colors.HexColor('#fef2f2'), C_RED, "INTERFACE WEB (React + Vite)",
         "10 onglets  |  14 composants  |  ECharts  |  Theme clair/sombre  |  Chatbot IA"),
    ]

    for (y, h, bg, border, title, sub) in layers:
        actual_y = y + 20
        # Rectangle fond
        r = Rect(10, actual_y, W - 20, h, fillColor=bg, strokeColor=border, strokeWidth=1.5)
        d.add(r)
        # Titre
        d.add(String(24, actual_y + h - 14, title,
                     fontName='Helvetica-Bold', fontSize=8, fillColor=border))
        # Sous-titre
        d.add(String(24, actual_y + 8, sub,
                     fontName='Helvetica', fontSize=6.5, fillColor=C_SLATE))

    # Fleches de liaison
    arrow_x = W // 2
    for y_from, y_to in [(264, 244), (204, 184), (144, 124), (84, 64)]:
        d.add(Line(arrow_x, y_from, arrow_x, y_to,
                   strokeColor=C_SLATE_LT, strokeWidth=1.2))
        # Pointe de fleche (triangle vers le bas)
        tip = y_to
        d.add(Polygon([arrow_x-5, tip+6, arrow_x+5, tip+6, arrow_x, tip],
                      fillColor=C_SLATE_LT, strokeColor=C_SLATE_LT, strokeWidth=0))

    return d


def draw_rbac_schema():
    """
    Schema RBAC : roles utilisateurs avec droits
    """
    W, H = 480, 220
    d = Drawing(W, H)

    # Fond
    d.add(Rect(0, 0, W, H, fillColor=C_BG, strokeColor=C_BORDER, strokeWidth=0.5))

    # Titre centre
    d.add(String(W/2, H - 18, "Systeme de Controle d'Acces par Role (RBAC)",
                 fontName='Helvetica-Bold', fontSize=9, fillColor=C_NAVY,
                 textAnchor='middle'))

    roles = [
        ("admin",          C_RED,    "Tout",                     10),
        ("direction",      C_PURPLE, "Dashboard + PDF + Alertes", 100),
        ("inspecteur",     C_AMBER,  "Risques + Marquage",       190),
        ("transitaire",    C_BLUE,   "Dossiers (son bureau)",    280),
        ("partenaire",     C_TEAL,   "Fiabilite importateurs",   370),
        ("statisticien",   C_GREEN,  "Export CSV anonymise",     460),
        ("journaliste",    C_SLATE,  "Vue publique limitee",     550),
    ]

    box_w = 58
    box_h = 34
    y_box = H - 55

    for (role, col, droits, x) in roles:
        if x + box_w > W:
            break
        # Boite role
        d.add(Rect(x, y_box, box_w, box_h, fillColor=col, strokeColor=col, strokeWidth=0,
                   rx=4, ry=4))
        d.add(String(x + box_w/2, y_box + box_h - 12, role,
                     fontName='Helvetica-Bold', fontSize=6.5, fillColor=C_WHITE,
                     textAnchor='middle'))

        # Description droits
        lines = droits.split('+')
        for i, line in enumerate(lines):
            d.add(String(x + box_w/2, y_box - 14 - i*10, line.strip(),
                         fontName='Helvetica', fontSize=6, fillColor=C_SLATE,
                         textAnchor='middle'))

        # Fleche vers API
        mid_x = x + box_w/2
        d.add(Line(mid_x, y_box, mid_x, y_box - 8, strokeColor=col, strokeWidth=1))

    # Barre "API JWT"
    d.add(Rect(8, H - 175, W - 16, 18, fillColor=C_NAVY, strokeColor=C_NAVY,
               strokeWidth=0, rx=3, ry=3))
    d.add(String(W/2, H - 165, "API FastAPI  --  Authentification JWT  --  Verification du role a chaque requete",
                 fontName='Helvetica-Bold', fontSize=7, fillColor=C_WHITE,
                 textAnchor='middle'))

    return d


def draw_etl_pipeline():
    """
    Schema pipeline ETL sequentiel (gauche -> droite)
    """
    W, H = 480, 110
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=C_WHITE, strokeColor=C_BORDER, strokeWidth=0))

    steps = [
        ("CSV Bruts\n1,8M lignes",       C_SLATE,       12),
        ("Correction\nEncodage",          C_BLUE_DARK,   100),
        ("Normalisation\nMetier",         C_BLUE,        188),
        ("Scoring ML\nRisque + Fraude",   C_PURPLE,      276),
        ("DuckDB\ngainde_douane.db",      C_GREEN,       364),
        ("API / JSON\nStatique",          C_AMBER,       452),
    ]

    box_w = 64
    box_h = 40
    y_box = 38

    for (label, col, x) in steps:
        if x + box_w > W:
            break
        d.add(Rect(x, y_box, box_w, box_h, fillColor=col, strokeColor=col,
                   strokeWidth=0, rx=4, ry=4))
        lines = label.split('\n')
        for i, line in enumerate(lines):
            d.add(String(x + box_w/2, y_box + box_h - 14 - i*12, line,
                         fontName='Helvetica-Bold', fontSize=7, fillColor=C_WHITE,
                         textAnchor='middle'))

        # Fleche vers la suivante
        if x + box_w + 12 < W:
            ax = x + box_w + 2
            ay = y_box + box_h/2
            d.add(Line(ax, ay, ax + 10, ay, strokeColor=C_SLATE_LT, strokeWidth=1.2))
            d.add(Polygon([ax + 10, ay+4, ax + 10, ay-4, ax + 14, ay],
                          fillColor=C_SLATE_LT, strokeColor=C_SLATE_LT, strokeWidth=0))

    d.add(String(W/2, 12, "Pipeline ETL : de la source brute a la base analytique (Polars + DuckDB)",
                 fontName='Helvetica-Oblique', fontSize=7, fillColor=C_SLATE_LT,
                 textAnchor='middle'))
    return d


def draw_bar_chart(data_dict, title, width=460, height=160):
    """
    Diagramme a barres generique
    data_dict : {label: valeur}
    """
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=C_WHITE, strokeColor=C_BORDER, strokeWidth=0.3))

    labels = list(data_dict.keys())
    values = list(data_dict.values())

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 30
    bc.width = width - 70
    bc.height = height - 50

    bc.data = [values]
    bc.strokeColor = None
    bc.fillColor = C_BLUE
    bc.bars[0].fillColor = C_BLUE

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.dy = -8
    bc.categoryAxis.strokeColor = C_BORDER
    bc.categoryAxis.visibleTicks = False

    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.strokeColor = C_BORDER
    bc.valueAxis.gridStrokeColor = C_BG
    bc.valueAxis.visibleGrid = True
    bc.valueAxis.gridStrokeWidth = 0.4

    d.add(bc)
    d.add(String(width/2, height - 12, title,
                 fontName='Helvetica-Bold', fontSize=8, fillColor=C_NAVY,
                 textAnchor='middle'))
    return d


def draw_pie_chart(data_dict, title, width=300, height=220, palette=None):
    """
    Diagramme camembert generique
    """
    from reportlab.graphics.charts.piecharts import Pie

    palette = palette or [C_BLUE, C_TEAL, C_PURPLE, C_AMBER, C_GREEN, C_RED, C_SLATE]

    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=C_WHITE, strokeColor=C_BORDER, strokeWidth=0.3))

    labels = list(data_dict.keys())
    values = list(data_dict.values())

    pie = Pie()
    pie.x = 40
    pie.y = 35
    pie.width = 120
    pie.height = 120
    pie.data = values
    pie.labels = None
    pie.strokeColor = C_WHITE
    pie.strokeWidth = 1.2
    for i, col in enumerate(palette[:len(values)]):
        pie.slices[i].fillColor = col

    d.add(pie)

    # Legende manuelle
    leg_x = 175
    leg_y = height - 30
    for i, (lbl, val) in enumerate(zip(labels, values)):
        total = sum(values) or 1
        pct = val / total * 100
        col = palette[i % len(palette)]
        d.add(Rect(leg_x, leg_y - i*16, 10, 10, fillColor=col, strokeColor=col, strokeWidth=0))
        d.add(String(leg_x + 14, leg_y - i*16 + 2, f"{lbl}  ({pct:.1f}%)",
                     fontName='Helvetica', fontSize=7, fillColor=C_SLATE))

    d.add(String(width/2, height - 12, title,
                 fontName='Helvetica-Bold', fontSize=8, fillColor=C_NAVY,
                 textAnchor='middle'))
    return d


def draw_risk_pyramid():
    """
    Pyramide du scoring de risque (3 niveaux)
    """
    W, H = 320, 180
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=C_WHITE, strokeColor=C_BORDER, strokeWidth=0))

    levels = [
        # (y_base, largeur, couleur, label, nb_dossiers, score_range)
        (20,  260, C_GREEN,  "RISQUE FAIBLE",  "337 008 dossiers", "Score < 30"),
        (80,  170, C_AMBER,  "RISQUE MOYEN",   "13 507 dossiers",  "Score 30-60"),
        (140, 80,  C_RED,    "HAUT RISQUE",    "276 dossiers",     "Score >= 60"),
    ]

    for (y, w, col, label, nb, score_range) in levels:
        x_start = (W - w) / 2
        d.add(Rect(x_start, y, w, 48, fillColor=col, strokeColor=C_WHITE, strokeWidth=1.5,
                   rx=3, ry=3))
        d.add(String(W/2, y + 32, label,
                     fontName='Helvetica-Bold', fontSize=8, fillColor=C_WHITE,
                     textAnchor='middle'))
        d.add(String(W/2, y + 20, nb,
                     fontName='Helvetica-Bold', fontSize=9, fillColor=C_WHITE,
                     textAnchor='middle'))
        d.add(String(W/2, y + 8, score_range,
                     fontName='Helvetica', fontSize=7, fillColor=C_WHITE,
                     textAnchor='middle'))

    d.add(String(W/2, 6, "Pyramide de Classification des Dossiers par Niveau de Risque",
                 fontName='Helvetica-Oblique', fontSize=7, fillColor=C_SLATE_LT,
                 textAnchor='middle'))
    return d


def draw_ml_comparison():
    """
    Comparaison modeles ML (tableau visuel)
    """
    W, H = 460, 130
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=C_BG, strokeColor=C_BORDER, strokeWidth=0.4))

    models = [
        ("Moyenne Mobile", 336, 382, "Reference"),
        ("Regression Lin.", 160, 234, "Valide"),
        ("Random Forest", 115, 195, "Recommande"),
        ("Gradient Boosting", 117, 195, "Recommande"),
    ]

    cell_w = W / len(models)
    for i, (name, mae, rmse, status) in enumerate(models):
        x = i * cell_w
        is_best = "Recommande" in status
        bg = colors.HexColor('#f0fdf4') if is_best else C_WHITE
        border_col = C_GREEN if is_best else C_BORDER

        d.add(Rect(x + 4, 20, cell_w - 8, H - 30, fillColor=bg,
                   strokeColor=border_col, strokeWidth=1.5 if is_best else 0.5,
                   rx=4, ry=4))

        d.add(String(x + cell_w/2, H - 24, name,
                     fontName='Helvetica-Bold', fontSize=7.5, fillColor=C_NAVY,
                     textAnchor='middle'))
        d.add(String(x + cell_w/2, H - 48, f"MAE : {mae}",
                     fontName='Helvetica', fontSize=8, fillColor=C_SLATE,
                     textAnchor='middle'))
        d.add(String(x + cell_w/2, H - 66, f"RMSE : {rmse}",
                     fontName='Helvetica', fontSize=8, fillColor=C_SLATE,
                     textAnchor='middle'))

        col = C_GREEN if is_best else (C_AMBER if status == "Valide" else C_SLATE_LT)
        d.add(Rect(x + cell_w/2 - 30, 26, 60, 16, fillColor=col, strokeColor=col,
                   strokeWidth=0, rx=6, ry=6))
        d.add(String(x + cell_w/2, 31, status,
                     fontName='Helvetica-Bold', fontSize=7, fillColor=C_WHITE,
                     textAnchor='middle'))

    d.add(String(W/2, H - 10, "Comparaison des modeles de prevision (test sur 30 jours de dossiers)",
                 fontName='Helvetica-Oblique', fontSize=7, fillColor=C_SLATE_LT,
                 textAnchor='middle'))
    return d


# ─────────────────────────────────────────────────────────────
# CONSTRUCTION DU DOCUMENT
# ─────────────────────────────────────────────────────────────
def build_rapport(output_path):
    W_PAGE, H_PAGE = A4
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2.2*cm,
        leftMargin=2.2*cm,
        topMargin=2.8*cm,
        bottomMargin=2.2*cm,
        title="Rapport Projet GAINDE2000 / Orbus Sentinel",
        author="Orbus Infinity",
        subject="Plateforme Analytique Douaniere du Senegal"
    )
    s = build_styles()
    story = []

    # ══════════════════════════════════════════════════
    # PAGE DE COUVERTURE
    # ══════════════════════════════════════════════════
    # Fond bleu marine sur toute la page
    cover_bg = Table(
        [[Paragraph("", s['body'])]],
        colWidths=[16.5*cm], rowHeights=[24*cm]
    )
    cover_bg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_NAVY),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(cover_bg)

    # On "remonte" dans la page via une couverture a base de table
    # (technique : page de garde construite en 1 grande table avec contenu)
    story.pop()  # retire le fond vide

    cover_content = [
        [
            Paragraph("", s['body']),  # spacer
        ],
    ]

    # Construction de la couverture comme une grande table pleine page
    # Logo
    logo_cell_content = []
    logo_path = "orbus_sentinel_logo.png"
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=5*cm, height=1.2*cm)
            logo_cell_content.append(img)
        except Exception:
            logo_cell_content.append(Paragraph("ORBUS SENTINEL", ParagraphStyle(
                'logo_text', fontName='Helvetica-Bold', fontSize=14, textColor=C_BLUE)))
    else:
        logo_cell_content.append(Paragraph("ORBUS SENTINEL", ParagraphStyle(
            'logo_text', fontName='Helvetica-Bold', fontSize=14, textColor=C_BLUE)))

    logo_cell_content.append(Spacer(1, 0.5*cm))
    logo_cell_content.append(HRFlowable(width="100%", thickness=1, color=C_BLUE, spaceAfter=0))
    logo_cell_content.append(Spacer(1, 1.5*cm))
    logo_cell_content.append(Paragraph(
        "RAPPORT COMPLET DE PROJET",
        ParagraphStyle('cover_tag', fontName='Helvetica', fontSize=10,
                       textColor=colors.HexColor('#94a3b8'), leading=14)
    ))
    logo_cell_content.append(Spacer(1, 0.3*cm))
    logo_cell_content.append(Paragraph(
        "Plateforme Analytique Douaniere\ndu Senegal",
        s['cover_title']
    ))
    logo_cell_content.append(Spacer(1, 0.2*cm))
    logo_cell_content.append(Paragraph(
        "Analyse de donnees  |  Machine Learning  |  Dashboard Web  |  API Securisee",
        s['cover_sub']
    ))
    logo_cell_content.append(Spacer(1, 2*cm))

    # Bande d'info
    meta_items = [
        ("Client",      "GAINDE 2000 — Guichet Unique Douanier du Senegal"),
        ("Prestataire", "Orbus Infinity — Orbus Sentinel Division"),
        ("Perimetre",   "Importations, Exportations, Reexportations, Transit 2020-2026"),
        ("Date",        datetime.now().strftime("%d %B %Y")),
        ("Statut",      "CONFIDENTIEL"),
    ]
    for key, val in meta_items:
        logo_cell_content.append(Paragraph(
            f'<font color="#94a3b8">{key}&nbsp;&nbsp;&nbsp;</font>'
            f'<font color="#e2e8f0"><b>{val}</b></font>',
            ParagraphStyle('meta', fontName='Helvetica', fontSize=9, leading=16,
                           textColor=C_WHITE)
        ))

    cover_table = Table([[logo_cell_content]], colWidths=[16.5*cm], rowHeights=[25.5*cm])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_NAVY),
        ('LEFTPADDING', (0,0), (-1,-1), 1.5*cm),
        ('RIGHTPADDING', (0,0), (-1,-1), 1.5*cm),
        ('TOPPADDING', (0,0), (-1,-1), 2.5*cm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # SOMMAIRE
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Sommaire", s['section']))
    section_rule(story, s)

    toc_items = [
        ("1.", "Contexte et Objectifs du Projet"),
        ("2.", "Architecture Technique"),
        ("3.", "Pipeline ETL et Nettoyage des Donnees"),
        ("4.", "Analyses Statistiques Avancees"),
        ("5.", "Machine Learning et Scoring de Risque"),
        ("6.", "Backend API — FastAPI"),
        ("7.", "Interface Web — React + Vite"),
        ("8.", "Generation de Rapports PDF"),
        ("9.", "Livrables Produits"),
        ("10.", "Modifications Recentes et Etat du Projet"),
        ("11.", "Chiffres Cles du Projet"),
    ]
    toc_data = []
    for num, title in toc_items:
        toc_data.append([
            Paragraph(num, s['toc_num']),
            Paragraph(title, s['toc']),
        ])
    toc_table = Table(toc_data, colWidths=[1*cm, 15.5*cm])
    toc_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, C_BORDER),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 1. CONTEXTE ET OBJECTIFS
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 1", s['chapter_num']))
    story.append(Paragraph("Contexte et Objectifs du Projet", s['section']))
    section_rule(story, s)

    story.append(Paragraph(
        "GAINDE 2000 administre le systeme ORBUS, le guichet unique de "
        "teledeclaration douaniere du Senegal. Ce systeme enregistre l'ensemble des "
        "flux d'importation, d'exportation, de reexportation et de transit de marchandises. "
        "Les donnees se structurent en trois niveaux logiques complementaires.",
        s['body']
    ))

    callout_box(story,
        "La mission confiee a Orbus Infinity consiste a concevoir et deployer une plateforme analytique "
        "securisee, connectee aux sources de donnees douanieres en temps reel, permettant a la Direction "
        "Generale des Douanes de piloter l'activite, detecter les fraudes et produire des rapports decisionnels.",
        s, bg=colors.HexColor('#eff6ff'), border=C_BLUE_DARK
    )

    story.append(Paragraph("Trois niveaux de donnees sources :", s['subsection']))
    std_table(story,
        ["Niveau", "Table Source", "Description", "Relation"],
        [
            ["Administratif", "DOSSIERTPS", "Dossier douanier : mode de transport, banque, importateur, date", "1 dossier = 1 entite"],
            ["Transactionnel", "FACTURE",    "Facture commerciale : devise, incoterms, valeur FOB, assurance",  "1 dossier = 1 facture"],
            ["Physique",       "CONTENIR",   "Articles declares : code SH, designation, quantite, poids, valeur", "1 facture = N articles"],
        ],
        s, col_widths=[2.5*cm, 3.5*cm, 7.5*cm, 3*cm]
    )

    story.append(Paragraph("Objectifs strategiques :", s['subsection']))
    for item in [
        "<b>Nettoyage et Consolidation</b> : fusionner plus de 1,8 million de lignes de donnees reparties sur plusieurs fichiers volumineux (2020 a 2026), corriger les encodages corrompus, normaliser les variables textuelles et eliminer les doublons.",
        "<b>Analyse Metier (EDA) et KPIs</b> : degager des statistiques descriptives sur les flux financiers, les pays d'origine, les banques partenaires et les assurances.",
        "<b>Analyses Statistiques Avancees</b> : identifier les correlations physiques et financieres, valider les dependances de variables (Chi-Deux), modeliser la saisonnalite (autocorrelation) et detecter les transactions exceptionnellement hautes.",
        "<b>Modelisation Machine Learning</b> : mettre au point un modele statistique robuste de detection de sous-evaluation douaniere (fraude fiscale) et structurer les series temporelles pour le forecasting des flux logistiques.",
        "<b>Dashboard et API securisee</b> : exposer les resultats via une interface web moderne multi-onglets avec authentification JWT et controle d'acces par role.",
    ]:
        story.append(Paragraph(f"- {item}", s['bullet']))

    story.append(Spacer(1, 8))

    # Volume dossiers : camembert
    story.append(Paragraph("Repartition des dossiers par type d'operation (2020-2026)", s['subsection']))
    pie = draw_pie_chart(
        {
            "Importation (72,3%)": 253780,
            "Exportation (21,5%)": 75507,
            "Reexportation (3,6%)": 12732,
            "Transit (2,5%)": 8772,
        },
        "Repartition par type d'operation — 350 791 dossiers totaux",
        width=380, height=200,
        palette=[C_BLUE, C_TEAL, C_AMBER, C_PURPLE]
    )
    story.append(pie)
    story.append(Paragraph(
        "Figure 1 — Repartition des 350 791 dossiers traites de 2020 a 2026 par type d'operation douaniere.",
        s['caption']
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 2. ARCHITECTURE TECHNIQUE
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 2", s['chapter_num']))
    story.append(Paragraph("Architecture Technique", s['section']))
    section_rule(story, s)

    story.append(Paragraph(
        "Face au volume de donnees (fichiers CSV cumulant pres de 1 Go de texte brut), "
        "le projet a ete concu sur une architecture haute performance en couches independantes. "
        "Chaque couche peut evoluer sans impacter les autres, garantissant la maintenabilite a long terme.",
        s['body']
    ))

    story.append(Spacer(1, 6))
    arch = draw_architecture_schema()
    story.append(arch)
    story.append(Paragraph(
        "Figure 2 — Architecture en couches de la plateforme Orbus Sentinel. "
        "Les donnees remontent des sources brutes jusqu'a l'interface web via le pipeline ETL et l'API.",
        s['caption']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Stack technologique :", s['subsection']))
    std_table(story,
        ["Couche", "Technologie", "Role"],
        [
            ["ETL / Ingestion",    "Polars (Rust), DuckDB",                     "Traitement haute performance, 1,8M lignes en quelques secondes"],
            ["Stockage analytique","DuckDB gainde_douane.db",                    "Requetes SQL vectorisees, jointures massives"],
            ["Authentification",   "SQLite users.db + bcrypt + JWT (HS256)",     "Stockage utilisateurs, hachage mdp, tokens 24h"],
            ["Machine Learning",   "Scikit-Learn (Isolation Forest, K-Means)",   "Detection anomalies, segmentation importateurs"],
            ["Prevision",          "XGBoost, Random Forest, Gradient Boosting",  "Forecasting flux logistiques"],
            ["Analyse",            "Pandas, Scipy, Seaborn",                     "EDA, tests statistiques, visualisations"],
            ["Backend",            "Python 3.12, FastAPI, Uvicorn ASGI",         "27 routes REST, middleware CORS, responses JSON"],
            ["Frontend",           "React 19, Vite 6, ECharts, Lucide Icons",    "SPA moderne, 10 onglets, thème clair/sombre"],
        ],
        s, col_widths=[3.5*cm, 5*cm, 8*cm]
    )

    story.append(Paragraph("Bases de donnees :", s['subsection']))
    std_table(story,
        ["Base", "Technologie", "Contenu", "Acces"],
        [
            ["SQL Server MSSQL", "pymssql",  "Donnees temps reel (DOSSIERTPS, FACTURE, CONTENIR)", "192.168.2.138 — DataAnalyse"],
            ["DuckDB analytique", "duckdb",  "Historique 2020-2026 nettoye et enrichi",             "Lecture directe fichier .db"],
            ["SQLite utilisateurs","sqlite3", "Comptes, hash mdp, audit logs, dossiers marques",    "Thread-safe via contextmanager"],
            ["JSON statique",     "Fichiers", "Cache dashboard_data.json, fallback si MSSQL offline","Lecture directe, 118 Ko"],
        ],
        s, col_widths=[3.5*cm, 3*cm, 6.5*cm, 3.5*cm]
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 3. PIPELINE ETL
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 3", s['chapter_num']))
    story.append(Paragraph("Pipeline ETL et Nettoyage des Donnees", s['section']))
    section_rule(story, s)

    etl = draw_etl_pipeline()
    story.append(etl)
    story.append(Paragraph(
        "Figure 3 — Pipeline ETL : de l'ingestion des fichiers CSV bruts jusqu'au stockage analytique et au cache statique.",
        s['caption']
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Problemes resolus :", s['subsection']))
    std_table(story,
        ["Probleme identifie", "Cause", "Solution appliquee"],
        [
            ["Fichiers CSV sans en-tetes", "Format GAINDE non documente", "Reconstruction manuelle des 20+ colonnes, documentee dans DICTIONNAIRE_DONNEES.md"],
            ["Encodage corrompu (SÃ©nÃ©gal)", "Fichiers generes en latin-1 lus en utf-8", "Lecture utf-8-sig + html.unescape sur toutes les colonnes textuelles"],
            ["9 variantes du nom Senegal", "Encodages multiples accumules", "Normalisation geographique unifiee avec mapping exhaustif"],
            ["Codes pays non standards", "Saisies libres operateurs", "Mapping vers nomenclature ISO 3166"],
            ["Devises mixtes (EURO -> EUR)", "Saisies heterogenes", "Standardisation ISO 4217, passage en majuscule"],
            ["Modes transport heterogenes", "Saisies libres (10+ variantes)", "Reduction en 5 categories : Mer, Air, Route, Fer, Autres"],
            ["Codes operation (I/E/R/S)", "Codes internes GAINDE", "Traduction : Importation, Exportation, Reexportation, Transit"],
            ["Valeurs numériques avec virgule", "Format local (1 234,56)", "Remplacement virgule -> point avant conversion float"],
            ["Doublons exacts", "Soumissions multiples", "Deduplication sur cle composite NUMERODOSSIERTPS"],
        ],
        s, col_widths=[4.5*cm, 4*cm, 8*cm]
    )

    story.append(Paragraph("Volume final traite :", s['subsection']))
    kpi_band(story, [
        ("Importations", "253 780", colors.HexColor('#dbeafe'), C_BLUE_DARK),
        ("Exportations",  "75 507", colors.HexColor('#d1fae5'), C_GREEN),
        ("Reexportations","12 732", colors.HexColor('#fef3c7'), C_AMBER),
        ("Transits",       "8 772", colors.HexColor('#f3e8ff'), C_PURPLE),
    ])

    callout_box(story,
        "Valeur financiere totale analysee : environ 35 Trillions de Francs CFA  |  "
        "dont 26,99 Trillions CFA pour les importations et 6,04 Trillions CFA pour les exportations.",
        s, bg=colors.HexColor('#f0fdf4'), border=C_GREEN
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 4. ANALYSES STATISTIQUES
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 4", s['chapter_num']))
    story.append(Paragraph("Analyses Statistiques Avancees", s['section']))
    section_rule(story, s)

    story.append(Paragraph("Matrice de Correlation de Spearman", s['subsection']))
    story.append(Paragraph(
        "La correlation de Spearman est utilisee car elle est robuste aux valeurs extremes "
        "(outliers financiers) et ne suppose pas une distribution normale des donnees. "
        "Elle mesure la dependance monotone entre deux variables.",
        s['body']
    ))
    std_table(story,
        ["Variables", "Correlation Spearman", "Interpretation"],
        [
            ["Poids Net <-> Poids Brut",     "0,9965  (Tres forte)", "Coherence physique absolue — les donnees sont fiables"],
            ["Valeur CFA <-> Valeur FOB",     "0,9465  (Tres forte)", "Coherence financiere validee — FOB bien declare"],
            ["Poids Net <-> Valeur CFA",      "0,6148  (Forte)",      "Lien entre masse physique et valeur commerciale"],
            ["Quantite <-> Valeur CFA",       "0,4086  (Moderee)",    "Les gros volumes ne sont pas forcement les plus couteux (valeur unitaire variable)"],
            ["Valeur Devise <-> Valeur CFA",  "0,3577  (Moderee)",    "Coherence generale des taux de change utilises"],
        ],
        s, col_widths=[5.5*cm, 4*cm, 7*cm]
    )

    story.append(Paragraph("Analyse de Saisonnalite (Autocorrelation)", s['subsection']))
    story.append(Paragraph(
        "L'autocorrelation mesure la dependance entre le nombre de dossiers d'un jour donne "
        "et les valeurs des jours precedents. Un pic a Lag 7 confirme un cycle hebdomadaire strict.",
        s['body']
    ))
    bar = draw_bar_chart(
        {f"J-{i}": v for i, v in zip(
            [1,2,3,4,5,6,7,8,9,10,11,12,13,14],
            [0.330, -0.287, -0.369, -0.367, -0.280, 0.314, 0.854, 0.304, -0.305, -0.382, -0.373, -0.291, 0.312, 0.825]
        )},
        "Autocorrelation du nombre de dossiers par lag (en jours)",
        width=460, height=160
    )
    story.append(bar)
    story.append(Paragraph(
        "Figure 4 — Autocorrelation temporelle. Pic a Lag 7 = 0,854 (cycle hebdomadaire fort). Pic a Lag 14 = 0,825 (cycle bi-hebdomadaire confirme).",
        s['caption']
    ))

    story.append(Spacer(1, 6))
    callout_box(story,
        "Conclusion operationnelle : L'activite douaniere suit un cycle rigide de 7 jours. "
        "Creux en aout, pics en novembre et decembre. Ces donnees permettent de planifier les "
        "ressources humaines et logistiques de facon proactive.",
        s, bg=C_BLUE_LIGHT, border=C_BLUE
    )

    story.append(Paragraph("Analyse de Concentration Pareto (80/20)", s['subsection']))
    std_table(story,
        ["Dimension", "Top 20%", "Valeur couverte", "Conclusion"],
        [
            ["Importateurs", "20% des declarants", "98,54% de la valeur totale CFA", "Concentration extreme — 4 segments K-Means identifies"],
            ["Codes tarifaires", "20% des codes SH", "97,50% du montant global", "Ciblage prioritaire des codes a fort enjeu fiscal"],
        ],
        s, col_widths=[3.5*cm, 3.5*cm, 5*cm, 4.5*cm]
    )

    story.append(Paragraph("Test Chi-Deux — Dependances entre Variables Categorielles", s['subsection']))
    std_table(story,
        ["Couple de variables", "P-Value", "Conclusion"],
        [
            ["Mode de Transport <-> Devise de Facturation", "0,0000 (p < 0,001)", "Dependance statistiquement significative : le mode de transport influence le choix de la devise"],
        ],
        s, col_widths=[6*cm, 4*cm, 6.5*cm]
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 5. MACHINE LEARNING
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 5", s['chapter_num']))
    story.append(Paragraph("Machine Learning et Scoring de Risque", s['section']))
    section_rule(story, s)

    story.append(Paragraph("Segmentation des Importateurs — K-Means Clustering", s['subsection']))
    story.append(Paragraph(
        "Quatre groupes d'importateurs ont ete identifies par l'algorithme K-Means "
        "sur la base de la frequence d'importation, du volume physique et de la valeur "
        "declaree en CFA. Cette segmentation permet un ciblage controle adapte a chaque profil.",
        s['body']
    ))
    std_table(story,
        ["Cluster", "Taille", "Frequence Moy.", "Valeur Moy./an", "Profil"],
        [
            ["Petits occasionnels",    "12 175 comptes", "4,1 dossiers/an",    "432 M CFA",     "Importateurs ponctuels, faible risque systemique"],
            ["Reguliers",              "943 comptes",    "161,2 dossiers/an",  "13,4 Mds CFA",  "PME actives, profil stable"],
            ["Grands comptes",         "1 compte",       "674 dossiers/an",    "151,4 Mds CFA", "Acteur dominant, surveillance renforcee"],
            ["Strategiques",           "52 comptes",     "1 862 dossiers/an",  "302 Mds CFA",   "Grands groupes industriels et agro-alimentaires"],
        ],
        s, col_widths=[3.5*cm, 2.5*cm, 3*cm, 3*cm, 4.5*cm]
    )

    story.append(Spacer(1, 8))

    story.append(Paragraph("Score de Risque Douanier (0 a 100)", s['subsection']))
    story.append(Paragraph(
        "Un score de risque multicritere a ete construit pour chaque dossier douanier. "
        "Il combine des signaux statistiques et des regles metier etablies par les inspecteurs.",
        s['body']
    ))
    std_table(story,
        ["Critere de risque", "Points ajoutes", "Justification metier"],
        [
            ["Sous-evaluation detectee (Z-Score)",           "+40 pts", "Ecart significatif par rapport au prix de reference du code SH"],
            ["Valeur dans le top 10% du code SH",            "+20 pts", "Transaction anormalement elevee pour la categorie"],
            ["Nouveau declarant (< 3 dossiers historiques)", "+15 pts", "Absence d'historique de conformite"],
            ["Pays d'origine a risque historique eleve",     "+15 pts", "Provenance associee a des precedents de fraude"],
            ["Quantite dans le top 5% du code SH",           "+10 pts", "Volume physique inhabituel pour la categorie"],
        ],
        s, col_widths=[6*cm, 2.5*cm, 8*cm]
    )

    story.append(Spacer(1, 10))
    pyr = draw_risk_pyramid()
    story.append(pyr)
    story.append(Paragraph(
        "Figure 5 — Pyramide de classification des dossiers par niveau de risque douanier.",
        s['caption']
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Detection de Fraude par Double Methode", s['subsection']))
    std_table(story,
        ["Methode", "Factures signalees", "Principe", "Niveau d'alerte"],
        [
            ["Z-Score Robuste",   "1 255",   "Ecart > 3 sigma par rapport a la mediane du code SH",  "Eleve — Priorite 2"],
            ["Isolation Forest",  "11 448",  "Isolation des points outliers multidimensionnels (1% contamination)", "Eleve — Priorite 2"],
            ["Intersection (double ciblage)", "132", "Factures signalees par les deux methodes simultanement", "CRITIQUE — Priorite 1"],
        ],
        s, col_widths=[3.5*cm, 3*cm, 6.5*cm, 3.5*cm]
    )

    callout_box(story,
        "Les 132 factures identifiees simultanement par le Z-Score et l'Isolation Forest "
        "representent la priorite absolue de controle physique. "
        "Tout dossier dans cette zone de convergence doit etre bloque automatiquement.",
        s, bg=C_RED_LT, border=C_RED
    )

    story.append(PageBreak())

    story.append(Paragraph("Prevision des Flux Logistiques (Forecasting)", s['subsection']))
    story.append(Paragraph(
        "Quatre modeles de serie temporelle ont ete evalues pour predire le nombre de "
        "dossiers douaniers quotidiens sur un jeu de test de 30 jours.",
        s['body']
    ))

    ml_d = draw_ml_comparison()
    story.append(ml_d)
    story.append(Paragraph(
        "Figure 6 — Comparaison des modeles de prevision. Random Forest et Gradient Boosting "
        "obtiennent les meilleures performances (MAE ~115-117 dossiers/jour).",
        s['caption']
    ))
    story.append(Spacer(1, 8))
    std_table(story,
        ["Modele", "MAE (dossiers)", "RMSE", "MAPE (%)", "Statut"],
        [
            ["Moyenne Mobile (Baseline)", "336", "382", "1 479 %",  "Reference"],
            ["Regression Lineaire",       "160", "234", "168 %",    "Valide"],
            ["Random Forest",             "115", "195", "141 %",    "Recommande (MAE)"],
            ["Gradient Boosting",         "117", "195", "152 %",    "Recommande (RMSE)"],
        ],
        s, col_widths=[5.5*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm]
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 6. BACKEND API
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 6", s['chapter_num']))
    story.append(Paragraph("Backend API — FastAPI", s['section']))
    section_rule(story, s)

    story.append(Paragraph(
        "Le backend est developpe en Python 3.12 avec FastAPI, expose sur Uvicorn ASGI "
        "(port 8000). Il centralise l'authentification, la logique metier, la liaison avec "
        "les bases de donnees et la generation de rapports PDF.",
        s['body']
    ))

    story.append(Paragraph("Systeme d'authentification et de roles (RBAC)", s['subsection']))
    rbac = draw_rbac_schema()
    story.append(rbac)
    story.append(Paragraph(
        "Figure 7 — Schema RBAC : chaque role utilisateur dispose d'un acces filtre "
        "via l'API FastAPI avec verification JWT a chaque requete.",
        s['caption']
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Les 7 roles utilisateurs :", s['subsection']))
    std_table(story,
        ["Role", "Acces autorise", "Profil utilisateur type"],
        [
            ["admin",        "Acces complet : gestion utilisateurs, audit, toutes les donnees", "Administrateur systeme"],
            ["direction",    "Dashboard executif, alertes budget, generation PDF, KPIs globaux", "Directeur Regional des Douanes"],
            ["inspecteur",   "Simulation de risque, marquage de dossiers, zone ciblage", "Inspecteur de bureau de douane"],
            ["transitaire",  "Dossiers de son propre bureau douane uniquement", "Agent transitaire (ex : CargoLink)"],
            ["partenaire",   "Score de fiabilite des importateurs (banques, assurances)", "SGBS, AXA, partenaires financiers"],
            ["statisticien", "Export CSV anonymise, analyses agregees", "Chercheur, data analyst externe"],
            ["journaliste",  "Vue publique limitee, donnees agregees non sensibles", "Presse, medias"],
        ],
        s, col_widths=[2.5*cm, 8*cm, 6*cm]
    )

    story.append(Paragraph("Les 27 routes API :", s['subsection']))
    std_table(story,
        ["Endpoint", "Methode", "Role requis", "Description"],
        [
            ["/api/auth/login",                       "POST", "Public",       "Connexion JWT — retourne token + role + bureau"],
            ["/api/dashboard-data",                   "GET",  "Tous",         "KPIs executifs globaux, donnees graphiques"],
            ["/api/filter-options",                   "GET",  "Tous",         "Options de filtres (annees, modes transport)"],
            ["/api/dossiers-preview",                 "GET",  "Tous",         "Preview des dossiers pagines, avec filtres"],
            ["/api/business-prospects",               "GET",  "Tous",         "Prospects business et opportunites commerciales"],
            ["/api/inspecteur/simulate-risk",         "POST", "inspecteur",   "Calcule le score de risque en temps reel"],
            ["/api/inspecteur/mark-inspection",       "POST", "inspecteur",   "Marque un dossier pour controle physique"],
            ["/api/inspecteur/marked-dossiers",       "GET",  "inspecteur",   "Liste les dossiers marques pour inspection"],
            ["/api/direction/simulate-weights",       "POST", "direction",    "Simule l'impact d'un changement de poids de risque"],
            ["/api/direction/budget-alerts",          "GET",  "direction",    "Alertes de depassement budgetaire"],
            ["/api/direction/generate-pdf-report",    "GET",  "direction",    "Generation PDF dynamique (4 types de rapports)"],
            ["/api/partenaire/importer-reliability",  "GET",  "partenaire",   "Score de fiabilite des importateurs"],
            ["/api/statistician/export-csv",          "POST", "statisticien", "Export CSV anonymise selon criteres"],
            ["/api/statistician/download-csv/{file}", "GET",  "statisticien", "Telechargement du fichier CSV genere"],
            ["/api/admin/audit-logs",                 "GET",  "admin",        "Consultation des logs de securite"],
            ["/api/admin/create-user",                "POST", "admin",        "Creation d'un nouveau compte utilisateur"],
            ["/api/admin/update-password",            "POST", "admin",        "Modification du mot de passe d'un utilisateur"],
            ["/api/admin/users",                      "GET",  "admin",        "Liste complete des comptes enregistres"],
            ["/api/assistant/chat",                   "POST", "Tous",         "Chatbot IA : langage naturel -> SQL -> resultat"],
            ["/api/assistant/download-csv/{file}",   "GET",  "Tous",         "Telechargement export chatbot"],
            ["/api/log-error",                        "POST", "Public",       "Collecte des erreurs frontend (JS error logging)"],
        ],
        s, col_widths=[5.5*cm, 1.8*cm, 2.5*cm, 6.7*cm]
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 7. FRONTEND WEB
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 7", s['chapter_num']))
    story.append(Paragraph("Interface Web — React + Vite", s['section']))
    section_rule(story, s)

    story.append(Paragraph(
        "L'interface utilisateur est une Single Page Application (SPA) construite avec "
        "React 19 et Vite 6. Elle communique avec le backend via un proxy Vite en "
        "developpement et un build statique en production. La gestion du theme "
        "(clair/sombre) est persistee dans le localStorage du navigateur.",
        s['body']
    ))

    story.append(Paragraph("Les 10 onglets du dashboard :", s['subsection']))
    std_table(story,
        ["Onglet", "Composant", "Taille", "Contenu principal"],
        [
            ["Dashboard Executif", "DashboardTab.jsx",  "46 Ko", "KPIs globaux, carte mondiale, diagramme Sankey, heatmap hebdomadaire, tendances mensuelles"],
            ["Imports",            "ImportsTab.jsx",    "21 Ko", "Analyse des flux d'importation, top pays d'origine, top produits, evolution annuelle"],
            ["Exports",            "ExportsTab.jsx",    "21 Ko", "Flux d'exportation, repartition geographique, part de valeur"],
            ["Risques",            "RisksTab.jsx",      "66 Ko", "Score de risque, anomalies Isolation Forest, heatmap de risque, dossiers cibles"],
            ["Logistique",         "LogisticsTab.jsx",  "32 Ko", "Modes de transport, delais, performance logistique par corridor"],
            ["Business",           "BusinessTab.jsx",   "8,6 Ko","Prospects business, opportunites commerciales, scoring partenaires"],
            ["Paiements",          "PaymentTab.jsx",    "8,4 Ko","Devises utilisees, banques domiciliataires, assureurs"],
            ["Finance",            "FinanceTab.jsx",    "26 Ko", "Valeurs CFA et FOB, alertes budget, taux de change, ecarts"],
            ["Cybersecurite",      "CybersecurityTab.jsx","9,7 Ko","Logs d'audit, tentatives d'intrusion, historique des connexions"],
            ["Admin Utilisateurs", "AdminUsersTab.jsx", "20 Ko", "Gestion des comptes, creation/modification, roles et bureaux"],
        ],
        s, col_widths=[3*cm, 4*cm, 1.5*cm, 8*cm]
    )

    story.append(Paragraph("Fonctionnalites avancees :", s['subsection']))
    for item in [
        "<b>Chatbot IA (Chatbot.jsx)</b> : Interface conversationnelle permettant a l'utilisateur de formuler des questions en langage naturel. Le backend les traduit en requetes SQL executees sur MSSQL ou DuckDB et retourne le resultat.",
        "<b>Modal Timeline Dossier (DossierTimelineModal.jsx)</b> : Visualisation de l'historique complet d'un dossier douanier avec chronologie des etapes de traitement.",
        "<b>Compteurs animes (AnimatedCounter.jsx)</b> : Animations des KPIs au chargement de la page pour un effet visuel premium.",
        "<b>Generation PDF multi-rapports</b> : 4 types de rapports generables directement depuis l'interface (executif, fraude, logistique, partenaires).",
        "<b>Carte monde interactive</b> : Visualisation ECharts des pays d'origine des importations via world.json (GeoJSON).",
        "<b>Proxy Vite</b> : En mode developpement, toutes les requetes /api sont automatiquement redirigees vers le backend FastAPI sur le port 8000.",
    ]:
        story.append(Paragraph(f"- {item}", s['bullet']))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 8. GENERATION DE RAPPORTS PDF
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 8", s['chapter_num']))
    story.append(Paragraph("Generation de Rapports PDF Dynamiques", s['section']))
    section_rule(story, s)

    story.append(Paragraph(
        "Un module de generation PDF dedie (pdf_generator.py, 1 122 lignes) produit "
        "des rapports professionnels a partir des donnees du dashboard en temps reel. "
        "Les rapports incluent des graphiques matplotlib, des tableaux de donnees et "
        "une mise en page institutionnelle avec en-tete, pied de page et logo.",
        s['body']
    ))
    std_table(story,
        ["Type de rapport", "Contenu principal", "Destinataire"],
        [
            ["Rapport Executif",     "KPIs globaux, repartition operations, tendances mensuelles, flux logistiques", "Direction Generale"],
            ["Rapport Fraude",       "Algorithmes de ciblage (Z-Score + Isolation Forest), dossiers cibles, directives inspecteurs", "Inspecteurs, Chefs de bureau"],
            ["Rapport Logistique",   "Flux par mode de transport, delais, stress-test resilience, saisonnalite", "Service logistique"],
            ["Rapport Partenaires",  "Fiabilite importateurs par cluster, performance banques et assurances", "Direction commerciale, partenaires"],
        ],
        s, col_widths=[3.5*cm, 9*cm, 4*cm]
    )

    callout_box(story,
        "Chaque rapport peut etre genere avec ou sans anonymisation des noms d'importateurs, "
        "selon le role de l'utilisateur connecte. L'option d'anonymisation est automatiquement "
        "activee pour les roles 'statisticien' et 'journaliste'.",
        s, bg=C_AMBER_LT, border=C_AMBER
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 9. LIVRABLES
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 9", s['chapter_num']))
    story.append(Paragraph("Livrables Produits", s['section']))
    section_rule(story, s)

    story.append(Paragraph("Fichiers de code source :", s['subsection']))
    std_table(story,
        ["Fichier", "Type", "Taille", "Description"],
        [
            ["app.py",                        "Python",        "1 940 lignes", "API backend complète : routes, auth, ML, traducteur SQL"],
            ["pdf_generator.py",              "Python",        "1 122 lignes", "Generateur de rapports PDF institutionnels"],
            ["frontend/src/App.jsx",          "React/JSX",     "848 lignes",   "Application principale : routing, theme, layout"],
            ["frontend/src/components/RisksTab.jsx","React/JSX","1 381 lignes","Onglet risques : scoring, ciblage, heatmap"],
            ["frontend/src/components/DashboardTab.jsx","React","1 035 lignes","Dashboard executif : KPIs, graphiques, carte"],
            ["frontend/src/index.css",        "CSS",           "1 714 lignes", "Systeme de design complet (variables, composants, themes)"],
            ["scripts/etl_pipeline.py",       "Python ETL",    "337 lignes",   "Pipeline de nettoyage et normalisation des donnees"],
            ["scripts/etl_pipeline_duckdb.py","Python ETL",    "376 lignes",   "Pipeline optimise avec stockage DuckDB"],
            ["scripts/run_advanced_analysis.py","Python ML",   "783 lignes",   "Analyses statistiques avancees, ML, forecasting"],
            ["scripts/generate_excel_dashboard.py","Python",   "416 lignes",   "Generation du dashboard Excel multi-onglets"],
            ["scripts/init_auth_db.py",       "Python",        "89 lignes",    "Initialisation de la base de donnees utilisateurs"],
        ],
        s, col_widths=[5.5*cm, 2.5*cm, 2.5*cm, 6*cm]
    )

    story.append(Paragraph("Donnees et modeles :", s['subsection']))
    std_table(story,
        ["Fichier", "Description"],
        [
            ["data/models/iforest_model.pkl",       "Modele Isolation Forest entraine (569 Ko) — detection d'anomalies en temps reel"],
            ["data/models/kmeans_model.pkl",         "Modele K-Means (6,8 Ko) — segmentation des importateurs en 4 clusters"],
            ["data/models/scaler_kmeans.pkl",        "Scaler de normalisation (1 Ko) — preprocessing avant K-Means"],
            ["data/static/dashboard_data.json",      "Cache statique dashboard (118 Ko) — fallback si MSSQL offline"],
            ["data/static/dossiers_preview.json",    "Cache preview dossiers (33 Ko) — 200 dernieres lignes"],
            ["data/static/business_prospects.json",  "Prospects business (49 Ko) — donnees Business tab"],
            ["export_dossiers_2022_2026.csv",         "Export complet 2022-2026 (26 Mo) — donnees brutes preparees"],
        ],
        s, col_widths=[5.5*cm, 11*cm]
    )

    story.append(Paragraph("Documentation :", s['subsection']))
    std_table(story,
        ["Document", "Description"],
        [
            ["docs/DOCUMENTATION.md",             "Documentation technique complete du projet (analyse, ETL, ML, livrables)"],
            ["docs/DICTIONNAIRE_DONNEES.md",       "Dictionnaire des colonnes des 3 tables (DOSSIERTPS, FACTURE, CONTENIR)"],
            ["docs/FICHE_EXPLICATIVE.md",          "Fiche d'explication des fichiers Articles (31 523 enregistrements)"],
            ["docs/data_engineering_specifications.md","Specifications data engineering detaillees"],
            ["guide_utilisation_sentinel.pdf",     "Manuel utilisateur de la plateforme Orbus Sentinel"],
            ["gainde_douane_dashboard.xlsx",       "Dashboard Excel statique multi-onglets (530 Ko)"],
            ["reports/advanced_analysis_report.md","Rapport d'analyse statistique avancee avec matrices et tableaux"],
        ],
        s, col_widths=[6*cm, 10.5*cm]
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 10. MODIFICATIONS RECENTES
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 10", s['chapter_num']))
    story.append(Paragraph("Modifications Recentes et Etat du Projet", s['section']))
    section_rule(story, s)

    story.append(Paragraph("Commit initial — 6 juillet 2026", s['subsection']))
    story.append(Paragraph(
        "Le commit de reference (hash 29a80c5) portant le message "
        "feat: Orbus Sentinel exploitation dashboard and dynamic report generator "
        "a introduit 43 478 insertions de code reparties sur 107 fichiers.",
        s['body']
    ))

    story.append(Paragraph("Modifications post-commit (non encore versionnees) :", s['subsection']))
    std_table(story,
        ["Fichier modifie", "Insertions (+)", "Suppressions (-)", "Nature des changements"],
        [
            ["app.py",                               "+919",  "-519", "Nouvelles routes API, chatbot SQL, wrapper MSSQL ameliore, route PDF"],
            ["frontend/index.html",                  "+25",   "0",    "Metadonnees SEO, error logging JavaScript automatique"],
            ["frontend/src/App.jsx",                 "+70",   "-14",  "Nouveaux onglets, gestion theme, rechargement de donnees"],
            ["frontend/src/components/RisksTab.jsx", "+200",  "-200", "Refonte partielle : nouveaux graphiques, scoring mis a jour"],
            ["frontend/src/components/FinanceTab.jsx","+144", "-144", "Refonte alertes budget, graphiques valeurs CFA/FOB"],
            ["frontend/src/components/DashboardTab.jsx","+22","-14",  "Ajustements graphiques, nouveaux KPIs"],
            ["frontend/src/components/BusinessTab.jsx","0",   "-1",   "Correction mineure"],
        ],
        s, col_widths=[6.5*cm, 2.5*cm, 2.5*cm, 5*cm]
    )

    story.append(Paragraph("Etat des serveurs :", s['subsection']))
    std_table(story,
        ["Service", "Commande de demarrage", "URL", "Statut"],
        [
            ["Backend FastAPI", ".venv\\Scripts\\uvicorn.exe app:app --host 127.0.0.1 --port 8000 --reload", "http://127.0.0.1:8000", "Operationnel"],
            ["Frontend Vite",   "npm.cmd run dev  (dans frontend/)", "http://localhost:5173",  "Operationnel"],
            ["MSSQL Server",    "192.168.2.138 — base APPLICATIONS",  "Port 1433",             "Intermittent (timeout)"],
        ],
        s, col_widths=[2.5*cm, 6.5*cm, 4*cm, 2.5*cm]
    )

    callout_box(story,
        "Note technique : Des erreurs de timeout MSSQL sont observees (DB-Lib error 20047 — "
        "DBPROCESS dead or not enabled). Le systeme bascule automatiquement sur le cache "
        "JSON statique (dashboard_data.json) lorsque la connexion MSSQL echoue, "
        "assurant la continuite de service.",
        s, bg=C_AMBER_LT, border=C_AMBER
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════
    # 11. CHIFFRES CLES
    # ══════════════════════════════════════════════════
    story.append(Paragraph("Chapitre 11", s['chapter_num']))
    story.append(Paragraph("Chiffres Cles du Projet", s['section']))
    section_rule(story, s)

    story.append(Paragraph("Metriques du code source :", s['subsection']))
    kpi_band(story, [
        ("Lignes Python backend", "~7 800", colors.HexColor('#dbeafe'), C_BLUE_DARK),
        ("Lignes React/JSX", "~12 000", colors.HexColor('#f3e8ff'), C_PURPLE),
        ("Lignes CSS", "~1 700", colors.HexColor('#d1fae5'), C_GREEN),
        ("Fichiers crees", "107", colors.HexColor('#fef3c7'), C_AMBER),
    ])
    kpi_band(story, [
        ("Routes API", "27", colors.HexColor('#dbeafe'), C_BLUE_DARK),
        ("Composants React", "14", colors.HexColor('#f3e8ff'), C_PURPLE),
        ("Onglets dashboard", "10", colors.HexColor('#d1fae5'), C_GREEN),
        ("Modeles ML", "3", colors.HexColor('#fef3c7'), C_AMBER),
    ])

    story.append(Paragraph("Metriques des donnees :", s['subsection']))
    kpi_band(story, [
        ("Dossiers traites", "350 791", colors.HexColor('#dbeafe'), C_BLUE_DARK),
        ("Valeur analysee", "~35 Trdn CFA", colors.HexColor('#d1fae5'), C_GREEN),
        ("Factures anomalies", "11 448", colors.HexColor('#fee2e2'), C_RED),
        ("Dossiers haut risque", "276", C_RED_LT, C_RED),
    ])

    story.append(Spacer(1, 10))

    # Graphique final : repartition valeur par type
    bar2 = draw_bar_chart(
        {
            "Importations\n26,99 Trdn": 26990,
            "Exportations\n6,04 Trdn": 6040,
            "Reexportations\n652 Mds": 652,
            "Transit\n108 Mds": 108,
        },
        "Valeur financiere totale par type d'operation (en milliards CFA)",
        width=460, height=170
    )
    story.append(bar2)
    story.append(Paragraph(
        "Figure 8 — Repartition de la valeur financiere totale (~35 Trillions CFA) "
        "par type d'operation douaniere. Les importations representent 76,4% de la valeur globale.",
        s['caption']
    ))

    story.append(Spacer(1, 12))
    HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=10)

    story.append(Paragraph(
        f"Rapport genere le {datetime.now().strftime('%d %B %Y a %H:%M')} par la plateforme Orbus Sentinel.",
        ParagraphStyle('footer_note', fontName='Helvetica-Oblique', fontSize=8,
                       textColor=C_SLATE_LT, leading=11, alignment=TA_CENTER)
    ))

    # ── COMPILATION ──
    doc.build(story, canvasmaker=OrbusCanvas)
    print(f"[OK] PDF genere : {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────
# POINT D'ENTREE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = os.path.join(PROJECT_ROOT, "reports", "rapport_projet_gainde2000.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_rapport(out)
