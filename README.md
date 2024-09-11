# Repeater-START
Repeater START - Showing The Amateur Repeaters Tool

This tool displays all the repeaters available through the repeater listing at https://hearham.com/repeaters

Support for searching for a Maidenhead-grid-square coordinate, WhatThreeWords Position, a mountain or peak on Openstreetmap, repeater frequency/IRLP node, or finding your current location, is included.

You can download this program for Windows 8, Windows 10, recent Ubuntu and Debian based systems at https://sourceforge.net/projects/repeater-start/
Simply download and open the file, select install. OR, if you prefer command line:

```
sudo dpkg -i ./repeater-start_0.7_all.deb
```


# Development

Linux computer/phone:

This is written in Python for GTK+. If you run it you should have:
* Geoclue introspection - for getting your location easily.
* libosmgpsmap introspection - for the maps widget display.

Then just run "python3 repeaterstart.py"

Windows:

Much of this will run on Windows. Check out the "windows" branch which has Geoclue locate-me button removed, and runs in msys2.

```
pacman -S mingw-w64-x86_64-osm-gps-map
pacman -S python3
pacman -S mingw-w64-x86_64-python-gobject
```

are requirements, for the map library and Python. Run with mingw python in the msys2 console:

```
cd src
/mingw64/bin/python3.exe ./repeaterstart.py
```


Android:

[<img src="https://hearham.com/img/GP.png"
     alt="Get it on Google Play"
     height="80">](https://play.google.com/store/apps/details?id=com.hearham.repeaterstartpremium)


[![Liberapay](https://img.shields.io/liberapay/patrons/deepdaikon.svg?logo=liberapay)](https://liberapay.com/Programmin/)
[<img src="https://www.ko-fi.com/img/githubbutton_sm.svg" alt="Ko-fi" height="20">](https://ko-fi.com/hearham)
