 
import math
import threading
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
 
import numpy as np
import requests
from PIL import Image
 
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
 
 
# ---------------------------------------------------------------------------
# Helpers de conversion WGS84 ↔ tuiles OSM
# ---------------------------------------------------------------------------
 
def lon_to_tile_x(lon: float, zoom: int) -> float:
    """Longitude → coordonnée X tuile (float)."""
    return (lon + 180.0) / 360.0 * (2 ** zoom)
 
 
def lat_to_tile_y(lat: float, zoom: int) -> float:
    """Latitude → coordonnée Y tuile (float, axe vers le bas)."""
    lat_r = math.radians(lat)
    return (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * (2 ** zoom)
 
 
def tile_x_to_lon(x: float, zoom: int) -> float:
    return x / (2 ** zoom) * 360.0 - 180.0
 
 
def tile_y_to_lat(y: float, zoom: int) -> float:
    n = math.pi - 2.0 * math.pi * y / (2 ** zoom)
    return math.degrees(math.atan(math.sinh(n)))
 
 
def best_zoom(lon_range: float, lat_range: float, width_px: int, height_px: int,
              tile_size: int = 256) -> int:
    """Calcule le zoom OSM optimal pour couvrir la vue sans trop de tuiles."""
    # Nombre de tuiles idéales en X et Y
    tiles_x = width_px / tile_size
    tiles_y = height_px / tile_size
 
    # Zoom en X
    zoom_x = math.log2(360.0 / lon_range * tiles_x) if lon_range > 0 else 15
    zoom_y = math.log2(170.0 / lat_range * tiles_y) if lat_range > 0 else 15  # ~170° de lat utile
 
    zoom = int(min(zoom_x, zoom_y)) + 2
    return max(0, min(zoom, 19))
 
 
# ---------------------------------------------------------------------------
# Couche ImageItem pour une tuile
# ---------------------------------------------------------------------------
 
class TileImageItem(pg.ImageItem):
    """Un pg.ImageItem positionné sur la carte en coordonnées lon/lat."""
 
    def __init__(self, tile_x: int, tile_y: int, zoom: int, image_array: np.ndarray):
        super().__init__(image_array)
 
        # Calcul des bornes lon/lat de la tuile
        lon_min = tile_x_to_lon(tile_x,     zoom)
        lon_max = tile_x_to_lon(tile_x + 1, zoom)
        lat_max = tile_y_to_lat(tile_y,     zoom)   # tile_y croît vers le bas → lat décroît
        lat_min = tile_y_to_lat(tile_y + 1, zoom)
 
        # Positionnement dans le repère lon/lat
        rect = QtCore.QRectF(lon_min, lat_min, lon_max - lon_min, lat_max - lat_min)
        self.setRect(rect)
        self.setZValue(-100)   # Toujours derrière les données utilisateur
 
 
# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------
 
class OSMTileOverlay(QtCore.QObject):
    """
    Superpose des tuiles OSM sur un PlotWidget pyqtgraph existant.
 
    Le PlotWidget doit utiliser la longitude en X et la latitude en Y.
 
    Parameters
    ----------
    plot_widget : pg.PlotWidget
        Widget cible (axes déjà en lon/lat).
    tile_url : str
        URL template OSM, ex: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    user_agent : str
        User-Agent requis par la politique d'utilisation d'OSM.
    max_workers : int
        Nombre de threads de téléchargement simultanés.
    debounce_ms : int
        Délai (ms) avant de recharger les tuiles après un zoom/pan
        (évite les rafales de requêtes).
    """
 
    _tile_ready = QtCore.pyqtSignal(int, int, int, object)   # x, y, zoom, ndarray
 
    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}&layers=P.png",
        user_agent: str = "VVA Software (open-source)",
        max_workers: int = 8,
        debounce_ms: int = 200,
    ):
        super().__init__(plot_widget)
 
        self._pw       = plot_widget
        self._view     = plot_widget.getViewBox()
        self._tile_url = tile_url
        self._headers  = {"User-Agent": user_agent}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
 
        # Cache mémoire  {(zoom, x, y) -> np.ndarray}
        self._cache: dict = {}
        self._cache_lock  = threading.Lock()
 
        # Tuiles actuellement affichées  {(zoom, x, y) -> TileImageItem}
        self._displayed: dict = {}
 
        # Zoom courant
        self._current_zoom = -1
 
        # Timer de debounce
        self._debounce_timer = QtCore.QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._refresh_tiles)
 
        # Signal interne émis depuis les threads de DL
        #self._tile_ready.connect(self._on_tile_ready, QtCore.Qt.ConnectionType.QueuedConnection)
 
        # Connexion au signal de changement de vue
        #self._view.sigRangeChanged.connect(self._on_range_changed)
 
        # Premier rendu
        QtCore.QTimer.singleShot(100, self._refresh_tiles)
 
    # ------------------------------------------------------------------
    # Slots Qt
    # ------------------------------------------------------------------
 
    def _on_range_changed(self, *_):
        """Déclenche le debounce à chaque zoom/pan."""
        self._debounce_timer.start()
 
    def _on_tile_ready(self, tx: int, ty: int, zoom: int, img_array):
        """Reçu dans le thread principal : affiche la tuile."""
        key = (zoom, tx, ty)
 
        # La vue a peut-être changé de zoom entre-temps → ignorer
        if zoom != self._current_zoom:
            return
 
        # Supprimer l'ancienne tuile si elle existe déjà
        if key in self._displayed:
            self._pw.removeItem(self._displayed.pop(key))
 
        item = TileImageItem(tx, ty, zoom, img_array)
        self._pw.addItem(item)
        self._displayed[key] = item
 
    # ------------------------------------------------------------------
    # Logique principale
    # ------------------------------------------------------------------
 
    def _refresh_tiles(self):
        """Calcule les tuiles nécessaires et lance leur chargement."""
        view_range = self._view.viewRange()
        lon_min, lon_max = view_range[0]
        lat_min, lat_max = view_range[1]
 
        # Sécurisation des bornes
        lon_min = max(-180.0, lon_min)
        lon_max = min(180.0,  lon_max)
        lat_min = max(-85.051129, lat_min)
        lat_max = min(85.051129,  lat_max)
 
        if lon_max <= lon_min or lat_max <= lat_min:
            return
 
        # Taille en pixels de la viewport
        rect  = self._view.screenGeometry()
        w_px  = rect.width()  or 800
        h_px  = rect.height() or 600
 
        zoom = best_zoom(lon_max - lon_min, lat_max - lat_min, w_px, h_px)
        self._current_zoom = zoom
 
        # Indices de tuiles couvrant la vue
        tx_min = int(math.floor(lon_to_tile_x(lon_min, zoom)))
        tx_max = int(math.floor(lon_to_tile_x(lon_max, zoom)))
        ty_min = int(math.floor(lat_to_tile_y(lat_max, zoom)))   # lat_max → ty le plus petit
        ty_max = int(math.floor(lat_to_tile_y(lat_min, zoom)))
 
        n_tiles = 2 ** zoom
        tx_min = max(0, tx_min)
        tx_max = min(n_tiles - 1, tx_max)
        ty_min = max(0, ty_min)
        ty_max = min(n_tiles - 1, ty_max)
 
        needed = set()
        for tx in range(tx_min, tx_max + 1):
            for ty in range(ty_min, ty_max + 1):
                needed.add((zoom, tx, ty))
 
        # Supprimer les tuiles qui ne sont plus dans la vue ou d'un ancien zoom
        to_remove = [k for k in list(self._displayed.keys()) if k not in needed]
        for key in to_remove:
            self._pw.removeItem(self._displayed.pop(key))
 
        # Charger les tuiles manquantes
        for key in needed:
            if key not in self._displayed:
                _, tx, ty = key
                self._load_tile_async(tx, ty, zoom)
 
    def _load_tile_async(self, tx: int, ty: int, zoom: int):
        """Soumet le téléchargement dans le thread pool."""
        self._executor.submit(self._download_tile, tx, ty, zoom)
 
    def _download_tile(self, tx: int, ty: int, zoom: int):
        """Télécharge (ou récupère du cache) une tuile et émet le signal."""
        key = (zoom, tx, ty)
 
        with self._cache_lock:
            if key in self._cache:
                arr = self._cache[key]
                self._tile_ready.emit(tx, ty, zoom, arr)
                return
        
        url = self._tile_url.format(z=zoom, x=tx, y=ty)
        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
            resp.raise_for_status()
            img  = Image.open(BytesIO(resp.content)).convert("RGBA")
            arr  = np.array(img)
            # pyqtgraph ImageItem attend (width, height, channels) avec axe Y non inversé
            arr = np.flipud(arr)                    # remet l'origine en bas à gauche
            arr = np.transpose(arr, (1, 0, 2))     # height,width → width,height pour ImageItem

 
            with self._cache_lock:
                self._cache[key] = arr
 
            self._tile_ready.emit(tx, ty, zoom, arr)
 
        except Exception as exc:
            print(f"[OSMTileOverlay] Erreur tuile ({zoom}/{tx}/{ty}): {exc}")
 
    # ------------------------------------------------------------------
    # Nettoyage
    # ------------------------------------------------------------------
 
    def clear(self):
        """Retire toutes les tuiles du widget."""
        for item in self._displayed.values():
            self._pw.removeItem(item)
        self._displayed.clear()
 
    def invalidate_cache(self):
        """Vide le cache mémoire et recharge les tuiles."""
        with self._cache_lock:
            self._cache.clear()
        self.clear()
        self._refresh_tiles()