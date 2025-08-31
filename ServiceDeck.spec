# -*- mode: python ; coding: utf-8 -*-

# Importa o 'os' para manipulação de caminhos
import os

block_cipher = None

# O nome do seu executável e da pasta final
APP_NAME = 'ServiceDeck'

# Caminho para os assets
assets_path = os.path.join('app', 'assets')
icon_file = os.path.join(assets_path, 'icon.png')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Adicionamos os arquivos que queremos na pasta final do build.
    # O formato é ('arquivo_origem', 'pasta_destino_no_build')
    datas=[
        (assets_path, 'app/assets'),
        (icon_file, '.'),
        ('setup.sh', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=APP_NAME,
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
    icon=icon_file,
)

# --- ESTA É A SEÇÃO CORRIGIDA E ADICIONADA ---
# O COLLECT junta o executável (exe), as dependências (a.binaries, etc)
# e os nossos dados (a.datas) na pasta final.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME  # Define o nome da pasta final em 'dist/'
)
