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
    hiddenimports=[
        'pyqtgraph',
        'scipy._lib.array_api_compat.numpy.fft',
        'sklearn.utils._cython_blas',
        'MetPy',
        'pyproj',
    ],
    excludes=[
        'tkinter',
        'IPython',
        'jupyter',
        'pytest',
        'sphinx',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Vector Vario Software',
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
    name='Vector Vario Software',
)