import numpy as np
from scipy.interpolate import CubicSpline , interp1d
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidget, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt


VARIABLE_LABELS = {
    "GNSS_time"    : "Time",
    "GNSS_lat"     : "Latitude",
    "GNSS_lon"     : "Longitude",
    "GNSS_alt"     : "GNSS Altitude",
    "QNS_alt"      : "Pressure Altitude",
    "GNSS_speed"   : "GNSS Speed",
    "GNSS_head"    : "GNSS Heading",
    "GNSS_velD"    : "GNSS Vario",
    "compass_head" : "Compass Heading",
    "pitch"        : "Pitch",
    "roll"         : "Roll",
    "G_force"      : "G Force",
    "vario"        : "Vario",
    "DP"           : "Dynamic Pressure",
    "T_sensor"     : "Sensor Temperature",
    "A0_cor_DP"    : "A0 Corrected DP",
    "A1_cor_DP"    : "A1 Corrected DP",
    "P_stat"       : "Static Pressure",
    "air_T"        : "Air Temperature",
    "air_RH"       : "Relative Humidity",
    "wind_origin"  : "Wind Direction",
    "wind_vel"     : "Wind Speed",
    "netto"        : "Netto",
    "IAS"          : "Indicated Airspeed",
    "AirES"        : "Saturation Vapor",
    "AirE"        : "Vapor Pressure",
    "AirW"        : "Mixing Ratio",
    "AirTd"        : "Dew Point",
    "LCL"        : "Cloud Base",
    "AirTheta"        : "Potential Temperature",
    "AirRho"        : "Air Density",
    "VarioIAS"        : "Vario IAS ",
    "TAS"        : "True Air Speed",
    "turb"          : "Turbulence",
    
}

VARIABLE_KEYS = {v: k for k, v in VARIABLE_LABELS.items()}

