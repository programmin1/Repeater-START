# Repeater-START
Repeater START - Showing The Amateur Repeaters Tool

This tool displays all the repeaters available through the repeater listing at https://hearham.com/repeaters

Support for searching for a WhatThreeWords Position, a mountain or peak on Openstreetmap, or finding your current location, is included.

You can download this program for recent Ubuntu and Debian based systems at https://sourceforge.net/projects/repeater-start/
Simply download and open the file, select install. OR, if you prefer command line:

```
sudo dpkg -i ./repeater-start_0.4_all.deb
```


# Development
This is written in Python for GTK+. If you run it you should have:
* Geoclue introspection - for getting your location easily.
* libosmgpsmap introspection - for the maps widget display.

Then just run "python3 repeaterstart.py"
