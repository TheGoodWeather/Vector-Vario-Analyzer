# MonApp.spec
import sys
from pathlib import Path

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
        'tkinter',
        'IPython',
        'jupyter',
        'pytest',
        'sphinx',
        'matplotlib',
        'matplotlib.backends',
        'pyqtgraph.widgets.MatplotlibWidget',
        'pyqtgraph.flowchart',
        'pyqtgraph.parametertree',
        'h5py',
        'OpenGL',
        'notebook',
        'PIL',
        'numba',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Vector Vario Analyzer',
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
    name='Vector Vario Analyzer',
)