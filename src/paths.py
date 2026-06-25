# -*- coding: utf-8 -*-
"""
Centralise la gestion des chemins pour gérer correctement les deux modes :

- mode dev      : `python main.py` lancé depuis n'importe quel répertoire
- mode PyInstaller (onedir) + Inno Setup : VVA.exe installé avec, à côté :
      _internal/
      flight/
      log/
      uninstall/
      VVA.exe

Deux notions différentes :

1. "resource root" : où sont les ressources EMBARQUÉES en lecture seule
   (dossier gui/, modèles 3D, icônes, LICENSE.txt, requirements.txt, ...)
       - dev        -> dossier contenant ce fichier (src/)
       - PyInstaller -> sys._MEIPASS (dossier d'extraction temporaire)

2. "app root" : où vit l'exécutable / le script, utilisé comme base pour
   les données ÉCRITES par l'utilisateur (flight/, log/, ...)
       - dev        -> dossier contenant ce fichier (src/), donc à côté
                        de main.py, quel que soit le cwd
       - PyInstaller -> dossier contenant VVA.exe (sys.executable.parent)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

APP_NAME = "Vector Vario Analyzer"

# ---------------------------------------------------------------------------
# App root : utilisé pour les dossiers "flight", "log", etc.
# ---------------------------------------------------------------------------
def get_app_root() -> Path:
    """
    Base à utiliser pour tout ce qui doit être ÉCRIT par l'app
    (flight/, log/, ...). Dépend de la plateforme en mode frozen.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            # Ne JAMAIS écrire dans le bundle .app (Contents/MacOS/...).
            return Path.home() / "Library" / "Application Support" / APP_NAME
        # Windows / Linux : sys.executable = .../Vector Vario Analyzer/VVA.exe
        return Path(sys.executable).resolve().parent
    # __file__ = .../src/paths.py -> .parent = .../src/  (== dossier de main.py)
    return Path(__file__).resolve().parent
 



# ---------------------------------------------------------------------------
# Ressources embarquées en lecture seule
# ---------------------------------------------------------------------------
def resource_path(relative_path: str) -> Path:
    """
    Ressources embarquées qui vivent à côté de main.py en dev, et qui sont
    copiées telles quelles dans le bundle PyInstaller via
    `datas=[('gui', 'gui'), ...]` (gui/, models, icônes...).
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / relative_path


def project_root_resource_path(relative_path: str) -> Path:
    """
    Fichiers copiés depuis la racine du projet (un niveau au-dessus de src/)
    via `datas=[('../LICENSE.txt', '.'), ('../requirements.txt', '.'),
    ('../CHANGELOG.md', '.'), ...]`.

    En PyInstaller, ils se retrouvent à la racine de _MEIPASS, donc même
    base que `resource_path` une fois bundlé.
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base / relative_path


# ---------------------------------------------------------------------------
# Dossier de données "flight"
# ---------------------------------------------------------------------------
def flight_dir() -> Path:
    """
    Retourne le dossier 'flight', créé si besoin :
      - dev         : à côté de main.py (peu importe le cwd)
      - PyInstaller : à côté de VVA.exe

    Si l'emplacement n'est pas inscriptible (ex: install dans
    "Program Files" sans droits d'écriture), on retombe sur un dossier
    temporaire utilisateur.
    """
    path = get_app_root() / "flight"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.touch()
        probe.unlink()
    except OSError:
        path = Path(tempfile.gettempdir()) / "Vector Vario Analyzer" / "flight"
        path.mkdir(parents=True, exist_ok=True)
    return path


def open_flight_folder():
    """
    Ouvre le dossier flight dans l'explorateur de fichiers.
    """
    folder = flight_dir()
    if sys.platform.startswith("win"):
        os.startfile(folder)

    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])

    else:  # Linux
        subprocess.Popen(["xdg-open", str(folder)])