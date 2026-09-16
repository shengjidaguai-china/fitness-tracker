"""
PyInstaller 打包脚本 — 健身监控 v9.0 (精简版)
排除 torch/scipy/numba/pyarrow 等无关大依赖
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 排除与健身软件无关的大型依赖
EXCLUDE_MODULES = [
    "torch",
    "torchvision",
    "torchaudio",
    "triton",
    "tensorflow",
    "tensorboard",
    "scipy",
    "numba",
    "llvmlite",
    "pyarrow",
    "sqlalchemy",
    "cryptography",
    "IPython",
    "jupyter",
    "notebook",
    "ipykernel",
    "pytest",
    "black",
    "mypy",
    "ruff",
    "win32com",
    "pythoncom",
    "pywintypes",
    "jedi",
    "parso",
    "pygments",
    "rich",
    "wcwidth",
    "onnxruntime",
    "gi",
    "pandas.tests",
    "numpy.tests",
    "matplotlib.tests",
]

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name",
    "健身监控v9.0",
    "--distpath",
    os.path.join(HERE, "dist"),
    "--workpath",
    os.path.join(HERE, "build"),
    "--specpath",
    HERE,
    # 资源: 体重体脂监控目录 (GIF/JSON/MD计划/体测数据/AI教练数据)
    "--add-data",
    "体重体脂监控" + os.pathsep + "体重体脂监控",
]

# 打包微软雅黑字体 (解决 matplotlib 中文乱码)
msyh = r"C:\Windows\Fonts\msyh.ttc"
if os.path.exists(msyh):
    cmd.extend(["--add-data", msyh + os.pathsep + "fonts"])
    print(f"[BUILD] 已添加微软雅黑字体: {msyh}")

cmd += [
    # 图标: 与 健身监控v9.0.spec 保持一致, 否则 exe 无图标且两个入口行为不同
    '--icon', os.path.join(HERE, 'fitness_icon.ico'),
    # PySide6: 只收集实际使用的模块 (QtCore/QtGui/QtWidgets 自动发现)
    # matplotlib QtAgg backend 需要 QtSvg
    "--collect-submodules",
    "PySide6.QtSvg",
    "--collect-submodules",
    "PySide6.QtSvgWidgets",
    # 显式声明本地模块
    "--hidden-import",
    "ai_coach_engine",
    "--hidden-import",
    "fitness_modules",
    "--hidden-import",
    "fitness_pkg",
    "--paths",
    HERE,
]

# 图标缺失时提前报错, 而不是打包出无图标的 exe
icon_path = os.path.join(HERE, 'fitness_icon.ico')
if not os.path.exists(icon_path):
    print('[WARN] 未找到 fitness_icon.ico, 将跳过图标')

# 排除不需要的 PySide6 子模块 (大幅减小体积)
PYSIDE6_EXCLUDE = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtAsyncio",
    "PySide6.QtAxContainer",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtConcurrent",
    "PySide6.QtDBus",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickTest",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtXml",
    "PySide6.scripts",
    "PySide6.support",
]

# 添加排除模块
for mod in EXCLUDE_MODULES + PYSIDE6_EXCLUDE:
    cmd.extend(["--exclude-module", mod])

cmd.append("体脂体重监控_完整版.py")

print("[BUILD] 启动 PyInstaller 精简打包...")
print("[BUILD] 排除模块:", ", ".join(EXCLUDE_MODULES[:8]), "...")
print()

result = subprocess.run(cmd, cwd=HERE)

if result.returncode == 0:
    out = os.path.join(HERE, "dist", "健身监控v9.0", "健身监控v9.0.exe")
    if os.path.exists(out):
        size_mb = os.path.getsize(out) / 1024 / 1024
        total = (
            sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.dirname(out)) for f in fs)
            / 1024
            / 1024
        )
        print()
        print(f"[OK] 打包成功! exe: {size_mb:.1f} MB, 总体积: {total:.1f} MB")
        print("[OK] 输出:", out)
    else:
        print("[FAIL] exe 未生成")
        sys.exit(1)
else:
    print()
    print("[FAIL] 打包失败, 返回码:", result.returncode)
    sys.exit(result.returncode)
