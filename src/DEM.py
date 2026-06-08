"""
DEM Elevation Fetcher
=====================
Récupère l'altitude (Z) pour un point ou une grille de points lat/lon
via l'API Open-Elevation (SRTM 30m, mondial, sans clé API).

Utilisation :
    fetcher = DEMFetcher()
    
    # Un seul point
    z = fetcher.get_elevation(45.832, 6.865)  # Chamonix
    
    # Grille de points (pour un terrain 3D)
    grid = fetcher.get_elevation_grid(
        lat_min=45.80, lat_max=45.86,
        lon_min=6.84,  lon_max=6.90,
        resolution=20  # 20x20 points
    )
    # grid = {'lats': ..., 'lons': ..., 'elevations': np.ndarray (20x20)}
"""

import time
from logging_handler import  logger
import numpy as np
import requests


class DEMFetcher:
    """
    Récupère les données d'élévation SRTM (30m) via Open-Elevation.
    Mondial, sans clé API, sans cache.

    Parameters
    ----------
    timeout : int       Timeout HTTP en secondes (défaut 30)
    max_points : int    Nombre max de points par requête (défaut 100)
                        Open-Elevation accepte jusqu'à ~500 points par POST
    """

    API_URL = "https://api.open-elevation.com/api/v1/lookup"

    def __init__(self, timeout: int = 30, max_points: int = 100):
        self._timeout    = timeout
        self._max_points = max_points
        self._session    = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_elevation(self, lat: float, lon: float) -> float | None:
        """
        Retourne l'élévation en mètres pour un point unique.
        Retourne None si la requête échoue.
        """
        results = self._fetch_batch([{"latitude": lat, "longitude": lon}])
        if results:
            return results[0]
        return None

    def get_elevation_grid(
        self,
        lat_min: float, lat_max: float,
        lon_min: float, lon_max: float,
        resolution: int = 30,
    ) -> dict | None:
        """
        Retourne une grille d'élévations pour une zone rectangulaire.

        Parameters
        ----------
        lat_min, lat_max : float    Bornes latitude
        lon_min, lon_max : float    Bornes longitude
        resolution : int            Nombre de points sur chaque axe (défaut 30)

        Returns
        -------
        dict avec :
            'lats'       : np.ndarray (resolution,)
            'lons'       : np.ndarray (resolution,)
            'elevations' : np.ndarray (resolution, resolution)  en mètres
            'lat_grid'   : np.ndarray (resolution, resolution)
            'lon_grid'   : np.ndarray (resolution, resolution)
        """

        lats = np.linspace(lat_min, lat_max, resolution)
        lons = np.linspace(lon_min, lon_max, resolution)

        lon_grid, lat_grid = np.meshgrid( lons, lats, indexing='ij')  # A CHECKER

        # Aplatir pour envoyer en batch

        points = [
            {"latitude": float(lat_grid[i, j]), "longitude": float(lon_grid[i, j])}
            for i in range(resolution)
            for j in range(resolution)
        ]

        logger.info(f"[DEMFetcher] Requesting {len(points)} points"
                    f"({lat_min:.3f}-{lat_max:.3f}, {lon_min:.3f}-{lon_max:.3f})")

        elevations_flat = self._fetch_all(points)
        if elevations_flat is None:
            return None

        elevations = np.array(elevations_flat, dtype=float).reshape(resolution, resolution)

        return {
            "lats":       lats,
            "lons":       lons,
            "elevations": elevations,
            "lat_grid":   lat_grid,
            "lon_grid":   lon_grid,
        }

    def get_elevation_along_track(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
    ) -> np.ndarray | None:
        """
        Retourne les élévations le long d'une trace GPS.

        Parameters
        ----------
        lats, lons : array-like     Coordonnées de la trace

        Returns
        -------
        np.ndarray d'élévations (même longueur que lats/lons)
        """
        points = [
            {"latitude": float(lat), "longitude": float(lon)}
            for lat, lon in zip(lats, lons)
        ]
        results = self._fetch_all(points)
        if results is None:
            return None
        return np.array(results, dtype=float)

    # ------------------------------------------------------------------
    # Requêtes HTTP internes
    # ------------------------------------------------------------------

    def _fetch_all(self, points: list) -> list | None:
        """
        Envoie les points en plusieurs batches si nécessaire.
        Retourne la liste des élévations dans le même ordre.
        """
        results = []
        batches = [
            points[i:i + self._max_points]
            for i in range(0, len(points), self._max_points)
        ]

        for idx, batch in enumerate(batches):
            logger.debug(f"[DEMFetcher] Batch {idx+1}/{len(batches)} ({len(batch)} pts)")
            elevs = self._fetch_batch(batch)
            if elevs is None:
                return None
            results.extend(elevs)

            # Pause légère entre les batches pour ne pas surcharger l'API
            if idx < len(batches) - 1:
                time.sleep(0.3)

        return results

    def _fetch_batch(self, points: list) -> list | None:
        """
        Envoie un batch de points à l'API et retourne les élévations.
        """
        payload = {"locations": points}
        try:
            resp = self._session.post(
                self.API_URL,
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return [r["elevation"] for r in data["results"]]

        except requests.exceptions.Timeout:
            logger.warning("[DEMFetcher] Timeout error ")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("[DEMFetcher] No internet connexion. ")
            return None
        except Exception as exc:
            logger.warning(f"[DEMFetcher] API error : {exc}")
            return None

