# -*- mode: python ; coding: utf-8 -*-
#pyinstaller spec; tested on mac

hiddenimports=[
        'uvicorn',
        'uvicorn.lifespan.off',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.protocols.websockets_impl',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.http',
        'uvicorn.protocols',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.loops.uvloop',
        'uvicorn.loops',
        'uvicorn.logging',
        'httptools',
        'uvloop',
        'websockets',
        'wsproto',
        'watchgod',
        'asgiref',
        'asgiref.wsgi',
        'app'
    ]

datas=[
    ('asgi.py', '.'),
    ('templates', 'templates'),
    ('static', 'static'),
    ('certs/cert.pem', 'certs'),
    ('certs/key.pem', 'certs'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
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
    a.binaries,
    a.datas,
    [],
    name='wokabetrena',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)