#!/usr/bin/python3
"""
Repeater START - Showing The Amateur Repeaters Tool
(C) 2019-2026 Luke Bryan.
OSMGPSMap examples are (C) Hadley Rich 2008 <hads@nice.net.nz>

This is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License
as published by the Free Software Foundation; version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
"""

import sys
import signal
from time import sleep

#necessary for Ubuntu/GNOME desktop file icon match:
sys.argv[0] = 'repeaterSTART' # GTK reads argv[0] to set WM_CLASS
import os.path
import random
import subprocess
import json
import gettext
import locale
import pathlib
import webbrowser

localedir = pathlib.Path(__file__).resolve().parent / 'lang'
espanol = gettext.translation('repeaterstart', localedir=localedir, languages=['es'], fallback=True)
locale.textdomain('repeaterstart')
if os.environ.get('LANG', '')[:2] == 'es':
    lang = gettext.translation('repeaterstart', localedir=localedir, languages=['es'], fallback=True)
else:
    lang = gettext.NullTranslations()
lang.install()
__ = lang.gettext

localedir_str = str(localedir)
gettext.bindtextdomain('repeaterstart', localedir_str)
locale.bindtextdomain('repeaterstart', localedir_str) 

import gi
gi.require_version("Gtk", "4.0")
gi.require_version('Geoclue', '2.0')
gi.require_version('Shumate', '1.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango
import time
import random
import re
import datetime
from gi.repository import Gio

from gi.repository import Geoclue
import math
import shutil
import urllib.request
import urllib.parse
from math import pi, sin, cos, sqrt, atan2, radians

from RepeaterStartCommon import userFile
from IRLPNode import IRLPNode
from HearHamRepeater import HearHamRepeater
from SettingsDialog import SettingsDialog
from PremiumDialog import PremiumDialog
# from HelpDialog import HelpDialog
from CsvRepeaterListing import CsvRepeaterListing
from MaidenheadLocator import locatorToLatLng, latLongToLocator
from lib import openlocationcode #Plus code. https://github.com/google/open-location-code
from NetworkStatus import isMobileData
from SVGLoaderWindow import SVGLoaderWindow
from threading import Thread
from RepeaterMap import RepeaterMap
from GtkSupport import asset, margins, message, install_css
from zipfile import ZipFile, BadZipFile



class RTLSDRRun:
    """Own only this app's radio/audio processes; never block GTK or killall."""
    def __init__(self, mhz):
        frequency = float(mhz)
        if not math.isfinite(frequency) or frequency <= 0:
            raise ValueError('Select a repeater with a valid receive frequency.')
        self.radio = subprocess.Popen(
            ['rtl_fm', '-M', 'fm', '-f', f'{frequency}M', '-s', '200k',
             '-r', '24k', '-l', '50'], stdout=subprocess.PIPE)
        try:
            self.audio = subprocess.Popen(
                ['play', '-r', '24k', '-t', 'raw', '-e', 's', '-b', '16',
                 '-c', '1', '-V1', '-'], stdin=self.radio.stdout)
        except OSError:
            self.radio.terminate()
            self.radio.wait()
            raise
        finally:
            self.radio.stdout.close()

    def exited(self):
        return self.radio.poll() is not None or self.audio.poll() is not None

    def stop(self):
        processes = (self.radio, self.audio)
        for process in processes:
            if process.poll() is None:
                process.terminate()
        def reap():
            for process in processes:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        Thread(target=reap, daemon=True).start()


class BackgroundDownload(Thread):
    def __init__(self, url, filename):
        super().__init__(daemon=True)
        self.url, self.filename = url, filename
        self.finished = self.success = False

    def run(self):
        import tempfile
        tempname = None
        try:
            with urllib.request.urlopen(self.url, timeout=30) as response:
                with tempfile.NamedTemporaryFile(dir=os.path.dirname(self.filename), delete=False) as temp:
                    tempname = temp.name
                    shutil.copyfileobj(response, temp)
            os.replace(tempname, self.filename)
            tempname = None
            self.after_download()
            self.success = True
        except (OSError, ValueError, BadZipFile) as error:
            print('Download failed:', self.filename, error)
        finally:
            if tempname and os.path.exists(tempname):
                os.unlink(tempname)
            self.finished = True

    def after_download(self):
        pass


class BackgroundDownloadZip(BackgroundDownload):
    def after_download(self):
        target = pathlib.Path(userFile('.hidden')).resolve()
        with ZipFile(self.filename) as archive:
            for member in archive.infolist():
                if not (target / member.filename).resolve().is_relative_to(target):
                    raise ValueError('Archive contains a path outside its destination')
            archive.extractall(target)
        os.unlink(self.filename)


class SearchThread(Thread):
    def __init__(self, query, main):
        #Search and network that must be in a thread or freezes up the window!
        Thread.__init__(self)
        self.query = query
        self.main = main

    def run(self):
        try:
            self.search()
        except (OSError, ValueError, KeyError) as error:
            GLib.idle_add(self.main.search_failed, str(error))

    def search(self):
        srctext = self.query
        #What3Words address has 2 . in it:
        if re.match( r".*\..*\..*", srctext):
            req = urllib.request.Request(
                'https://hearham.com/api/whatthreewords/v1?words=%s' % (urllib.parse.quote(srctext),), 
                data=None,
                headers={
                    'User-Agent': 'Repeater-START/'+self.main.version
                }
            )
            f = urllib.request.urlopen(req, timeout=20)
            objs = json.loads(f.read().decode('utf-8'))
            if not objs:
                GLib.idle_add(self.main.latlon_entry.set_text, 'Invalid what3words.com address.')
                #self.latlon_entry.set_text('Invalid what3words.com address.')
            else:
                GLib.idle_add(self.main.map.set_center, objs['coordinates']['lat'], objs['coordinates']['lng'])
                #self.map.set_center(objs['coordinates']['lat'], objs['coordinates']['lng'])
                #self.latlon_entry.set_text('Map Center: %s %s : %s' % ( latLongToLocator(objs['coordinates']['lat'], objs['coordinates']['lng']), objs['map'], objs['nearestPlace'] ) )
        else:
            # Use new query format https://github.com/osm-search/Nominatim/issues/2121 
            req = urllib.request.Request(
                'https://nominatim.openstreetmap.org/search?q=%s&format=json&limit=50' % (urllib.parse.quote(srctext),), 
                data=None,
                headers={
                    'User-Agent': 'Repeater-START/'+self.main.version
                }
            )
            f = urllib.request.urlopen(req, timeout=20)
            objs = json.loads(f.read().decode('utf-8'))
            if len(objs) == 0:
                try:
                    req = urllib.request.Request(
                        'https://hamcall.dev/'+srctext+'.json', 
                        data=None,
                        headers={
                            'User-Agent':'Repeater-START/'+self.main.version
                        }
                    )
                    f=urllib.request.urlopen(req, timeout=20)#, context=ssl_context)
                    calllookup = json.loads(f.read().decode('utf-8'))
                    print('callsinglookup================')
                    print(calllookup)
                    GLib.idle_add(self.main.map.set_center, float(calllookup['location']['lat']), float(calllookup['location']['lon']))
                    #self.map.set_center(float(calllookup['location']['lat']), float(calllookup['location']['lon']))
                except (urllib.error.URLError,KeyError) as e:
                    print(e)
                    GLib.idle_add(self.main.processSearchResults, [])
            else:
                GLib.idle_add(self.main.processSearchResults, objs)

MAPBOX_URL = 'https://api.mapbox.com/styles/v1/programmin/ck7jtie300p7e1iqi1ow2yvi3/tiles/256/#Z/#X/#Y?access_token=pk.eyJ1IjoicHJvZ3JhbW1pbiIsImEiOiJjazdpaXVpMTEwbHJ1M2VwYXRoZmU3bmw4In0.3UpUBsTCOL5zvvJ1xVdJdg'

class UI(Gtk.ApplicationWindow):
    def __init__(self, application, *, start_background=True):
        super().__init__(application=application)
        self.version = '2.0-beta'
        self.mode = ''
        self._closing = False
        self._map_change_id = 0
        self._timers = []
        self._downloads = []
        self._elevation_windows = {}
        self._context_popover = None
        self.rtllistener = None
        self.playingfreq = None
        self.renderedLat = self.renderedLon = None
        self.allrepeaters = []
        self.GTKListRows, self.searchRows, self.playBtns = [], [], []
        self.set_title('RepeaterSTART GPS Mapper')
        self.set_default_size(700, 700)
        self.set_icon_name('repeaterSTART')
        self.connect('close-request', self.cleanup)
        install_css("""
            .repeater-marker { padding: 0; min-width: 20px; min-height: 20px;
                background: transparent; border: none; box-shadow: none; }
            .repeater-title { font-size: 1.2em; font-weight: bold; }
            .map-crosshair { font-size: 24px; color: #303030; }
            .credits { color: blue; font-size: 12px; outline:none; padding:2px; margin:0px;}
            .gopremium { background:rgb(255, 255, 204); font: Ubuntu Bold 12; font-weight: bold; color: rgb(230, 0, 0); outline: none;
                padding:3px; margin:0px; border-width:0px; border-radius:0px;}
        """)
        self.settingsDialog = SettingsDialog(self)
        self.settingsDialog.getShown()
        self.map = RepeaterMap(repo_uri=MAPBOX_URL)
        self.map.set_center_and_zoom(0, 0, 3)
        try:
            with open(userFile('lastPosition.json')) as infile:
                position = json.load(infile)
            lat, lon, zoom = (float(position[k]) for k in ('lat', 'lon', 'zoom'))
            if all(math.isfinite(v) for v in (lat, lon, zoom)) and -90 <= lat <= 90 and -180 <= lon <= 180:
                self.map.set_center_and_zoom(lat, lon, zoom)
        except (OSError, ValueError, TypeError, KeyError):
            pass
        self.lastLat = self.map.viewport.props.latitude
        self.lastLon = self.map.viewport.props.longitude
        self.towerPic = asset('signaltower.svg')
        self.towerDownPic = asset('signaltowerdown.svg')
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.vbox)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.paned.set_position(380)
        self.vbox.append(self.paned)
        overlay = Gtk.Overlay(child=self.map)
        self.paned.set_start_child(overlay)
        crosshair = Gtk.Label(label='+', halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        crosshair.add_css_class('map-crosshair')
        crosshair.set_can_target(False)
        overlay.add_overlay(crosshair)

        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0,
                        halign=Gtk.Align.START, valign=Gtk.Align.START,
                        margin_start=5, margin_top=5)
        zoom_box.add_css_class('osd')
        zin = Gtk.Button(icon_name='zoom-in-symbolic')
        zout = Gtk.Button(icon_name='zoom-out-symbolic')
        zin.connect('clicked', self.map.zoom_in)
        zout.connect('clicked', self.map.zoom_out)
        zoom_box.append(zout)
        zoom_box.append(zin)
        overlay.add_overlay(zoom_box)

        logo = Gtk.Image.new_from_file(asset('mapbox.svg'))
        logo.set_pixel_size(80)
        logo.set_halign(Gtk.Align.START)
        logo.set_valign(Gtk.Align.END)
        margins(logo, 6)
        logo.set_margin_bottom(32)
        logo.set_can_target(False)
        overlay.add_overlay(logo)

        credits = Gtk.Box()
        credits.set_halign(Gtk.Align.END)
        credits.set_valign(Gtk.Align.END)
        credits.append(self.creditLink('https://www.mapbox.com/about/maps/', '(c) Mapbox'))
        credits.append(self.creditLink('http://www.openstreetmap.org/about/', '(c) Openstreetmap'))
        credits.append(self.creditLink('https://www.mapbox.com/map-feedback/', 'Improve this map'))
        overlay.add_overlay(credits)

        if 'licenseKEY' not in self.settingsDialog.config['DownloadOptions']:
            premium = Gtk.Button(label=__('Go premium!'), halign=Gtk.Align.END, valign=Gtk.Align.START)
            premium.connect('clicked', self.gopremium)
            premium.add_css_class('gopremium')
            overlay.add_overlay(premium)
        self.listbox = Gtk.ListBox()
        self.listbox.set_activate_on_single_click(False)
        self.listbox.connect('row-activated', self.selrow)
        gesture = Gtk.GestureClick(button=3)
        gesture.connect('pressed', self.buttonPress)
        self.listbox.add_controller(gesture)
        scrolled = Gtk.ScrolledWindow(child=self.listbox, vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.paned.set_end_child(scrolled)
        toolbar = Gtk.Box(spacing=3)
        def button(icon, tooltip, callback):
            result = Gtk.Button(icon_name=icon, tooltip_text=tooltip)
            result.connect('clicked', callback)
            toolbar.append(result)
            return result
        button('find-location-symbolic', __('Find my location'), self.home_clicked)
        button('edit-find-symbolic', __('Search'), self.searchToggle_clicked)
        self.search_text = Gtk.Entry(hexpand=True, placeholder_text=__('Place, callsign, grid, frequency or node'))
        self.search_text.connect('activate', self.search_call)
        toolbar.append(self.search_text)
        self.back_button = button('go-previous-symbolic', __('Back'), self.back_clicked)
        self.cache_button = button('document-save-symbolic', __('Cache this map view'), self.cache_clicked)
        self.add_button = button('list-add-symbolic', __('Add Repeater'), self.add_repeater_clicked)
        self.pref_button = button('preferences-system-symbolic', __('Settings'), self.pref_clicked)
        self.help_button = button('help-browser-symbolic', __('Help'), self.help_clicked)
        self.help_about_button = button('help-about-symbolic', __('About'), self.helpAbout_clicked)
        self.vbox.append(toolbar)
        self.latlon_entry = Gtk.Entry(editable=False)
        self.vbox.append(self.latlon_entry)
        self.show_tooltips = False
        self.map.set_has_tooltip(True)
        self.map.connect('query-tooltip', self.on_query_tooltip)
        self.map.connect('changed', self.on_map_change)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._window_key)
        self.add_controller(keys)
        self.setViews()
        self.displayNodes()
        self._refresh_map()
        if start_background:
            self._timers.append(GLib.timeout_add(1000, self.downloadBackground))
            self._timers.append(GLib.timeout_add_seconds(600, self._periodic_download))
            GLib.idle_add(self._diagnostics_prompt)
            GLib.idle_add(self.updateMessage)

    def creditLink(self, url, label):
        link=Gtk.LinkButton(uri=url, label=label)
        link.add_css_class('credits')
        margins(link,0)
        return link

    def _window_key(self, controller, key, code, state):
        if key == Gdk.KEY_F11:
            self.unfullscreen() if self.is_fullscreen() else self.fullscreen()
            return True
        return False

    def _diagnostics_prompt(self):
        if self._closing:
            return False
        diagnostics = self.settingsDialog.config['Diagnostics']
        if 'SendReport' in diagnostics:
            if diagnostics.getboolean('SendReport', fallback=False):
                self.initSentry()
        else:
            def chosen(response):
                enabled = response == Gtk.ResponseType.YES
                diagnostics['SendReport'] = str(enabled)
                self.settingsDialog.writeSettings()
                if enabled:
                    self.initSentry()
            message(self, __('Do you want to send exception reports for Repeater-START?'), question=True, callback=chosen)
        return False

        
    def buttonPress(self, gesture, count, x, y):
        row = self.listbox.get_row_at_y(int(y))
        if row is None or not hasattr(row, 'repeater'):
            return
        if self._context_popover:
            self._context_popover.popdown()
        rpt = row.repeater
        popover = Gtk.Popover()
        popover.set_parent(self.listbox)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        popover.set_child(box)
        def link(label, url):
            btn = Gtk.Button(label=label)
            btn.connect('clicked', lambda *_: (popover.popdown(), webbrowser.open(url)))
            box.append(btn)
        if isinstance(rpt, HearHamRepeater):
            link(__('Goto Repeater Page'), f'https://hearham.com/repeaters/{rpt.id}?src={os.name}')
            link(__('Comment'), f'https://hearham.com/repeaters/{rpt.id}/comment?src={os.name}')
        elif getattr(rpt, 'node', ''):
            link(__('Goto IRLP Status page'), f'https://www.irlp.net/status/index.php?nodeid={rpt.node}')
        for url in re.findall(r'https?://[^\s<>"\']+', str(getattr(rpt, 'description', ''))):
            link(url, url)
        if box.get_first_child() is None:
            popover.unparent()
            return
        def closed(popover):
            if self._context_popover is popover:
                self._context_popover = None
            if popover.get_parent():
                popover.unparent()
        popover.connect('closed', closed)
        self._context_popover = popover
        popover.popup()

    

    
    def gopremium(self, *args):
        dlg = PremiumDialog(self)
        def response(dialog, result):
            key = dialog.get_license_key()
            dialog.destroy()
            if result == Gtk.ResponseType.OK and key:
                self.settingsDialog.config['DownloadOptions']['licenseKEY'] = key
                self.settingsDialog.writeSettings()
                self.downloadBackground()
        dlg.connect('response', response)
        dlg.present()

    
    def followIRLPlink(self,menuItem):
        webbrowser.open('https://www.irlp.net/status/index.php?nodeid=%s' % (menuItem.irlp,) )
        
    def followlink(self,menuItem):
        webbrowser.open("https://hearham.com/repeaters/%s?src=%s" % (menuItem.repeaterID,os.name) )

    def followcommentlink(self,menuItem):
        webbrowser.open("https://hearham.com/repeaters/%s/comment?src=%s" % (menuItem.repeaterID,os.name) )

    def followextralink(self,menuItem):
        webbrowser.open(menuItem.url)
        
    def setViews(self):
        if self.mode == 'search':
            self.search_text.show()
            self.back_button.hide()
            self.cache_button.hide()
            self.add_button.hide()
            self.pref_button.hide()
            self.help_button.hide()
            self.help_about_button.hide()
        else:
            self.search_text.hide()
            self.back_button.show()
            self.cache_button.show()
            self.add_button.show()
            self.pref_button.show()
            self.help_button.show()
            self.help_about_button.show()
    
    def search_call(self, widget):
        text = widget.get_text().strip()
        if not text:
            return
        try:
            code = openlocationcode.decode(text)
        except ValueError:
            code = None
        if code:
            self.map.set_center(code.latitudeCenter, code.longitudeCenter)
            return
        try:
            grid = locatorToLatLng(text)
        except (ValueError, IndexError):
            grid = None
        if grid:
            self.map.set_center(grid['lat'], grid['lng'])
        elif re.fullmatch(r'\d+(?:\.\d+)?', text):
            number = float(text)
            self.clearRows()
            lat, lon = self.map.viewport.props.latitude, self.map.viewport.props.longitude
            for rpt in sorted(self.allrepeaters, key=lambda r: r.distance(lat, lon)):
                freq = float(rpt.freq)
                if (math.isclose(freq, number, abs_tol=1e-6) or
                    math.isclose(freq + float(rpt.offset), number, abs_tol=1e-6) or
                    str(getattr(rpt, 'node', '')) == text):
                    self.addToList(rpt, lat, lon)
            if not self.GTKListRows:
                self.listbox.append(Gtk.Label(label=__('Nothing found for that frequency or node.')))
        else:
            thread = SearchThread(text, self)
            thread.daemon = True
            thread.start()

    def search_failed(self, error):
        if not self._closing:
            message(self, __('Search failed: ') + error)
        return False


    def processSearchResults(self, results_data):
        if self._closing:
            return False
        self.clearRows()
        if not results_data:
            self.listbox.append(Gtk.Label(label=__('Nothing found. Try a different peak, city or landmark.'), wrap=True))
        for item in results_data:
            row = Gtk.ListBoxRow()
            row.longitude, row.latitude = float(item['lon']), float(item['lat'])
            row.set_child(margins(Gtk.Label(label=item['display_name'], xalign=0, wrap=True), 8))
            self.listbox.append(row)
            self.searchRows.append(row)
        return False

        
    def clearRows(self):
        if self._context_popover:
            self._context_popover.popdown()
        while (child := self.listbox.get_first_child()) is not None:
            # Popovers are parented explicitly, not rows owned by ListBox.
            if isinstance(child, Gtk.Popover):
                child.unparent()
            else:
                self.listbox.remove(child)
        self.GTKListRows, self.searchRows, self.playBtns = [], [], []

    
    def initSentry(self):
        import sentry_sdk
        import platform
        useros = open('/etc/issue').read().strip() if os.path.exists('/etc/issue') else 'Unknown'
        sentry_sdk.init(
            dsn="https://662e8ffdfdf1a8e4691990e0b9dd1911@o92400.ingest.us.sentry.io/4511273440968704",
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
        sentry_sdk.set_tags({
            'Platform': platform.platform(), #Linux version
            'Issue': useros, # Ubuntu version
            'Machine' : platform.machine(),
            'CPU': platform.processor()
		})
        print("Errors will be reported for quality control.")
        
    def selrow(self, widget, row):
        if hasattr(row, 'latitude'):
            self.map.set_center(row.latitude, row.longitude)

        
        
    def updateMessage(self):
        if self._closing:
            return False
        try:
            with open(userFile('update.response')) as infile:
                info = json.load(infile)
            if str(info['version']) != self.version:
                message(self, __('There is an update available. Do you wish to install it?') + '\n' + info['message'],
                        question=True, callback=lambda response: webbrowser.open(info['link']) if response == Gtk.ResponseType.YES else None)
        except (OSError, ValueError, KeyError):
            pass
        return False

    
        


    def displayNodes(self):
        if self._closing:
            return False
        minimum, maximum = self.settingsDialog.getMinFilter(), self.settingsDialog.getMaxFilter()
        self.allrepeaters, self._marker_data = [], []
        for name, url in self.settingsDialog.getShown().items():
            if 'hearham.com/api/repeaters/v1' in url:
                try:
                    with open(userFile('irlp.txt')) as infile:
                        for line in infile:
                            try:
                                self.addRepeaterIcon(IRLPNode(line), minimum, maximum)
                            except (ValueError, IndexError):
                                continue
                except OSError:
                    pass
                try:
                    with open(userFile('repeaters.json')) as infile:
                        data = json.load(infile)
                    for item in data:
                        if item.get('group') != 'IRLP':
                            try:
                                self.addRepeaterIcon(HearHamRepeater(item), minimum, maximum)
                            except (ValueError, TypeError, KeyError):
                                continue
                except (OSError, ValueError):
                    pass
            else:
                filename = userFile('rpt-' + name + '.csv')
                if not os.path.exists(filename):
                    continue
                try:
                    listing = CsvRepeaterListing(filename, download_icon=False)
                    icon = listing.getIcon()
                    # Keep the supplied custom symbol for up repeaters; down
                    # repeaters use the application's red tower symbol.
                    for rpt in listing.repeaters:
                        self.addRepeaterWithIcon(rpt, minimum, maximum,
                                                self.towerDownPic if rpt.isDown() else icon)
                except (OSError, ValueError, IndexError, AttributeError, GLib.Error) as error:
                    print('Cannot read repeater source:', name, error)
        self.map.set_repeaters(self._marker_data)
        self.refreshListing()
        return False

    
    def addRepeaterIcon(self, repeater, minimum, maximum):
        icon = self.towerDownPic if repeater.isDown() else self.towerPic
        self.addRepeaterWithIcon(repeater, minimum, maximum, icon)

            
    def addRepeaterWithIcon(self, repeater, minimum, maximum, icon):
        if minimum <= float(repeater.freq) <= maximum:
            self.allrepeaters.append(repeater)
            self._marker_data.append((repeater, icon))




    def on_show_tooltips_toggled(self, btn):
        self.show_tooltips = btn.props.active


    def downloadBackground(self):
        if self._closing or any(not job.finished for job in self._downloads):
            return False
        if isMobileData() and not self.settingsDialog.getAllowMobile():
            return False
        jobs = [('https://hearham.com/api/updatecheck/linux', 'update.response', BackgroundDownload)]
        options = self.settingsDialog.config['DownloadOptions']
        if 'licenseKEY' in options:
            jobs.append(('https://hearham.com/api/repeaters/v1/radios?key=' + urllib.parse.quote(options['licenseKEY']), 'premium.zip', BackgroundDownloadZip))
        else:
            jobs.append(('https://hearham.com/premiumpromo.txt', 'promo.txt', BackgroundDownload))
        for name, url in self.settingsDialog.getShown().items():
            if 'hearham.com/api/repeaters/v1' in url:
                jobs.extend([('https://hearham.com/nohtmlstatus.txt', 'irlp.txt', BackgroundDownload),
                             ('https://hearham.com/api/repeaters/v1', 'repeaters.json', BackgroundDownload)])
            elif '.csv' in url:
                jobs.append((url, 'rpt-' + name + '.csv', BackgroundDownload))
        self._downloads = [cls(url, userFile(filename)) for url, filename, cls in jobs]
        for job in self._downloads:
            job.daemon = True
            job.start()
        self._download_poll_id = GLib.timeout_add(300, self._downloads_finished)
        return False

    def _periodic_download(self):
        self.downloadBackground()
        return not self._closing

    def _downloads_finished(self):
        if self._closing:
            return False
        if any(not job.finished for job in self._downloads):
            return True
        self._download_poll_id = 0
        self.displayNodes()
        return False

            

    def zoom_in_clicked(self, button):
        self.map.set_zoom(self.map.viewport.props.zoom_level + 1)

    def zoom_out_clicked(self, button):
        self.map.set_zoom(self.map.viewport.props.zoom_level - 1)

    def home_clicked(self, button):
        self.lastLat, self.lastLon = self.map.viewport.props.latitude, self.map.viewport.props.longitude
        Geoclue.Simple.new('repeaterstart', Geoclue.AccuracyLevel.EXACT, None, self.getlocation)

        
    def back_clicked(self, button):
        self.map.set_center_and_zoom(self.lastLat, self.lastLon, 12)
        
    def searchToggle_clicked(self,button):
        if self.mode == 'search':
            self.mode = ''
        else:
            self.mode = 'search'
            self.search_text.grab_focus()
        self.setViews()
        
    def help_clicked(self, button):
        message(self, __('Repeater-START finds amateur radio repeaters near the map center.\n'
            'Pan or zoom the map; nearby repeaters are sorted by distance. Click a marker for its callsign and frequency, or double-click a list row to center it.\n'
            'Search by place, callsign, Maidenhead grid, Plus Code, frequency or IRLP node.\n'
            'Cache downloads this view and two deeper zoom levels for offline use. Click again to cancel.\n'
            'Settings controls units, frequency filters and repeater sources. Play listens with RTL-SDR and SoX.'))

        
    def helpAbout_clicked(self, button):
        changed = 'never'
        filename = userFile('repeaters.json')
        if os.path.exists(filename):
            changed = datetime.datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d %H:%M')
        message(self, f'Repeater-START {self.version}\nGTK4 / libshumate\n'
                f'Repeater data updated: {changed}\nhttps://hearham.com/repeaters\n'
                'Support: contact@hearham.live', title=__('About'))

    
    def pref_clicked(self,button):
        self.settingsDialog.show()
        
    def getlocation(self, source, result):
        if self._closing:
            return
        try:
            self._geoclue = Geoclue.Simple.new_finish(result)
            location = self._geoclue.get_location()
            self.map.set_center_and_zoom(location.props.latitude, location.props.longitude, 12)
        except GLib.Error as error:
            message(self, __('Unable to find your location. Check your desktop location permissions.') + '\n' + str(error))

            
    



    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip):
        if not keyboard_tip and self.show_tooltips:
            lat, lon = self.map.screen_to_location(x, y)
            tooltip.set_text(f'{lat:+.4f}, {lon:+.4f}')
            return True
        return False


    def cache_clicked(self, button):
        if self.map._prefetch:
            self.map.cancel_cache()
            return
        def progress(done, total, failures, cancelled):
            self.cache_button.set_tooltip_text(f'Cache: {done}/{total}; {failures} failed. Click to cancel.')
            if self.map._prefetch is None:
                self.cache_button.set_icon_name('document-save-symbolic')
                self.cache_button.set_tooltip_text(__('Cache this map view'))
                text = __('Caching cancelled.') if cancelled else f'Cached {done-failures}/{total} tiles.'
                if failures and not cancelled:
                    text += ' Some tiles could not be downloaded; check your connection.'
                self.latlon_entry.set_text(text)
        try:
            self.cache_button.set_icon_name('process-stop-symbolic')
            self.map.cache_view(progress)
        except ValueError as error:
            self.cache_button.set_icon_name('document-save-symbolic')
            message(self, str(error))

        
    def add_repeater_clicked(self, button):
        webbrowser.open("https://hearham.com/repeaters/add?lat=%s&lon=%s" % (self.map.viewport.props.latitude, self.map.viewport.props.longitude) )

    def on_map_change(self, widget):
        if self._map_change_id:
            GLib.source_remove(self._map_change_id)
        self._map_change_id = GLib.timeout_add(180, self._refresh_map)

    def _refresh_map(self):
        self._map_change_id = 0
        if self._closing:
            return False
        lat, lon = self.map.viewport.props.latitude, self.map.viewport.props.longitude
        if (self.renderedLat, self.renderedLon) != (lat, lon):
            self.renderedLat, self.renderedLon = lat, lon
            text = f'{__("Map Center:")} {latLongToLocator(lat, lon)}, {lat:.4f}, {lon:.4f}'
            if self.settingsDialog.getMinFilter() > -1 or self.settingsDialog.getMaxFilter() < 1e99:
                text += ' ' + __('(Repeaters filtered in settings)')
            self.latlon_entry.set_text(text)
            self.refreshListing()
            for window, entry in list(self._elevation_windows.items()):
                btn = entry['btn']
                self.map.remove_overlay_layer(entry['track'])
                entry['track'] = self._make_track([(btn.lat, btn.lon), (lat, lon)])
                self.map.add_overlay_layer(entry['track'])
                window.loadsvg(self._svg_url(btn))
        return False

    
    def refreshListing(self):
        lat, lon = self.map.viewport.props.latitude, self.map.viewport.props.longitude
        self.clearRows()
        minimum, maximum = self.settingsDialog.getMinFilter(), self.settingsDialog.getMaxFilter()
        for rpt in sorted(self.allrepeaters, key=lambda r: r.distance(lat, lon)):
            if rpt.distance(lat, lon) > 500:
                break
            if minimum <= float(rpt.freq) <= maximum:
                self.addToList(rpt, lat, lon)
                if len(self.GTKListRows) >= 100:
                    break

    
    def addToList(self, repeater, lat, lon):
        row = Gtk.ListBoxRow()
        row.repeater = repeater
        row.latitude, row.longitude = float(repeater.lat), float(repeater.lon)
        box = margins(Gtk.Box(spacing=8), 8)
        row.set_child(box)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        box.append(text)
        title = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        title.add_css_class('repeater-title')
        node = getattr(repeater, 'node', '')
        caption = f'{repeater.callsign}, {repeater.freq} MHz'
        if float(repeater.freq) == 0:
            caption = f'{repeater.callsign} Reflector {node}'
        elif node:
            caption += f' · Node {node}'
        title.set_markup(('<s>' + GLib.markup_escape_text(caption) + '</s>') if repeater.isDown() else GLib.markup_escape_text(caption))
        text.append(title)
        try:
            linked = int(repeater.status)
        except (TypeError, ValueError):
            linked = 0
        if repeater.status == 0:
            irlp = 'OFFLINE'
        elif type(repeater.status) != int and not repeater.status.isnumeric():
            irlp = repeater.status
        else:
            irlp = ''
        if float(repeater.freq) == 0:
            #Reflecter info
            details = Gtk.Label(label=repeater.city, xalign=0, ellipsize=Pango.EllipsizeMode.END)
        else:
            if repeater.offset>0:
                details = Gtk.Label(label=f'PL {repeater.pl}, Offset +{repeater.offset} MHz {irlp}', xalign=0, ellipsize=Pango.EllipsizeMode.END)
            else:
                details = Gtk.Label(label=f'PL {repeater.pl}, Offset {repeater.offset} MHz {irlp}', xalign=0, ellipsize=Pango.EllipsizeMode.END)
        text.append(details)
        description = Gtk.Label(label=str(getattr(repeater, 'description', '')), xalign=0, ellipsize=Pango.EllipsizeMode.END)
        text.append(description)
        if linked > 1:
            link = Gtk.Button(label=f'Linked to {linked}')
            link.connect('clicked', self.goLinkIRLP)
            text.append(link)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        distance = repeater.distance(lat, lon)
        unit = self.settingsDialog.getUnit()
        if unit == 'mi':
            distance *= 0.62137119
        right.append(Gtk.Label(label=f'{distance:.1f} {unit}'))
        buttons = Gtk.Box(spacing=2)
        play = Gtk.Button(icon_name='media-playback-stop-symbolic' if repeater.freq == self.playingfreq else 'media-playback-start-symbolic', tooltip_text=__('Listen with RTL-SDR'))
        play.selFrequency = repeater.freq
        play.connect('clicked', self.playpause)
        buttons.append(play)
        helpbtn = Gtk.Button(icon_name='help-browser-symbolic', tooltip_text=__('Radio Setup Help'))
        helpbtn.repeater = repeater
        helpbtn.connect('clicked', self.helppro)
        buttons.append(helpbtn)
        elevation = Gtk.Button(tooltip_text=__('Elevation profile'))
        picture = Gtk.Image.new_from_file(asset('mtns.svg'))
        picture.set_pixel_size(24)
        elevation.set_child(picture)
        elevation.lat, elevation.lon, elevation.call = repeater.lat, repeater.lon, repeater.callsign
        elevation.connect('clicked', self.elevationDisplay)
        buttons.append(elevation)
        right.append(buttons)
        box.append(right)
        self.GTKListRows.append(row)
        self.playBtns.append(play)
        self.listbox.append(row)


    # ---------- track helpers ----------

    def _make_track(self, points, color_hex='#FF0000', width=4):
        return self.map.make_path(points, color_hex, width)


    def _svg_url(self, btn):
        return 'https://hearham.com/api/topo/v1/svg?lat1=%s&lon1=%s&lat2=%s&lon2=%s' % (
            btn.lat, btn.lon, self.map.viewport.props.latitude, self.map.viewport.props.longitude
        )

    # ---------- elevation windows ----------

    def elevationDisplay(self, btn):
        track = self._make_track([(btn.lat, btn.lon),
                                 (self.map.viewport.props.latitude, self.map.viewport.props.longitude)])
        self.map.add_overlay_layer(track)
        window = SVGLoaderWindow(self, self._svg_url(btn), btn.call)
        self._elevation_windows[window] = {'track': track, 'btn': btn}
        window.connect('close-request', self._on_elevation_window_destroy, window)
        window.present()
        return window


    def _on_elevation_window_destroy(self, widget, window):
        entry = self._elevation_windows.pop(window, None)
        if entry:
            self.map.remove_overlay_layer(entry['track'])
        return False


    def playpause(self, btn):
        if self.playingfreq == btn.selFrequency:
            self._stop_radio()
            return
        if not shutil.which('rtl_fm') or not shutil.which('play'):
            message(self, __('Install rtl-sdr and sox to listen to a repeater.'))
            return
        self._stop_radio()
        try:
            self.playRTLSDR(btn.selFrequency)
        except (OSError, ValueError) as error:
            message(self, str(error))
            return
        self.playingfreq = btn.selFrequency
        self._radio_icons()
        self._radio_poll_id = GLib.timeout_add(500, self._poll_radio)

    def _radio_icons(self):
        for button in self.playBtns:
            button.set_icon_name('media-playback-stop-symbolic' if button.selFrequency == self.playingfreq else 'media-playback-start-symbolic')

    def _stop_radio(self):
        if getattr(self, '_radio_poll_id', 0):
            GLib.source_remove(self._radio_poll_id)
            self._radio_poll_id = 0
        if self.rtllistener:
            self.rtllistener.stop()
            self.rtllistener = None
        self.playingfreq = None
        self._radio_icons()

    def _poll_radio(self):
        if self._closing:
            return False
        if self.rtllistener and self.rtllistener.exited():
            self._radio_poll_id = 0
            self._stop_radio()
            message(self, __('Radio playback stopped. Check the RTL-SDR device and audio output.'))
            return False
        return True

    def goLinkIRLP(self, btn):
        label = btn.get_label()
        print(label)
        label = label.replace('Linked to','').strip()
        for item in self.allrepeaters:
            if item.node == label:
                self.map.set_center(item.lat, item.lon)
        
    def helppro(self, el):
        pro = pathlib.Path(userFile('.hidden'))
        if not (pro / 'index.html').exists():
            self.gopremium()
            return
        rpt = el.repeater
        values = {'CALL': rpt.callsign, 'FREQ': str(rpt.freq), 'OFFSET': str(rpt.offset),
                  'MODE': str(rpt.mode), 'PL': str(rpt.pl), 'PLDECODE': str(getattr(rpt, 'decode', '')),
                  'DISABLED': bool(rpt.isDown()), 'URL': str(rpt.url)}
        (pro / 'base.data.js').write_text('\n'.join(f'{key}={json.dumps(value)};' for key, value in values.items()))
        subprocess.Popen([sys.executable, asset('HelpDialog.py')])



    def playRTLSDR(self, mhz):
        self.rtllistener = RTLSDRRun(mhz)

            
    def cleanup(self, *args):
        if self._closing:
            return False
        self._closing = True
        self._stop_radio()
        for source in [self._map_change_id, getattr(self, '_download_poll_id', 0)]:
            if source:
                GLib.source_remove(source)
        for source in self._timers:
            if GLib.MainContext.default().find_source_by_id(source):
                GLib.source_remove(source)
        for window in list(self._elevation_windows):
            window.close()
        self.settingsDialog.close()
        self.map.close()
        state = {'lat': self.map.viewport.props.latitude,
                 'lon': self.map.viewport.props.longitude,
                 'zoom': self.map.viewport.get_zoom_level()}
        with open(userFile('lastPosition.json'), 'w') as outfile:
            json.dump(state, outfile)
        return False

    

class RepeaterApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.hearham.repeaterstart')
        GLib.set_prgname('repeaterstart')
        GLib.set_application_name('Repeater-START')

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = UI(self)
        window.present()


if __name__ == '__main__':
    sys.exit(RepeaterApplication().run(sys.argv))
