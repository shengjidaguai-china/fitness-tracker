# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 健身监控 v9.0 打包配置

单目录模式 (onedir): 启动快、数据文件可独立更新
"""

import os

block_cipher = None

a = Analysis(
    ['体脂体重监控_完整版.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('体重体脂监控', '体重体脂监控'),
        ('Lzheng-fitness', 'Lzheng-fitness'),
        ('fitness_icon.ico', '.'),
    ],
    hiddenimports=[
        'ai_coach_engine',
        'fitness_modules',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'matplotlib.backends.backend_qtagg',
        'pandas',
        'numpy',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'IPython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='fitness_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='健身监控v9.0',
)
