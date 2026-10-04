Name:           repeaterSTART
Version:        1.1.0
Release:        1%{?dist}
Summary:        Repeater-START (Showing The Amateur-radio Repeaters Tool) is a tool to find local repeaters on a topo map. Works online or offline.
License:        GPL-2.0-or-later
URL:            https://hearham.com/repeaters
BuildArch:      noarch

Requires:       python3, python3-gobject, osm-gps-map-gobject, geoclue2-libs

%description
Repeater-START - Showing The Amateur Repeaters Tool.
This tool displays all the repeaters available through the repeater listing at https://hearham.com/repeaters
Support for searching for a Maidenhead-grid-square coordinate, WhatThreeWords Position, a mountain or peak on Openstreetmap, repeater frequency/IRLP node, or finding your current location, is included.

%build
# Nothing to compile - pure Python.

%install
rm -rf %{buildroot}

install -d %{buildroot}%{_datadir}/repeater-START
cp -r src/* %{buildroot}%{_datadir}/repeater-START/

install -Dm644 resources/repeaterstart.desktop \
    %{buildroot}%{_datadir}/applications/repeaterstart.desktop

install -Dm644 resources/repeaterSTART.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/repeaterSTART.svg

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/%{name} << 'EOF'
#!/bin/sh
#Starts up repeater-start
cd /usr/share/repeater-START/
./repeaterstart.py $@
EOF
chmod 755 %{buildroot}%{_bindir}/%{name}

%files
%attr(0755,root,root) %{_bindir}/%{name}
%{_bindir}/%{name}
%{_datadir}/repeater-START/
%{_datadir}/applications/repeaterstart.desktop
%{_datadir}/icons/hicolor/scalable/apps/repeaterSTART.svg
%license LICENSE
%doc README.md

%changelog
* Fri Jul 03 2026 Luke
- Initial Fedora/Red Hat build.
