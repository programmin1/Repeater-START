# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

binaries = [
    ('C:/msys64/mingw64/lib/gio/modules/libgiognomeproxy.dll', 'lib/gio/modules'),
    ('C:/msys64/mingw64/lib/gio/modules/libgiolibproxy.dll', 'lib/gio/modules'),
    ('C:/msys64/mingw64/lib/gio/modules/libgiognutls.dll', 'lib/gio/modules'),
    ('C:/msys64/mingw64/lib/gio/modules/libgioopenssl.dll', 'lib/gio/modules'),
    # These should be picked up by dependency analysis of the above modules, but don't seem to be...
    ('C:/msys64/mingw64/bin/libgnutls-30.dll', '.'),
    ('C:/msys64/mingw64/bin/libintl-8.dll', '.'),
    ('C:/msys64/mingw64/bin/libproxy-1.dll', '.'),
]
hiddenimports = []
datas = [
     ('C:/msys64/mingw64/lib/gio/modules/giomodule.cache', 'lib/gio/modules'),
    # Collect data (for when code is fixed not to assume current working directory)
    ('src/locateme.svg', '.'),
    ('src/mapbox.svg', '.'),
    ('src/signaltower.svg', '.'),
    ('src/signaltowerdown.svg', '.'),
    ('src/SettingsDialog.glade', '.'),
    ('src/README-WINDOWS.TXT', '.') 
]

a = Analysis(['src/repeaterstart.py'],
             pathex=[],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=['./extra-hooks/'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='repeaterstart',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='resources/repeaterSTART.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='repeaterstart')
