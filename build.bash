# build deploy directory:
PATH=/mingw64/bin:$PATH
/mingw64/bin/pyinstaller --noconfirm ./repeaterstart.spec
echo "Cleaning up."
rm -rf dist/repeaterstart/share/locale
rm -rf dist/repeaterstart/share/icons/hicolor
rm -rf dist/repeaterstart/share/icons/Adwaita/symbolic
rm -rf dist/repeaterstart/share/icons/Adwaita/512x512
rm -rf dist/repeaterstart/share/icons/Adwaita/256x256
rm -rf dist/repeaterstart/share/icons/Adwaita/96x96
rm -rf dist/repeaterstart/share/icons/Adwaita/64x64
rm -rf dist/repeaterstart/share/icons/Adwaita/48x48
rm -rf dist/repeaterstart/share/icons/Adwaita/32x32
rm -rf dist/repeaterstart/share/icons/Adwaita/22x22/devices
rm -rf dist/repeaterstart/share/icons/Adwaita/22x22/places
rm -rf dist/repeaterstart/share/icons/Adwaita/22x22/status
rm -rf dist/repeaterstart/share/icons/Adwaita/22x22/emblems
rm -rf dist/repeaterstart/share/icons/Adwaita/scalable/mimetypes
rm -rf dist/repeaterstart/share/icons/Adwaita/scalable/devices
rm -rf dist/repeaterstart/share/icons/Adwaita/cursors

rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/8x8
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/16x16/mimetypes
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/16x16/status
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/22x22/mimetypes
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/22x22/status
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/24x24/mimetypes
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/24x24/status
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/32x32/mimetypes
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/32x32/status
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/48x48/mimetypes
rm -rf dist/repeaterstart/share/icons/AdwaitaLegacy/48x48/status

rm -rf dist/repeaterstart/share/icons/Adwaita/16x16/devices
rm -rf dist/repeaterstart/share/icons/Adwaita/16x16/places
rm -rf dist/repeaterstart/share/icons/Adwaita/16x16/status
rm -rf dist/repeaterstart/share/icons/Adwaita/16x16/emblems
rm -rf dist/repeaterstart/share/icons/Adwaita/16x16/emotes

#Here's a hint, run the .exe, delete dll and if it does not give an "in use" error it is not in use!
rm dist/repeaterstart/libaom.dll
rm dist/repeaterstart/libSvtAv1Enc-4.dll
rm dist/repeaterstart/librav1e.dll
rm dist/repeaterstart/libgnutls-30.dll
rm dist/repeaterstart/libdav1d-7.dll
rm dist/repeaterstart/libp11-kit-0.dll
rm dist/repeaterstart/libimagequant.dll
rm dist/repeaterstart/libyuv.dll
rm dist/repeaterstart/libgmp-10.dll
rm dist/repeaterstart/libngtcp2-16.dll
rm dist/repeaterstart/libnettle-8.dll
rm dist/repeaterstart/libssh2-1.dll
rm dist/repeaterstart/libgomp-1.dll
rm dist/repeaterstart/libcurl-4.dll
rm dist/repeaterstart/libtasn1-6.dll
rm dist/repeaterstart/liblcms2-2.dll
rm dist/repeaterstart/libhogweed-6.dll
rm dist/repeaterstart/libavif-16.dll
rm dist/repeaterstart/libwebpdemux-2.dll

rm -rf dist/repeaterstart/PIL

echo "Cleaned - now run NSIS"