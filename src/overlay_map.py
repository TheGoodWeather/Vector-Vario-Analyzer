 
# import math
# import threading
# from io import BytesIO
# from concurrent.futures import ThreadPoolExecutor
 
# import numpy as np
# import requests
# from PIL import Image
 
# import pyqtgraph as pg
# from pyqtgraph.Qt import QtCore, QtGui
 
 
# # ---------------------------------------------------------------------------
# # Helpers de conversion WGS84 ↔ tuiles OSM
# # ---------------------------------------------------------------------------
 
# def lon_to_tile_x(lon: float, zoom: int) -> float:
#     """Longitude → coordonnée X tuile (float)."""
#     return (lon + 180.0) / 360.0 * (2 ** zoom)
 
 
# def lat_to_tile_y(lat: float, zoom: int) -> float:
#     """Latitude → coordonnée Y tuile (float, axe vers le bas)."""
#     lat_r = math.radians(lat)
#     return (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * (2 ** zoom)
 
 
# def tile_x_to_lon(x: float, zoom: int) -> float:
#     return x / (2 ** zoom) * 360.0 - 180.0
 
 
# def tile_y_to_lat(y: float, zoom: int) -> float:
#     n = math.pi - 2.0 * math.pi * y / (2 ** zoom)
#     return math.degrees(math.atan(math.sinh(n)))
 
 
# def best_zoom(lon_range: float, lat_range: float, width_px: int, height_px: int,
#               tile_size: int = 256) -> int:
#     """Calcule le zoom OSM optimal pour couvrir la vue sans trop de tuiles."""
#     # Nombre de tuiles idéales en X et Y
#     tiles_x = width_px / tile_size
#     tiles_y = height_px / tile_size
 
#     # Zoom en X
#     zoom_x = math.log2(360.0 / lon_range * tiles_x) if lon_range > 0 else 15
#     zoom_y = math.log2(170.0 / lat_range * tiles_y) if lat_range > 0 else 15  # ~170° de lat utile
 
#     zoom = int(min(zoom_x, zoom_y)) + 2
#     return max(0, min(zoom, 19))
 
 
# # ---------------------------------------------------------------------------
# # Couche ImageItem pour une tuile
# # ---------------------------------------------------------------------------
 
# class TileImageItem(pg.ImageItem):
#     """Un pg.ImageItem positionné sur la carte en coordonnées lon/lat."""
 
#     def __init__(self, tile_x: int, tile_y: int, zoom: int, image_array: np.ndarray):
#         super().__init__(image_array)
 
#         # Calcul des bornes lon/lat de la tuile
#         lon_min = tile_x_to_lon(tile_x,     zoom)
#         lon_max = tile_x_to_lon(tile_x + 1, zoom)
#         lat_max = tile_y_to_lat(tile_y,     zoom)   # tile_y croît vers le bas → lat décroît
#         lat_min = tile_y_to_lat(tile_y + 1, zoom)
 
#         # Positionnement dans le repère lon/lat
#         rect = QtCore.QRectF(lon_min, lat_min, lon_max - lon_min, lat_max - lat_min)
#         self.setRect(rect)
#         self.setZValue(-100)   # Toujours derrière les données utilisateur
 
 
# # ---------------------------------------------------------------------------
# # Classe principale
# # ---------------------------------------------------------------------------
 
# class OSMTileOverlay(QtCore.QObject):
#     """
#     Superpose des tuiles OSM sur un PlotWidget pyqtgraph existant.
 
#     Le PlotWidget doit utiliser la longitude en X et la latitude en Y.
 
#     Parameters
#     ----------
#     plot_widget : pg.PlotWidget
#         Widget cible (axes déjà en lon/lat).
#     tile_url : str
#         URL template OSM, ex: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
#     user_agent : str
#         User-Agent requis par la politique d'utilisation d'OSM.
#     max_workers : int
#         Nombre de threads de téléchargement simultanés.
#     debounce_ms : int
#         Délai (ms) avant de recharger les tuiles après un zoom/pan
#         (évite les rafales de requêtes).
#     """
 
#     _tile_ready = QtCore.pyqtSignal(int, int, int, object)   # x, y, zoom, ndarray
 
