# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules


hiddenimports = (
    collect_submodules("ai")
    + collect_submodules("alembic")
    + collect_submodules("langchain_core")
    + collect_submodules("langchain_ollama")
    + collect_submodules("langchain_openai")
    + collect_submodules("routers")
    + collect_submodules("sqlalchemy")
    + collect_submodules("uvicorn")
)

a = Analysis(
    ["desktop_main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("alembic.ini", "."),
        ("migrations", "migrations"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["mysql", "pymysql", "redis", "rq"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="emovest-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
