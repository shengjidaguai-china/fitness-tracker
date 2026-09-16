# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

HERE = os.path.abspath('.')
hiddenimports = ['ai_coach_engine', 'fitness_modules', 'fitness_pkg', 'fitness_pkg.science']
hiddenimports += collect_submodules('PySide6.QtSvg')
hiddenimports += collect_submodules('PySide6.QtSvgWidgets')

datas = [('体重体脂监控', '体重体脂监控')]
# Include Microsoft YaHei for matplotlib Chinese rendering when present on the build machine
msyh = r'C:/Windows/Fonts/msyh.ttc'
if os.path.exists(msyh):
    datas.append((msyh, 'fonts'))

a = Analysis(
    ['体脂体重监控_完整版.py'],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'triton', 'tensorflow', 'tensorboard', 'scipy', 'numba', 'llvmlite', 'pyarrow', 'sqlalchemy', 'cryptography', 'IPython', 'jupyter', 'notebook', 'ipykernel', 'pytest', 'black', 'mypy', 'ruff', 'win32com', 'pythoncom', 'pywintypes', 'jedi', 'parso', 'pygments', 'rich', 'wcwidth', 'onnxruntime', 'gi', 'pandas.tests', 'numpy.tests', 'matplotlib.tests', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender', 'PySide6.QtAsyncio', 'PySide6.QtAxContainer', 'PySide6.QtBluetooth', 'PySide6.QtCharts', 'PySide6.QtConcurrent', 'PySide6.QtDBus', 'PySide6.QtDataVisualization', 'PySide6.QtDesigner', 'PySide6.QtGraphs', 'PySide6.QtGraphsWidgets', 'PySide6.QtHelp', 'PySide6.QtHttpServer', 'PySide6.QtLocation', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtNetworkAuth', 'PySide6.QtNfc', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPositioning', 'PySide6.QtPrintSupport', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickControls2', 'PySide6.QtQuickTest', 'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSensors', 'PySide6.QtSerialBus', 'PySide6.QtSerialPort', 'PySide6.QtSpatialAudio', 'PySide6.QtSql', 'PySide6.QtStateMachine', 'PySide6.QtTest', 'PySide6.QtTextToSpeech', 'PySide6.QtUiTools', 'PySide6.QtWebChannel', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebSockets', 'PySide6.QtWebView', 'PySide6.QtXml', 'PySide6.scripts', 'PySide6.support'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='健身监控v9.0',
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
    icon='fitness_icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='健身监控v9.0',
)
