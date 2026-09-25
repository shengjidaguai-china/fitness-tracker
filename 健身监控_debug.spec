# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 监控调试版 (保留窗口控制台, 便于排查启动异常)

与 健身监控v9.0.spec 的差异仅在于 console=True 与程序名,
其余分析参数一致, 避免多个 spec 各自漂移导致「某个 spec 能打包、另一个不能」。
"""
import os
from PyInstaller.utils.hooks import collect_submodules

HERE = os.path.abspath('.')
hiddenimports = ['ai_coach_engine', 'fitness_modules', 'fitness_pkg', 'fitness_pkg.auto_plan', 'fitness_pkg.auto_plan_page']
hiddenimports += collect_submodules('PySide6.QtSvg')
hiddenimports += collect_submodules('PySide6.QtSvgWidgets')

datas = [('体重体脂监控', '体重体脂监控')]
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
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='健身监控v9.0_debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='健身监控v9.0_debug',
)
