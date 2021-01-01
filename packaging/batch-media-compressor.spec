# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['../main.py'],
             pathex=[],
             binaries=[],
             datas=[('../assets/mainwindow.ui', 'assets'), ('../assets/pie_logo.ico', 'assets'), ('../assets/pie_logo.png', 'assets')],
             hiddenimports=['PySide2.QtXml'],
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
          name='Batch Media Compressor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='../assets/pie_logo.ico',
          version='win_exe_version_info.txt')
app = BUNDLE(exe,
             name='Batch Media Compressor.app',
             icon='../assets/pie_logo.icns',
             bundle_identifier='com.twohandapps.bmc',
             info_plist={
                'LSUIElement': True,
                'CFBundleDisplayName': 'Batch Media Compressor',
                'CFBundleShortVersionString': '1.0.0',
                'CFBundleVersion': '1.0.0',
                'NSHumanReadableCopyright': 'Copyright © 2020 Two Hand Apps. All rights reserved.',
                'LSApplicationCategoryType': 'public.app-category.photography',
                'NSRequiresAquaSystemAppearance': True # TODO: Support dark mode 
             }
            )