#     def __init__(
#         self,
#         plot_widget: pg.PlotWidget,
#         tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}&layers=P.png",
#         user_agent: str = "VVA Software (open-source)",
#         max_workers: int = 8,
#         debounce_ms: int = 200,
#     ):
#         super().__init__(plot_widget)
 
#         self._pw       = plot_widget
#         self._view     = plot_widget.getViewBox()
#         self._tile_url = tile_url
#         self._headers  = {"User-Agent": user_agent}
#         self._executor = ThreadPoolExecutor(max_workers=max_workers)
 
#         # Cache mémoire  {(zoom, x, y) -> np.ndarray}
#         self._cache: dict = {}
#         self._cache_lock  = threading.Lock()
 
#         # Tuiles actuellement affichées  {(zoom, x, y) -> TileImageItem}
#         self._displayed: dict = {}
 
#         # Zoom courant
#         self._current_zoom = -1
 
#         # Timer de debounce
#         self._debounce_timer = QtCore.QTimer(self)
#         self._debounce_timer.setSingleShot(True)
#         self._debounce_timer.setInterval(debounce_ms)
#         self._debounce_timer.timeout.connect(self._refresh_tiles)
 
#         # Signal interne émis depuis les threads de DL
#         #self._tile_ready.connect(self._on_tile_ready, QtCore.Qt.ConnectionType.QueuedConnection)
 
#         # Connexion au signal de changement de vue
#         #self._view.sigRangeChanged.connect(self._on_range_changed)
 
#         # Premier rendu
#         QtCore.QTimer.singleShot(100, self._refresh_tiles)
 
#     # ------------------------------------------------------------------
#     # Slots Qt
#     # ------------------------------------------------------------------
 
#     def _on_range_changed(self, *_):
#         """Déclenche le debounce à chaque zoom/pan."""
#         self._debounce_timer.start()
 
#     def _on_tile_ready(self, tx: int, ty: int, zoom: int, img_array):
#         """Reçu dans le thread principal : affiche la tuile."""
#         key = (zoom, tx, ty)
 
#         # La vue a peut-être changé de zoom entre-temps → ignorer
#         if zoom != self._current_zoom:
#             return
 
#         # Supprimer l'ancienne tuile si elle existe déjà
#         if key in self._displayed:
#             self._pw.removeItem(self._displayed.pop(key))
 
#         item = TileImageItem(tx, ty, zoom, img_array)
#         self._pw.addItem(item)
#         self._displayed[key] = item
 
#     # ------------------------------------------------------------------
#     # Logique principale
#     # ------------------------------------------------------------------
 
#     def _refresh_tiles(self):
#         """Calcule les tuiles nécessaires et lance leur chargement."""
#         view_range = self._view.viewRange()
#         lon_min, lon_max = view_range[0]
#         lat_min, lat_max = view_range[1]
 
#         # Sécurisation des bornes
#         lon_min = max(-180.0, lon_min)
#         lon_max = min(180.0,  lon_max)
#         lat_min = max(-85.051129, lat_min)
#         lat_max = min(85.051129,  lat_max)
 
#         if lon_max <= lon_min or lat_max <= lat_min:
#             return
 
#         # Taille en pixels de la viewport
#         rect  = self._view.screenGeometry()
#         w_px  = rect.width()  or 800
#         h_px  = rect.height() or 600
 
#         zoom = best_zoom(lon_max - lon_min, lat_max - lat_min, w_px, h_px)
#         self._current_zoom = zoom
 
#         # Indices de tuiles couvrant la vue
#         tx_min = int(math.floor(lon_to_tile_x(lon_min, zoom)))
#         tx_max = int(math.floor(lon_to_tile_x(lon_max, zoom)))
#         ty_min = int(math.floor(lat_to_tile_y(lat_max, zoom)))   # lat_max → ty le plus petit
#         ty_max = int(math.floor(lat_to_tile_y(lat_min, zoom)))
 
#         n_tiles = 2 ** zoom
#         tx_min = max(0, tx_min)
#         tx_max = min(n_tiles - 1, tx_max)
#         ty_min = max(0, ty_min)
#         ty_max = min(n_tiles - 1, ty_max)
 
