"""GTK4 settings, preserving the existing settings.ini format."""
import configparser
import math
import os
import tempfile
import threading
import urllib.request
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from CsvRepeaterListing import CsvRepeaterListing
from RepeaterStartCommon import userFile
from GtkSupport import margins, message


class SettingsDialog:
    def __init__(self, parentWin):
        self.parentWin = parentWin
        self.dialog = None
        self.config = configparser.ConfigParser()
        self.config.read(userFile('settings.ini'))
        defaults = {
            'ViewOptions': {'unitsLength': 'mi', 'filterMin': '', 'filterMax': ''},
            'DownloadOptions': {'mobile': 'False'}, 'Diagnostics': {},
            'Repeaters': {'Hearham Amateur Radio Repeaters': 'https://hearham.com/api/repeaters/v1'},
        }
        for section, values in defaults.items():
            if section not in self.config:
                self.config[section] = values
            elif section != 'Repeaters':
                for key, value in values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value

    def writeSettings(self):
        # Never replace DownloadOptions: doing so erased licenseKEY previously.
        with open(userFile('settings.ini'), 'w') as outfile:
            self.config.write(outfile)

    def getAllowMobile(self):
        return self.config.getboolean('DownloadOptions', 'mobile', fallback=False)

    def getMinFilter(self):
        try:
            return float(self.config['ViewOptions']['filterMin'])
        except ValueError:
            return -1

    def getMaxFilter(self):
        try:
            return float(self.config['ViewOptions']['filterMax'])
        except ValueError:
            return math.inf

    def getUnit(self):
        return self.config['ViewOptions']['unitsLength']

    def getShown(self):
        return self.config['Repeaters']

    def show(self):
        if self.dialog:
            self.dialog.present()
            return
        self.dialog = Gtk.Window(title='Settings', transient_for=self.parentWin,
                                 modal=True, destroy_with_parent=True,
                                 default_width=440, default_height=470)
        self.dialog.connect('close-request', self.onClosed)
        box = margins(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12), 12)
        self.dialog.set_child(box)
        units = Gtk.Box(spacing=12)
        units.append(Gtk.Label(label='Distance units'))
        self.miles = Gtk.CheckButton(label='Miles')
        self.km = Gtk.CheckButton(label='Kilometers')
        self.km.set_group(self.miles)
        (self.km if self.getUnit() == 'km' else self.miles).set_active(True)
        units.append(self.miles)
        units.append(self.km)
        box.append(units)
        presets = Gtk.Box(spacing=6)
        presets.append(Gtk.Label(label='Frequency filter'))
        self.minimum = Gtk.Entry(text=self.config['ViewOptions']['filterMin'], placeholder_text='Min MHz', hexpand=True)
        self.maximum = Gtk.Entry(text=self.config['ViewOptions']['filterMax'], placeholder_text='Max MHz', hexpand=True)
        for name, low, high in [('All', '', ''), ('VHF', '144', '148'), ('UHF', '420', '450')]:
            button = Gtk.Button(label=name)
            button.connect('clicked', lambda _, a=low, b=high: (self.minimum.set_text(a), self.maximum.set_text(b)))
            presets.append(button)
        box.append(presets)
        limits = Gtk.Box(spacing=6)
        limits.append(self.minimum)
        limits.append(self.maximum)
        box.append(limits)
        self.mobile = Gtk.CheckButton(label='Download repeater updates on mobile data', active=self.getAllowMobile())
        box.append(self.mobile)
        box.append(Gtk.Label(label='Repeater sources', xalign=0))
        self.repolist = Gtk.ListBox()
        scrolled = Gtk.ScrolledWindow(child=self.repolist, vexpand=True, min_content_height=120)
        box.append(scrolled)
        self._fill_sources()
        actions = Gtk.Box(spacing=6)
        for label, callback in [('Add', self.addRpt), ('Remove', self.rmRpt), ('Properties', self.propertyRpt)]:
            button = Gtk.Button(label=label)
            button.connect('clicked', callback)
            actions.append(button)
        box.append(actions)
        close = Gtk.Button(label='Save and close')
        close.connect('clicked', self.onClosed)
        box.append(close)
        self.dialog.present()

    def _fill_sources(self):
        while (row := self.repolist.get_first_child()) is not None:
            self.repolist.remove(row)
        for name, url in self.getShown().items():
            row = Gtk.ListBoxRow(child=margins(Gtk.Label(label=name, xalign=0), 6))
            row.name, row.url = name, url
            self.repolist.append(row)

    def _edit_source(self, row=None):
        dialog = Gtk.Dialog(title='Repeater source URL', transient_for=self.dialog,
                            modal=True, destroy_with_parent=True)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Save', Gtk.ResponseType.OK)
        entry = Gtk.Entry(text=row.url if row else '', placeholder_text='https://…/repeaters.csv', hexpand=True)
        dialog.get_content_area().append(margins(entry, 12))
        entry.connect('activate', lambda _: dialog.response(Gtk.ResponseType.OK))
        def response(dialog, result):
            url = entry.get_text().strip()
            old_name = row.name if row else None
            dialog.destroy()
            if result != Gtk.ResponseType.OK or not url:
                return
            if not url.startswith(('https://', 'http://')):
                message(self.dialog, 'Enter an HTTP or HTTPS URL for a CSV repeater list.')
                return
            if 'hearham.com/api/repeaters/v1' in url:
                self._source_loaded('Hearham Amateur Radio Repeaters', url, old_name)
                return
            def download():
                filename = None
                try:
                    with urllib.request.urlopen(url, timeout=20) as response:
                        data = response.read()
                    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
                        temp.write(data)
                        filename = temp.name
                    listing = CsvRepeaterListing(filename)
                    if not listing.name:
                        raise ValueError('The CSV must have a Name header.')
                    # Keep a first copy available immediately, also when offline.
                    Path(userFile('rpt-' + listing.name + '.csv')).write_bytes(data)
                    GLib.idle_add(self._source_loaded, listing.name, url, old_name)
                except (OSError, ValueError, IndexError, AttributeError) as error:
                    GLib.idle_add(self._source_failed, str(error))
                finally:
                    if filename:
                        os.unlink(filename)
            threading.Thread(target=download, daemon=True).start()
        dialog.connect('response', response)
        dialog.present()

    def _source_loaded(self, name, url, old_name):
        if old_name and old_name != name:
            self.config['Repeaters'].pop(old_name, None)
        self.config['Repeaters'][name] = url
        self.writeSettings()
        if self.dialog:
            self._fill_sources()
        if not self.parentWin._closing:
            self.parentWin.displayNodes()
        return False

    def _source_failed(self, error):
        if self.dialog:
            message(self.dialog, 'Cannot load repeater list: ' + error)
        return False

    def addRpt(self, *args):
        self._edit_source()

    def rmRpt(self, *args):
        row = self.repolist.get_selected_row()
        if row:
            del self.config['Repeaters'][row.name]
            self._fill_sources()
        else:
            message(self.dialog, 'Select an entry first.')

    def propertyRpt(self, *args):
        row = self.repolist.get_selected_row()
        if row:
            self._edit_source(row)
        else:
            message(self.dialog, 'Select an entry first.')

    def onClosed(self, *args):
        low, high = self.minimum.get_text().strip(), self.maximum.get_text().strip()
        try:
            values = [float(value) for value in (low, high) if value]
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError
            if low and high and float(low) > float(high):
                raise ValueError
        except ValueError:
            message(self.dialog, 'Enter valid frequency limits, with minimum no greater than maximum.')
            return True
        self.config['ViewOptions'].update({'unitsLength': 'km' if self.km.get_active() else 'mi',
                                          'filterMin': low, 'filterMax': high})
        self.config['DownloadOptions']['mobile'] = str(self.mobile.get_active())
        self.writeSettings()
        self.close()
        self.parentWin.displayNodes()
        self.parentWin.downloadBackground()
        return True

    def close(self):
        if self.dialog:
            dialog, self.dialog = self.dialog, None
            dialog.destroy()
