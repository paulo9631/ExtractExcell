# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('modules', 'modules'), ('modules/DB', 'modules/DB'), ('modules/ui', 'modules/ui'), ('modules/core', 'modules/core'), ('alunos.db', '.'), ('config.json', '.'), ('matricula_template.png', '.'), ('modelo_gabarito_base.pdf', '.'), ('pagina72dpi.png', '.'), ('template_gabarito_10.png', '.'), ('template_gabarito_20.png', '.'), ('template_cabecalho.png', '.'), ('credentials.json', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