#         needed = set()
#         for tx in range(tx_min, tx_max + 1):
#             for ty in range(ty_min, ty_max + 1):
#                 needed.add((zoom, tx, ty))
 
#         # Supprimer les tuiles qui ne sont plus dans la vue ou d'un ancien zoom
#         to_remove = [k for k in list(self._displayed.keys()) if k not in needed]
#         for key in to_remove:
#             self._pw.removeItem(self._displayed.pop(key))
 
#         # Charger les tuiles manquantes
#         for key in needed:
#             if key not in self._displayed:
#                 _, tx, ty = key
#                 self._load_tile_async(tx, ty, zoom)
 
#     def _load_tile_async(self, tx: int, ty: int, zoom: int):
#         """Soumet le téléchargement dans le thread pool."""
#         self._executor.submit(self._download_tile, tx, ty, zoom)
 
#     def _download_tile(self, tx: int, ty: int, zoom: int):
#         """Télécharge (ou récupère du cache) une tuile et émet le signal."""
#         key = (zoom, tx, ty)
 
#         with self._cache_lock:
#             if key in self._cache:
#                 arr = self._cache[key]
#                 self._tile_ready.emit(tx, ty, zoom, arr)
#                 return
        
#         url = self._tile_url.format(z=zoom, x=tx, y=ty)
#         try:
#             resp = requests.get(url, headers=self._headers, timeout=10)
#             resp.raise_for_status()
#             img  = Image.open(BytesIO(resp.content)).convert("RGBA")
#             arr  = np.array(img)
#             # pyqtgraph ImageItem attend (width, height, channels) avec axe Y non inversé
#             arr = np.flipud(arr)                    # remet l'origine en bas à gauche
#             arr = np.transpose(arr, (1, 0, 2))     # height,width → width,height pour ImageItem

 
#             with self._cache_lock:
#                 self._cache[key] = arr
 
#             self._tile_ready.emit(tx, ty, zoom, arr)
 
#         except Exception as exc:
#             print(f"[OSMTileOverlay] Erreur tuile ({zoom}/{tx}/{ty}): {exc}")
 
#     # ------------------------------------------------------------------
#     # Nettoyage
#     # ------------------------------------------------------------------
 
#     def clear(self):
#         """Retire toutes les tuiles du widget."""
#         for item in self._displayed.values():
#             self._pw.removeItem(item)
#         self._displayed.clear()
 
#     def invalidate_cache(self):
#         """Vide le cache mémoire et recharge les tuiles."""
#         with self._cache_lock:
#             self._cache.clear()
#         self.clear()
#         self._refresh_tiles()



"""
OSM Tile Overlay pour un PlotWidget pyqtgraph existant
======================================================
Ajoute des tuiles OpenStreetMap en arrière-plan d'un PlotWidget
dont les axes X = longitude et Y = latitude (WGS84).
 
Utilisation minimale :
    plot_widget = pg.PlotWidget()
    overlay = OSMTileOverlay(plot_widget)
 
Dépendances : pyqtgraph, PyQt6 (ou PyQt5/PySide6), requests, Pillow
    pip install pyqtgraph requests Pillow
 
Système de cache à deux niveaux
--------------------------------
  L1 – LRU mémoire  : accès instantané, 0 I/O (défaut : 256 tuiles ≈ ~64 Mo)
  L2 – Disque       : ~/.cache/osm_tiles/<provider>/<z>/<x>/<y>.png
                       survit aux redémarrages, TTL configurable (défaut : 30 jours)
 
Stratégie de résolution pour chaque tuile :
  1. L1 hit  → émission immédiate, 0 I/O
  2. L2 hit  → décodage PNG depuis disque, promotion en L1
  3. Miss     → téléchargement HTTP → écriture L2 → promotion L1
"""
 
import math
import threading
import time
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
 
import numpy as np
import requests
from PIL import Image
 
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
 
 
# ---------------------------------------------------------------------------
# Helpers de conversion WGS84 <-> tuiles OSM
# ---------------------------------------------------------------------------
 
def lon_to_tile_x(lon: float, zoom: int) -> float:
    return (lon + 180.0) / 360.0 * (2 ** zoom)
 
 
