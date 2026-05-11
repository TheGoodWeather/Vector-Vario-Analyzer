# MonApp.spec
import sys
from pathlib import Path
from PyInstaller.building.splash import Splash
sys.path.insert(0, '.')   # ajoute src/ au path pour trouver constants.py
from constants import SOFTWARE_VERSION

block_cipher = None

a = Analysis(
    ['main.py'],                          # point d'entrée
    pathex=['src'],                           # PyInstaller cherche aussi dans src/
    binaries=[],
    datas=[
        ('gui/*.ui', 'gui'),              # fichiers .ui
        ('gui/icons/*', 'gui/icons'),  
		('../requirements.txt', '.'),      # ← à la racine du bundle
		('../LICENSE.txt', '.'),               # ← à la racine du bundl# icônes
    ],
    hiddenimports=[],
    excludes=[
        'IPython',
        'pytest',
        'sphinx',
        'matplotlib',
        'matplotlib.backends',
        'pyqtgraph.widgets.MatplotlibWidget',
        'h5py',
        'numba',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


splash = Splash(
    'gui/icons/logo.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=f'Vector Vario Analyzer {SOFTWARE_VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                            # pas de console (app GUI)
    icon='gui/icons/app_icon.ico',        # icône .ico obligatoire sur Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name=f'Vector Vario Analyzer {SOFTWARE_VERSION}',
)