def mapping(value, fromLow, fromHigh, toLow, toHigh):
    return (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow
    

def min_res(data):

    diff_min = 9999
    for i in range(1,len(data)-1):
        diff = data[i] - data[i-1]
        if abs(diff) < diff_min and diff !=0:
            diff_min = abs(diff)
    return diff_min


def sma_filter(data, window_size_sma):
    """
    Apply a Simple Moving Average filter to data.
    Replaces the first and last window_size values with the original raw values
    to avoid edge effects from convolution.
    """
    if window_size_sma <= 1 or len(data) == 0:
        return data  # pas de filtrage nécessaire
    
    if window_size_sma > len(data):
        window_size_sma = len(data) 
    kernel_sma = np.ones(window_size_sma) / window_size_sma
    filtered = np.convolve(data, kernel_sma, mode='same')
    # Remplace les bords par les valeurs brutes
    filtered[:window_size_sma] = data[:window_size_sma]
    filtered[-window_size_sma:] = data[-window_size_sma:]
    return filtered



def get_label(variable: str) -> str:
    """
    Return a more comprehensive label from the VARIABLE_LEVELS list
    """
    return VARIABLE_LABELS.get(variable, variable)



def is_all_nan(data):

    arr = np.asarray(data)

    # types numériques seulement
    if np.issubdtype(arr.dtype, np.number):
        return np.all(np.isnan(arr))

    return False


def sort_combobox_alphabetically(combobox):
    """
    Trie un QComboBox par ordre alphabétique
    tout en conservant les userData.
    """

    items = []

    for i in range(combobox.count()):

        text = combobox.itemText(i)
        data = combobox.itemData(i)

        items.append((text, data))

    # tri alphabétique insensible à la casse
    items.sort(key=lambda x: x[0].lower())

    combobox.clear()

    for text, data in items:
        combobox.addItem(text, userData=data)

def get_variable(label: str) -> str:
    """
    Return the internal variable name from a user-friendly label.
    """
    return VARIABLE_KEYS.get(label, label)

def interp_spline(t_new, t, values):
    
    values = np.asarray(values, dtype=float)

    # supprime NaN
    mask = ~np.isnan(values)

    t_clean = t[mask]
    v_clean = values[mask]

    # fallback sécurité
    if len(v_clean) < 2:
        return np.full_like(t_new, np.nan)

    spline = CubicSpline(
        t_clean,
        v_clean,
        bc_type='natural'
    )

    return spline(t_new)


def interp_nearest(t_new, t, values):

    values = np.asarray(values, dtype=float)

    # suppression NaN
    mask = ~np.isnan(values)

    t_clean = t[mask]
    v_clean = values[mask]

    # sécurité
    if len(v_clean) < 2:
        return np.full_like(t_new, np.nan)

    f = interp1d(
        t_clean,
        v_clean,
        kind='nearest',
        bounds_error=False,
        fill_value=np.nan
    )

    return f(t_new)



def rgba_to_hex(r: float, g: float, b: float, a: float = 1.0) -> str:
    """
    Convertit RGBA (0.0 → 1.0) en hexadécimal '#RRGGBBAA'.
    """
    ri, gi, bi, ai = (int(round(c * 255)) for c in (r, g, b, a))
    return f'#{ri:02X}{gi:02X}{bi:02X}{ai:02X}'


def hex_to_rgba(hex_color: str) -> tuple[float, float, float, float]:
    """
    Convertit un hexadécimal '#RRGGBB' ou '#RRGGBBAA' en RGBA (0.0 → 1.0).
    Le '#' est optionnel.
    """
    h = hex_color.lstrip('#')

    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = 255
    elif len(h) == 8:
        r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
    else:
        raise ValueError(f"Format hex invalide : '{hex_color}' (attendu #RRGGBB ou #RRGGBBAA)")

    return r / 255.0, g / 255.0, b / 255.0, a / 255.0



def highlight_row(table, row, duration_ms=4000):
    """
    Makes a row blink in yellow during duration_ms.
    """

    yellow = QColor(255, 255, 120)

    original_colors = {}

    for col in range(table.columnCount()):
        item = table.item(row, col)

        if item is not None:
            original_colors[col] = item.background()
            item.setBackground(yellow)

    blink_count = 0

    def blink():
        nonlocal blink_count

        visible = blink_count % 2 == 0

        for col in range(table.columnCount()):
            item = table.item(row, col)

            if item is None:
                continue

            if visible:
                item.setBackground(yellow)
            else:
                item.setBackground(original_colors[col])

        blink_count += 1

    timer = QTimer(table)
    timer.timeout.connect(blink)
    timer.start(300)  # 300 ms

    QTimer.singleShot(duration_ms, lambda: (
        timer.stop(),
        [
            table.item(row, col).setBackground(original_colors[col])
            for col in original_colors
            if table.item(row, col)
        ]
    ))



### COPY TABLE TO MARKDOWN

# ---------------------------------------------------------------------------
# Internal conversion
# ---------------------------------------------------------------------------

def _table_to_markdown(table: QTableWidget, rows: list[int]) -> str:
 
    if not rows:
        return ""

    col_count = table.columnCount()

    # Colonnes à inclure : celles avec un header non vide
    visible_cols = []
    headers = []
    for col in range(col_count):
        header_item = table.horizontalHeaderItem(col)
        header_text = header_item.text().strip() if header_item else ""
        if header_text:
            visible_cols.append(col)
            headers.append(header_text)

    if not visible_cols:
        # Fallback : toutes les colonnes, numérotées
        visible_cols = list(range(col_count))
        headers = [str(c + 1) for c in visible_cols]

    # Collecte des cellules
    cell_rows: list[list[str]] = []
    for row in rows:
        if table.isRowHidden(row):
            continue
        cells = []
        for col in visible_cols:
            item = table.item(row, col)
            widget = table.cellWidget(row, col)
            if item is not None:
                cells.append(item.text().strip())
            elif widget is not None:
                # Cas d'un widget inséré dans la cellule (ex: QLabel, QComboBox)
                text = getattr(widget, "text", None) or getattr(widget, "currentText", None)
                cells.append(text().strip() if callable(text) else "")
            else:
                cells.append("")
        cell_rows.append(cells)

    if not cell_rows:
        return ""

    # Calcul des largeurs de colonnes pour l'alignement
    col_widths = [len(h) for h in headers]
    for cells in cell_rows:
        for i, cell in enumerate(cells):
            col_widths[i] = max(col_widths[i], len(cell))

    def _row_str(cells: list[str]) -> str:
        padded = [cell.ljust(col_widths[i]) for i, cell in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    def _separator() -> str:
        return "| " + " | ".join("-" * w for w in col_widths) + " |"

    lines = [_row_str(headers), _separator()]
    lines += [_row_str(cells) for cells in cell_rows]
    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> None:
    QApplication.clipboard().setText(text)


# ---------------------------------------------------------------------------
# Installation du menu contextuel
# ---------------------------------------------------------------------------

def install_markdown_copy(table: QTableWidget) -> None:
    """
    Installe un menu contextuel sur `table` pour copier le contenu en Markdown.

    Appelle cette fonction une seule fois par table, typiquement dans
    __init__ après uic.loadUi(). Aucune modification du .ui n'est nécessaire.
    """
    table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _show_context_menu(pos):
        selected_rows = sorted({idx.row() for idx in table.selectedIndexes()})
        all_rows = list(range(table.rowCount()))

        menu = QMenu(table)

        # --- Action : copy all ---
        action_all = QAction("Copy content", table)
        action_all.setEnabled(bool(all_rows))
        action_all.triggered.connect(
            lambda: _copy_to_clipboard(_table_to_markdown(table, all_rows))
        )
        menu.addAction(action_all)

        menu.exec(table.viewport().mapToGlobal(pos))

    table.customContextMenuRequested.connect(_show_context_menu)