def lat_to_tile_y(lat: float, zoom: int) -> float:
    lat_r = math.radians(lat)
    return (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * (2 ** zoom)
 
 
def tile_x_to_lon(x: float, zoom: int) -> float:
    return x / (2 ** zoom) * 360.0 - 180.0
 
 
def tile_y_to_lat(y: float, zoom: int) -> float:
    n = math.pi - 2.0 * math.pi * y / (2 ** zoom)
    return math.degrees(math.atan(math.sinh(n)))
 
 
def best_zoom(lon_range: float, lat_range: float, width_px: int, height_px: int,
              tile_size: int = 256) -> int:
    tiles_x = width_px / tile_size
    tiles_y = height_px / tile_size
    zoom_x  = math.log2(360.0 / lon_range * tiles_x) if lon_range > 0 else 15
    zoom_y  = math.log2(170.0 / lat_range * tiles_y) if lat_range > 0 else 15
    return max(0, min(int(min(zoom_x, zoom_y)), 19)) +1
 
 
def _decode_png(raw_bytes: bytes) -> np.ndarray:
    """Décode un PNG brut en ndarray au format attendu par pg.ImageItem."""
    img = Image.open(BytesIO(raw_bytes)).convert("RGBA")
    arr = np.array(img)
    arr = np.flipud(arr)                  # origine bas-gauche pour pg.ImageItem
    arr = np.transpose(arr, (1, 0, 2))   # (H,W,C) -> (W,H,C)
    return arr
 
 
# ---------------------------------------------------------------------------
# Cache L1 : LRU mémoire thread-safe
# ---------------------------------------------------------------------------
 
class _LRUCache:
    """Cache LRU thread-safe stockant des np.ndarray."""
 
    def __init__(self, max_size: int = 256):
        self._max  = max_size
        self._data = OrderedDict()
        self._lock = threading.Lock()
 
    def get(self, key):
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]
 
    def put(self, key, value: np.ndarray):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            if len(self._data) > self._max:
                self._data.popitem(last=False)   # éviction LRU
 
    def clear(self):
        with self._lock:
            self._data.clear()
 
    def __len__(self):
        with self._lock:
            return len(self._data)
 
 
# ---------------------------------------------------------------------------
# Cache L2 : disque persistant avec TTL et quota
# ---------------------------------------------------------------------------
 
class _DiskCache:
    """
    Cache disque pour tuiles PNG.
 
    Arborescence : <root>/<z>/<x>/<y>.png
                   <root>/<z>/<x>/<y>.meta  (timestamp float en texte)
 
    Parameters
    ----------
    root : Path
        Répertoire racine propre à ce fournisseur de tuiles.
    ttl_seconds : int
        Durée de vie d'une tuile (défaut : 30 jours).
    max_size_mb : int
        Quota disque en Mo ; 0 = illimité.
    """
 
    def __init__(self, root: Path, ttl_seconds: int = 30 * 24 * 3600,
                 max_size_mb: int = 500):
        self._root      = root
        self._ttl       = ttl_seconds
        self._max_bytes = max_size_mb * 1024 * 1024
        self._evict_lk  = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)
 
    def _paths(self, zoom, tx, ty):
        base = self._root / str(zoom) / str(tx) / str(ty)
        return base.with_suffix(".png"), base.with_suffix(".meta")
 
    # -- lecture --------------------------------------------------------
 
    def get(self, zoom: int, tx: int, ty: int):
        """Retourne le ndarray si présent et valide, sinon None."""
        png, meta = self._paths(zoom, tx, ty)
        if not png.exists():
            return None
 
        # Vérification TTL
        try:
            ts = float(meta.read_text()) if meta.exists() else png.stat().st_mtime
            if time.time() - ts > self._ttl:
                png.unlink(missing_ok=True)
                meta.unlink(missing_ok=True)
                return None
        except (ValueError, OSError):
            return None
 
        try:
            return _decode_png(png.read_bytes())
        except Exception:
            return None
 
    # -- écriture -------------------------------------------------------
 
    def put(self, zoom: int, tx: int, ty: int, raw_bytes: bytes):
        """Sauvegarde les bytes PNG bruts sur disque."""
        png, meta = self._paths(zoom, tx, ty)
        try:
            png.parent.mkdir(parents=True, exist_ok=True)
            png.write_bytes(raw_bytes)
            meta.write_text(str(time.time()))
        except OSError as e:
            print(f"[DiskCache] Ecriture impossible ({zoom}/{tx}/{ty}): {e}")
            return
 
        if self._max_bytes > 0:
            threading.Thread(target=self._evict_if_needed, daemon=True).start()
 
    # -- nettoyage LRU disque ------------------------------------------
 
    def _evict_if_needed(self):
        if not self._evict_lk.acquire(blocking=False):
            return
        try:
            files = sorted(self._root.rglob("*.png"),
                           key=lambda p: p.stat().st_mtime)
            total = sum(p.stat().st_size for p in files)
            for p in files:
                if total <= self._max_bytes:
                    break
                size = p.stat().st_size
                p.unlink(missing_ok=True)
                p.with_suffix(".meta").unlink(missing_ok=True)
                total -= size
        except Exception:
            pass
        finally:
            self._evict_lk.release()
 
    def clear(self):
        import shutil
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)
 
    def stats(self) -> dict:
        """Retourne des statistiques du cache disque."""
        files = list(self._root.rglob("*.png"))
        total = sum(p.stat().st_size for p in files)
        return {"tiles": len(files), "size_mb": round(total / 1024 / 1024, 2)}
 
 
