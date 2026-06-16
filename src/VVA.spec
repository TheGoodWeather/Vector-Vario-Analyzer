# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

sys.path.insert(0, '.')
from constants import SOFTWARE_VERSION

block_cipher = None


def safe_copy_metadata(package):
    try:
        return copy_metadata(package)
    except Exception:
        return []


scipy_hiddenimports = (
    collect_submodules('scipy._lib')
    + collect_submodules('scipy.interpolate')
    + collect_submodules('scipy.linalg')
    + collect_submodules('scipy.sparse')
    + collect_submodules('scipy.special')
)
dynamic_hiddenimports = (
    collect_submodules('pyqtgraph.opengl')
    + collect_submodules('trimesh')
)
scipy_datas = collect_data_files('scipy', excludes=['**/tests/**', '**/test/**'])
scipy_binaries = collect_dynamic_libs('scipy')
package_metadata = (
    safe_copy_metadata('numpy')
    + safe_copy_metadata('scipy')
    + safe_copy_metadata('trimesh')
    + safe_copy_metadata('PyOpenGL')
    + safe_copy_metadata('packaging')
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        *scipy_binaries,
    ],
    datas=[
        ('gui', 'gui'),
        ('../requirements.txt', '.'),
        ('../LICENSE.txt', '.'),
        ('../CHANGELOG.md', '.'),
        *scipy_datas,
        *package_metadata,
    ],
    hiddenimports=[
        'pyqtgraph',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'OpenGL',
        'scipy',
        'scipy.interpolate',
        'scipy._lib.messagestream',
        'trimesh',
        *scipy_hiddenimports,
        *dynamic_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'IPython',
        'jupyter',
        'pytest',
        'sphinx',
        'matplotlib',
        'matplotlib.backends',
        'pyqtgraph.widgets.MatplotlibWidget',
        'h5py',
        'numba',
    ],
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/icons/app_icon.ico',
    manifest='app.manifest',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Vector Vario Analyzer',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Vector Vario Analyzer.app',
        icon='gui/icons/app_icon.icns',
        bundle_identifier=f'com.vectorvario.vectorvarioanalyzer.{SOFTWARE_VERSION}',
    )
