# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['YACPcal.py'],
             pathex=[],
             binaries=[],
             datas=[('icon.ico','.')],
             hiddenimports=['can.interfaces.pcan','can.interfaces.kvaser','can.interfaces.ixxat','can.interfaces.vector','pyqtgraph.*'],
             hookspath=[],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='YACPcal',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
		  icon='icon.ico',
          console=True )
