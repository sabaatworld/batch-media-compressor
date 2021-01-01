#!/usr/bin/env bash

set -x
set -e

pyinstaller --noconfirm 'packaging/batch-media-compressor.spec'
codesign --entitlements 'packaging/app.entitlements' -s 'Batch Media Compressor Code Signing' 'dist/Batch Media Compressor.app'
dmgbuild -s 'packaging/dmgbuild_settings.py' 'Batch Media Compressor' 'dist/Batch Media Compressor.dmg'