# ---------------------------------------------------------------------------
# TileImageItem
# ---------------------------------------------------------------------------
 
class TileImageItem(pg.ImageItem):
    """pg.ImageItem positionné en coordonnées lon/lat."""
 
    def __init__(self, tile_x: int, tile_y: int, zoom: int, arr: np.ndarray):
        super().__init__(arr)
        lon_min = tile_x_to_lon(tile_x,     zoom)
        lon_max = tile_x_to_lon(tile_x + 1, zoom)
        lat_max = tile_y_to_lat(tile_y,     zoom)
        lat_min = tile_y_to_lat(tile_y + 1, zoom)
        self.setRect(QtCore.QRectF(lon_min, lat_min,
                                   lon_max - lon_min, lat_max - lat_min))
        self.setZValue(-100)
        
    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        return None
 
 
# ---------------------------------------------------------------------------
# OSMTileOverlay
# ---------------------------------------------------------------------------
 
class OSMTileOverlay(QtCore.QObject):
    """
    Superpose des tuiles XYZ (OSM, OpenTopoMap, ...) sur un PlotWidget
    pyqtgraph dont les axes sont en longitude (X) et latitude (Y).
 
    Parameters
    ----------
    plot_widget : pg.PlotWidget
    tile_url : str
        URL template, ex: "https://tile.opentopomap.org/{z}/{x}/{y}.png"
    user_agent : str
        Requis par la politique d'utilisation OSM/OpenTopoMap.
    provider_slug : str | None
        Identifiant du fournisseur pour isoler le cache disque.
        Si None, derive automatiquement du domaine de tile_url.
    cache_dir : Path | str | None
        Repertoire racine du cache disque (defaut : ~/.cache/osm_tiles).
    mem_cache_size : int
        Nombre de tuiles en cache memoire LRU (defaut : 256).
    disk_ttl_days : int
        Duree de vie des tuiles sur disque en jours (defaut : 30).
    disk_max_mb : int
        Quota disque en Mo par fournisseur (defaut : 500, 0 = illimite).
    max_workers : int
        Threads de telechargement simultanes.
    debounce_ms : int
        Delai anti-rebond apres zoom/pan avant rechargement.
    """
 
    _tile_ready = QtCore.pyqtSignal(int, int, int, object)   # tx, ty, zoom, ndarray
 
    def __init__(
        self,
        plot_widget,
        tile_url       = "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        user_agent     = "PyQtGraphOSMOverlay/1.0 (open-source)",
        provider_slug  = None,
        cache_dir      = None,
        mem_cache_size = 256,
        disk_ttl_days  = 30,
        disk_max_mb    = 500,
        max_workers    = 8,
        debounce_ms    = 200,
    ):
        super().__init__(plot_widget)
 
        self._pw       = plot_widget
        self._view     = plot_widget.getViewBox()
        self._tile_url = tile_url
        self._headers  = {"User-Agent": user_agent}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._visible = False          # état affichage (radiobutton)
        self._opacity = 1.0            # opacité courante (0.0 → 1.0)
 
        # Slug fournisseur
        if provider_slug is None:
            from urllib.parse import urlparse
            provider_slug = urlparse(tile_url).netloc.replace(".", "_") or "tiles"
        self._slug = provider_slug
 
        # Cache L1 (memoire LRU)
        self._l1 = _LRUCache(max_size=mem_cache_size)
 
        # Cache L2 (disque)
        root = (Path(cache_dir) if cache_dir else Path.home() / ".cache" / "osm_tiles")
        self._l2 = _DiskCache(
            root        = root / provider_slug,
            ttl_seconds = disk_ttl_days * 24 * 3600,
            max_size_mb = disk_max_mb,
        )
 
        # Ensemble des tuiles en cours de telechargement (evite les doublons)
        self._in_flight      = set()
        self._in_flight_lock = threading.Lock()
 
        # Tuiles affichees {(zoom, tx, ty) -> TileImageItem}
        self._displayed = {}
 
        # Zoom courant
        self._current_zoom = -1
 
        # Statistiques
        self._stats = {"l1_hit": 0, "l2_hit": 0, "dl": 0, "dl_err": 0}
 
        # Timer debounce
        self._debounce = QtCore.QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(debounce_ms)
        self._debounce.timeout.connect(self._refresh_tiles)
 
        # Signal inter-thread -> thread principal
        self._tile_ready.connect(self._on_tile_ready,
                                 QtCore.Qt.ConnectionType.QueuedConnection)
 
        self._view.sigRangeChanged.connect(self._on_range_changed)
        QtCore.QTimer.singleShot(100, self._refresh_tiles)
 
    # ------------------------------------------------------------------
    # Slots Qt (thread principal)
    # ------------------------------------------------------------------
 
    def _on_range_changed(self, *_):
        self._debounce.start()
 
    def _on_tile_ready(self, tx: int, ty: int, zoom: int, arr):
        key = (zoom, tx, ty)
    
        with self._in_flight_lock:
            self._in_flight.discard(key)
    
        if zoom != self._current_zoom or not self._visible:
            return
    
        if key in self._displayed:
            self._pw.removeItem(self._displayed.pop(key))
    
        item = TileImageItem(tx, ty, zoom, arr)
        item.setOpacity(self._opacity)  
    
        self._pw.addItem(item)
        self._displayed[key] = item
 
    # ------------------------------------------------------------------
    # Rafraichissement
    # ------------------------------------------------------------------
    def display_tiles(self, visible: bool):
        """
        Active ou désactive l'affichage des tuiles.
    
        Parameters
        ----------
        visible : bool
            True = affiche les tuiles
            False = les masque
        """
        self._visible = visible
    
        if not visible:
            # On retire simplement de l'affichage (cache conservé)
            self.clear_display()
            return
    
        # Si on réactive → recharger ce qui est visible
        self._refresh_tiles()
    
    def set_opacity(self, opacity: float):
        """
        Définit l'opacité des tuiles.
    
        Parameters
        ----------
        opacity : float
            Valeur entre 0.0 (transparent) et 1.0 (opaque)
        """
        opacity = max(0.0, min(1.0, opacity))  # clamp
        self._opacity = opacity
    
        # Appliquer aux tuiles déjà affichées
        for item in self._displayed.values():
            item.setOpacity(opacity)
        
        
    def _refresh_tiles(self):
        if not self._visible:
            return
        vr = self._view.viewRange()
        lon_min, lon_max = vr[0]
        lat_min, lat_max = vr[1]
 
        lon_min = max(-180.0,     lon_min)
        lon_max = min(180.0,      lon_max)
        lat_min = max(-85.051129, lat_min)
        lat_max = min(85.051129,  lat_max)
 
        if lon_max <= lon_min or lat_max <= lat_min:
            return
 
        rect = self._view.screenGeometry()
        w_px = rect.width()  or 800
        h_px = rect.height() or 600
 
        zoom = best_zoom(lon_max - lon_min, lat_max - lat_min, w_px, h_px)
        self._current_zoom = zoom
        
        if self._current_zoom > 18: #impossible to get better zoom
            return 
 
        n      = 2 ** zoom
        tx_min = max(0,     int(math.floor(lon_to_tile_x(lon_min, zoom))))
        tx_max = min(n - 1, int(math.floor(lon_to_tile_x(lon_max, zoom))))
        ty_min = max(0,     int(math.floor(lat_to_tile_y(lat_max, zoom))))
        ty_max = min(n - 1, int(math.floor(lat_to_tile_y(lat_min, zoom))))
 
        needed = {(zoom, tx, ty)
                  for tx in range(tx_min, tx_max + 1)
                  for ty in range(ty_min, ty_max + 1)}
 
        # Retirer les tuiles obsoletes
        for key in [k for k in self._displayed if k not in needed]:
            self._pw.removeItem(self._displayed.pop(key))
 
        # Charger les tuiles manquantes
        for key in needed:
            if key not in self._displayed:
                _, tx, ty = key
                self._schedule(tx, ty, zoom)
 
    def _schedule(self, tx: int, ty: int, zoom: int):
        """Soumet le chargement uniquement si pas deja en cours."""
        key = (zoom, tx, ty)
        with self._in_flight_lock:
            if key in self._in_flight:
                return
            self._in_flight.add(key)
        self._executor.submit(self._load_tile, tx, ty, zoom)
 
    # ------------------------------------------------------------------
    # Chargement (thread pool) : cascade L1 -> L2 -> HTTP
    # ------------------------------------------------------------------
 
    def _load_tile(self, tx: int, ty: int, zoom: int):
        key = (zoom, tx, ty)
 
        # 1. Cache L1 (memoire)
        arr = self._l1.get(key)
        if arr is not None:
            self._stats["l1_hit"] += 1
            self._tile_ready.emit(tx, ty, zoom, arr)
            return
 
        # 2. Cache L2 (disque)
        arr = self._l2.get(zoom, tx, ty)
        if arr is not None:
            self._stats["l2_hit"] += 1
            self._l1.put(key, arr)             # promotion L2 -> L1
            self._tile_ready.emit(tx, ty, zoom, arr)
            return
 
        # 3. Telechargement HTTP
        url = self._tile_url.format(z=zoom, x=tx, y=ty)
        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
            resp.raise_for_status()
            raw  = resp.content
            arr  = _decode_png(raw)
            self._stats["dl"] += 1
            self._l2.put(zoom, tx, ty, raw)    # ecriture disque (bytes bruts)
            self._l1.put(key, arr)             # promotion en memoire
            self._tile_ready.emit(tx, ty, zoom, arr)
        except Exception as exc:
            self._stats["dl_err"] += 1
            with self._in_flight_lock:
                self._in_flight.discard(key)
            print(f"[OSMTileOverlay] Erreur ({zoom}/{tx}/{ty}): {exc}")
 
    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
 
    def clear_display(self):
        """Retire toutes les tuiles affichees (ne vide pas le cache)."""
        for item in self._displayed.values():
            self._pw.removeItem(item)
        self._displayed.clear()
 
    def invalidate_memory_cache(self):
        """Vide le cache L1 uniquement (le disque est conserve)."""
        self._l1.clear()
 
    def invalidate_disk_cache(self):
        """Vide le cache L2 disque et force le retelechargement."""
        self._l2.clear()
        self.clear_display()
        self._refresh_tiles()
 
    def invalidate_all(self):
        """Vide L1 + L2 et force le retelechargement."""
        self._l1.clear()
        self.invalidate_disk_cache()
 
    def cache_stats(self) -> dict:
        """
        Retourne un resume des performances du cache.
 
        Exemple :
            {'l1_hits': 42, 'l1_size': 18,
             'l2_hits': 7,  'disk_tiles': 312, 'disk_mb': 24.5,
             'downloads': 5, 'errors': 0}
        """
        disk = self._l2.stats()
        return {
            "l1_hits":    self._stats["l1_hit"],
            "l1_size":    len(self._l1),
            "l2_hits":    self._stats["l2_hit"],
            "disk_tiles": disk["tiles"],
            "disk_mb":    disk["size_mb"],
            "downloads":  self._stats["dl"],
            "errors":     self._stats["dl_err"],
        }
 