#!/usr/bin/python3
"""
Repeater START - Showing The Amateur Repeaters Tool
(C) 2019-2022 Luke Bryan.
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
import os.path
import random
import subprocess
import json

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('Geoclue', '2.0')
gi.require_version('OsmGpsMap', '1.0')
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
from gi.repository import cairo

from gi.repository import Geoclue
import math
import shutil
import urllib.request
import urllib.parse
from math import pi, sin, cos, sqrt, atan2, radians

from IRLPNode import IRLPNode
from HearHamRepeater import HearHamRepeater
from SettingsDialog import SettingsDialog
from MaidenheadLocator import locatorToLatLng, latLongToLocator
from lib import openlocationcode #Plus code. https://github.com/google/open-location-code
from NetworkStatus import isMobileData

from threading import Thread
from gi.repository import OsmGpsMap as osmgpsmap

assert osmgpsmap._version == "1.0"

class RTLSDRRun(Thread):
    def __init__(self, cmd):
        Thread.__init__(self)
        self.cmd = cmd
        
    def run(self):
        #TODO test commands more
        #cmd = 'rtl_fm -M fm -f '+self.freq+'M -l 202 | play -r 24k -t raw -e s -b 16 -c 1 -V1 -'
        cmds = self.cmd.split('|')
        self.proc = subprocess.Popen(cmds[0].split(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        subprocess.check_output(cmds[1].split(),stdin=self.proc.stdout)
        for line in iter(self.proc.stdout.readline, b''):
            line = line.decode('utf-8')

class BackgroundDownload(Thread):
    def __init__(self, url, filename):
        #Thread init, as this is a thread:
        Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.finished = False
        self.success = False
    def run(self):
        try:
            tmpfile = '/tmp/output'+str(int(time.time()))+str(random.random())
            urllib.request.urlretrieve(self.url, tmpfile)
            shutil.move( tmpfile, self.filename )
            self.finished = True
            self.success = True
        except urllib.error.URLError:
            print("offline?")
            self.finished = True
        except urllib.error.HTTPError:
            print("Failed to fetch.")
            self.finished = True




class UI(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.version = '0.9.1'
        self.mode = ''
        self.set_default_size(500, 500)
        self.connect('destroy', self.cleanup)
        self.set_title('RepeaterSTART GPS Mapper')
        self.vbox = Gtk.VBox(False, 0)
        self.add(self.vbox)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.pack_start(self.paned, True, True, 0);

        self.unit = 'mi' #or km
        self.renderedLat = None
        self.renderedLon = None
        
        self.rtllistener = None
        self.playingfreq = None
        self.PLAYSIZE = Gtk.IconSize.BUTTON
        self.settingsDialog = SettingsDialog(self)
        
        self.mainScreen = Gdk.Screen.get_default()
        privatetilesapi='https://api.mapbox.com/styles/v1/programmin/ck7jtie300p7e1iqi1ow2yvi3/tiles/256/#Z/#X/#Y?access_token=pk.eyJ1IjoicHJvZ3JhbW1pbiIsImEiOiJjazdpaXVpMTEwbHJ1M2VwYXRoZmU3bmw4In0.3UpUBsTCOL5zvvJ1xVdJdg'

        self.osm = osmgpsmap.Map(
            repo_uri=privatetilesapi,
            image_format='jpg',
        )
        if os.path.exists(self.userFile('lastPosition.json')):
            with open(self.userFile('lastPosition.json')) as lastone:
                lastposition = json.loads(lastone.read())
                self.osm.set_center_and_zoom(lastposition['lat'],
                    lastposition['lon'],
                    lastposition['zoom']
                )
        #Now map-source required or it gets some mysterious null pointers and render issue:
        self.osm.set_property("map-source", osmgpsmap.MapSource_t.LAST)
        self.osm.set_property("repo-uri", privatetilesapi)
        
        osd = osmgpsmap.MapOsd(
                        show_dpad=True,
                        show_zoom=True,
                        show_crosshair=True)
        
        icon_app_path = '/usr/share/icons/hicolor/scalable/apps/repeaterSTART.svg'
        if os.path.exists(icon_app_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_app_path)
            surface=Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        self.towerDownPic = GdkPixbuf.Pixbuf.new_from_file_at_scale('signaltowerdown.svg',width=20,height=20,preserve_aspect_ratio=True)
        self.towerPic = GdkPixbuf.Pixbuf.new_from_file_at_scale('signaltower.svg',width=20,height=20,preserve_aspect_ratio=True)
        
        self.osm.layer_add(osd)
        
        self.displayNodes()

        self.last_image = None

        self.osm.connect('button_press_event', self.on_button_press)
        self.osm.connect('button_release_event', self.on_button_release)
        self.osm.connect('changed', self.on_map_change)

        #connect keyboard shortcuts
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.FULLSCREEN, Gdk.keyval_from_name("F11"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.UP, Gdk.keyval_from_name("Up"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.DOWN, Gdk.keyval_from_name("Down"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.LEFT, Gdk.keyval_from_name("Left"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.RIGHT, Gdk.keyval_from_name("Right"))

        #connect to tooltip
        self.osm.props.has_tooltip = True
        self.osm.connect("query-tooltip", self.on_query_tooltip)

        self.latlon_entry = Gtk.Entry()

        home_button = Gtk.Button()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale('locateme.svg',width=21,height=21,preserve_aspect_ratio=True)
        GoImg = Gtk.Image.new_from_pixbuf(pixbuf)
        home_button.set_image(GoImg)
        home_button.set_tooltip_text('Find my location')
        search_button = Gtk.Button()
        search_button.set_image(Gtk.Image(icon_name='edit-find',
                      icon_size=Gtk.IconSize.LARGE_TOOLBAR))
        search_button.connect('clicked', self.searchToggle_clicked)
        self.search_text = Gtk.Entry()
        self.search_text.connect('activate',self.search_call)
        
        self.help_button = Gtk.Button()
        self.help_button.set_image(Gtk.Image(icon_name='help-browser',
                      icon_size=Gtk.IconSize.LARGE_TOOLBAR))
        self.help_button.connect('clicked', self.help_clicked)
        self.help_about_button = Gtk.Button()
        self.help_about_button.set_image(Gtk.Image(icon_name='help-about',
                      icon_size=Gtk.IconSize.LARGE_TOOLBAR))
        self.help_about_button.connect('clicked', self.helpAbout_clicked)
        
        self.pref_button = Gtk.Button()
        self.pref_button.set_image(Gtk.Image(icon_name="preferences-system",
                       icon_size=Gtk.IconSize.LARGE_TOOLBAR))
        self.pref_button.connect('clicked', self.pref_clicked)
                       
        
        home_button.connect('clicked', self.home_clicked)
        self.back_button = Gtk.Button(stock=Gtk.STOCK_GO_BACK)
        self.back_button.connect('clicked', self.back_clicked)
        
        self.cache_button = Gtk.Button('Cache')
        self.cache_button.connect('clicked', self.cache_clicked)
        if self.mainScreen.get_width() < 800:
            #Just room for icon on Librem/phone.
            self.add_button = Gtk.Button()
            self.add_button.set_image(Gtk.Image(icon_name="list-add",
                       icon_size=Gtk.IconSize.LARGE_TOOLBAR))
        else:
            self.add_button = Gtk.Button('Add Repeater')
        self.add_button.connect('clicked', self.add_repeater_clicked)
        
        overlay = Gtk.Overlay()
        overlay.set_size_request(15,15)
        overlay.add(self.osm)
        top_container = Gtk.VBox()
        leftright_container = Gtk.HBox()
        mapboxlogo = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale('mapbox.svg',width=80,height=25,preserve_aspect_ratio=True))
        leftright_container.pack_start(mapboxlogo, False, False, 0)
        leftright_container.pack_end(self.linkLabel(' Improve this map', self.improvement_link), False, False, 0)
        leftright_container.pack_end(self.linkLabel(' (c) openstreetmap ', self.credit_osm), False, False, 0)
        leftright_container.pack_end(self.linkLabel(' (c) mapbox ', self.credit_mapbox), False, False, 0)
        
        top_container.pack_end(leftright_container, False, False, 0)
        #self.vbox.pack_start(overlay, True, True, 0)
        self.paned.pack1(overlay, resize=True)
        overlay.add_overlay(top_container)
        overlay.set_overlay_pass_through(top_container,True)
        #overlay.set_overlay_pass_through(mapboxlink,False)
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(home_button, False, True, 0)
        hbox.pack_start(search_button, False, True, 0)
        hbox.pack_start(self.search_text, False, True, 0)
        hbox.pack_start(self.back_button, False, True, 0)
        hbox.pack_start(self.cache_button, False, True, 0)
        hbox.pack_start(self.add_button, False, True, 0)
        hbox.pack_start(self.pref_button, False, True, 0)
        hbox.pack_start(self.help_button, False, True, 0)
        hbox.pack_start(self.help_about_button, False, True, 0)

        #Adding image in the render code causes infinite loop.
        icon_app_path = '/usr/share/icons/hicolor/scalable/apps/repeaterSTART.svg'
        if os.path.exists(icon_app_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_app_path)
            self.set_icon(pixbuf)
            
        #add ability to test custom map URIs
        #ex = Gtk.Expander(label="<b>Display Options</b>")
        #ex.props.use_markup = True
        vb = Gtk.VBox()
        self.repouri_entry = Gtk.Entry()
        self.image_format_entry = Gtk.Entry()
        self.image_format_entry.set_text(self.osm.props.image_format)

        
        lbl = Gtk.Label(
"""
Enter an repository URL to fetch map tiles from in the box below. Special metacharacters may be included in this url

<i>Metacharacters:</i>
\t#X\tMax X location
\t#Y\tMax Y location
\t#Z\tMap zoom (0 = min zoom, fully zoomed out)
\t#S\tInverse zoom (max-zoom - #Z)
\t#Q\tQuadtree encoded tile (qrts)
\t#W\tQuadtree encoded tile (1234)
\t#U\tEncoding not implemeted
\t#R\tRandom integer, 0-4""")
        lbl.props.xalign = 0
        lbl.props.use_markup = True
        lbl.props.wrap = True

        #ex.add(vb)
        self.show_tooltips = False
        #self.vbox.pack_end(ex, False, True, 0)
        self.vbox.pack_end(self.latlon_entry, False, True, 0)
        self.vbox.pack_end(hbox, False, True, 0)

        GLib.timeout_add(500, self.print_tiles)
        GLib.timeout_add(1000, self.downloadBackground)
        self.bgdl = None

        self.listbox = Gtk.ListBox()
        self.listbox.set_activate_on_single_click(False)
        self.listbox.connect('row-activated', self.selrow)
        self.listbox.connect("button_press_event", self.buttonPress)
        
        self.searchlistbox = Gtk.ListBox()
        self.searchlistbox.set_activate_on_single_click(False)
        self.searchlistbox.connect('row-activated', self.selsearchrow)
        self.searchRows = []

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        #self.vbox.pack_start(scrolled, True, True, 0)
        self.paned.pack2(scrolled, resize=True)
        self.GTKListRows = []
        self.playBtns = []
        GObject.idle_add(self.updateMessage)
        
    def buttonPress(self,listbox, event):
        """
        The right click feature on repeater list items
        """
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            moment = event.time
            listBoxRow = listbox.get_row_at_y(y)
            if listBoxRow is not None:
                listBoxRow.grab_focus()
                # Right click menu
                rcmenu = Gtk.Menu()
                rcgoto = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_JUMP_TO,None)
                if listBoxRow.repeaterID>0:
                    rcgoto.connect("activate", self.followlink)
                    rcgoto.repeaterID = listBoxRow.repeaterID
                    rcgoto.set_label("_Goto Repeater Page")
                    rcgoto.show()
                    rccomment = Gtk.ImageMenuItem.new()
                    rccomment.connect("activate", self.followcommentlink)
                    rccomment.repeaterID = listBoxRow.repeaterID
                    rccomment.set_label("Comment")
                    rccomment.show()
                    rcmenu.append(rcgoto)
                    rcmenu.append(rccomment)
                    #And link any other links in the description:
                    desc = listBoxRow.get_children()[0].get_children()[0].get_children()[-1].get_text()
                    for url in re.finditer(r'(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', desc):
                        link = Gtk.ImageMenuItem.new()
                        link.url = url.group(0)
                        link.connect("activate", self.followextralink)
                        link.set_label(link.url)
                        link.show()
                        rcmenu.append(link)
                elif int(listBoxRow.irlp)>0:
                    rcgoto.connect("activate", self.followIRLPlink)
                    rcgoto.irlp = listBoxRow.irlp
                    rcgoto.set_label("_Goto IRLP Status page")
                    rcgoto.show()
                    rcmenu.append(rcgoto)
                else:
                    print('Unknown data')
                rcmenu.popup(None, None, None,None,
                          event.button, moment)
                          
    def followIRLPlink(self,menuItem):
        os.system('xdg-open "https://www.irlp.net/status/index.php?nodeid=%s"' % (menuItem.irlp,) )
        
    def followlink(self,menuItem):
        os.system('xdg-open "https://hearham.com/repeaters/%s?src=%s"' % (menuItem.repeaterID,os.name) )

    def followcommentlink(self,menuItem):
        os.system('xdg-open "https://hearham.com/repeaters/%s/comment?src=%s"' % (menuItem.repeaterID,os.name) )

    def followextralink(self,menuItem):
        os.system('xdg-open "%s"' % (menuItem.url.replace('"','%22'),) )
        
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
        srctext = widget.get_text()
        try:
            pluscode = openlocationcode.decode(srctext)
            self.osm.set_center(pluscode.latitudeCenter, pluscode.longitudeCenter)
        except:
            try:
                gridsquare = locatorToLatLng(srctext)
                if gridsquare:
                    self.osm.set_center(gridsquare['lat'], gridsquare['lng'])
                #Search for number - internet node no. or frequency
                elif re.match(r"(\d)*\.?(\d)*$", srctext):
                    number = float(srctext)
                    self.clearRows()
                    lat, lon = self.osm.props.latitude, self.osm.props.longitude
                    noneFound = True;
                 
                    for repeater in self.allrepeaters:
                        km = repeater.distance(lat,lon)
                        if self.settingsDialog.getUnit() == 'mi':
                            km = km*.62137119
                        freq = float(repeater.freq)
                        off = freq + float(repeater.offset)
                        if repeater.freq == number or number == off:
                            row = Gtk.ListBoxRow()
                            row.longitude = float(repeater.lon)
                            row.latitude = float(repeater.lat)
                            row.repeaterID = repeater.id
                            # ^ for double click activate
                            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                            #print(repeater.callsign, repeater.freq, off, km)
                            mainlbl = Gtk.Label("%s (%.3f/%.3f) (%.2f%s)" % (
                                  repeater.callsign, freq, off, km, self.settingsDialog.getUnit() ), xalign=0)
                            hbox.pack_start(mainlbl,True,True,0)
                            row.add(hbox)
                            self.listbox.add(row)
                            self.searchRows.append(row)
                            noneFound = False
                        elif repeater.node == srctext:
                            row = Gtk.ListBoxRow()
                            row.longitude = float(repeater.lon)
                            row.latitude = float(repeater.lat)
                            row.repeaterID = repeater.id
                            # ^ for double click activate
                            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                            mainlbl = Gtk.Label("%s node %s (%.2f%s)" % (
                                repeater.callsign, repeater.node, km, self.settingsDialog.getUnit()
                            ),xalign=0)
                            hbox.pack_start(mainlbl,True,True,0)
                            row.add(hbox)
                            self.listbox.add(row)
                            self.searchRows.append(row)
                            noneFound = False
                    if noneFound:
                        row = Gtk.ListBoxRow()
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                        mainlbl = Gtk.Label("Sorry, nothing found for that frequency or IRLP node number",xalign=0)
                        hbox.pack_start(mainlbl,True,True,0)
                        row.add(hbox)
                        self.listbox.add(row)
                        self.searchRows.append(row)
                    self.listbox.show_all()
                    
                #What3Words address has 2 . in it:
                elif re.match( r".*\..*\..*", srctext):
                    req = urllib.request.Request(
                        'https://hearham.com/api/whatthreewords/v1?words=%s' % (urllib.parse.quote(srctext),), 
                        data=None,
                        headers={
                            'User-Agent': 'Repeater-START/'+self.version
                        }
                    )
                    f = urllib.request.urlopen(req)
                    objs = json.loads(f.read().decode('utf-8'))
                    if not objs:
                        self.latlon_entry.set_text('Invalid what3words.com address.')
                    else:
                        self.osm.set_center(objs['coordinates']['lat'], objs['coordinates']['lng'])
                        self.latlon_entry.set_text('Map Center: %s %s : %s' % ( latLongToLocator(objs['coordinates']['lat'], objs['coordinates']['lng']), objs['map'], objs['nearestPlace'] ) )
                else:
                    # Use new query format https://github.com/osm-search/Nominatim/issues/2121 
                    req = urllib.request.Request(
                        'https://nominatim.openstreetmap.org/search?q=%s&format=json&limit=50' % (urllib.parse.quote(srctext),), 
                        data=None,
                        headers={
                            'User-Agent': 'Repeater-START/'+self.version
                        }
                    )
                    f = urllib.request.urlopen(req)
                    objs = json.loads(f.read().decode('utf-8'))
                    self.clearRows()
                    if len(objs) == 0:
                        row = Gtk.ListBoxRow()
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                        mainlbl = Gtk.Label("Sorry, nothing found. Please enter a different peak, city or landmark.",xalign=0)
                        hbox.pack_start(mainlbl,True,True,0)
                        row.add(hbox)
                        self.listbox.add(row)
                        self.searchRows.append(row)
                    for item in objs:
                        row = Gtk.ListBoxRow()
                        row.longitude = float(item['lon'])
                        row.latitude = float(item['lat'])
                        # ^ for double click activate
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                        mainlbl = Gtk.Label(item['display_name'],xalign=0)
                        hbox.pack_start(mainlbl,True,True,0)
                        row.add(hbox)
                        self.listbox.add(row)
                        self.searchRows.append(row)
                    self.listbox.show_all()
            except urllib.error.URLError:
                self.latlon_entry.set_text('Network error')
                
    def clearRows(self):
        for r in self.GTKListRows:
            r.destroy()
        self.GTKListRows = []
        for r in self.searchRows:
            r.destroy()
        self.searchRows = []
        
        
    def selrow(self,widget,listboxrow):
        self.osm.set_center(listboxrow.latitude, listboxrow.longitude)
        
    def selsearchrow(self, widget, listboxrow):
        print(widget)
        
    def updateMessage(self):
        toupdatefile = self.userFile('update.response')
        if os.path.exists(toupdatefile):
            Gdk.threads_enter()
            try:
                updateinfo = json.load(open(toupdatefile))
                if str(updateinfo['version']) != self.version:
                    dlg = Gtk.MessageDialog(self, 
                        0,Gtk.MessageType.QUESTION,
                        Gtk.ButtonsType.YES_NO,
                        'There is an update available. Do you wish to install it?\n'+
                        updateinfo['message'])
                    response = dlg.run()
                    if response == Gtk.ResponseType.YES:
                        os.system('xdg-open '+updateinfo['link'])
                    dlg.destroy()
                        
            except:
                print('Error update check')
            Gdk.threads_leave()
    
    def linkLabel(self, lbltext, connectfunction):
        """ Like a label, clickable. https://stackoverflow.com/questions/5822191/ """
        lbl = Gtk.Label(lbltext, xalign=1);
        lbl.set_has_window(True)
        lbl.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        lbl.override_color(Gtk.StateFlags.NORMAL,  Gdk.RGBA(0.0, 0.0, 0.8, 1.0))
        lbl.connect("button-press-event", connectfunction)
        return lbl
        
    def userFile(self, name):
        """ Returns available filename in user data dir for this app. """
        mydir = os.path.join(GLib.get_user_data_dir(),'repeater-START')
        if not os.path.exists(mydir):
            os.mkdir(mydir)
        return os.path.join(mydir,name)


    def displayNodes(self):
        start = time.time();
        self.osm.image_remove_all()
        minimum = self.settingsDialog.getMinFilter()
        maximum = self.settingsDialog.getMaxFilter()
        self.allrepeaters = []
        irlpfile = self.userFile('irlp.txt')
        repeatersfile = self.userFile('repeaters.json')
        if os.path.exists(irlpfile):
            with open(irlpfile) as repfile:
                for line in repfile:
                    try:
                        self.addRepeaterIcon(IRLPNode(line), minimum, maximum)
                    except ValueError as e:
                        print(e)
        else:
            print('WARNING IRLP FILE NOT LOADED')
        if os.path.exists(repeatersfile):
            for repeater in json.load(open(repeatersfile)):
                #IRLP has been done in direct pull above.
                if repeater['group'] != 'IRLP':
                    self.addRepeaterIcon(HearHamRepeater(repeater), minimum, maximum)
        else:
            print('WARNING: REPEATERS FILE NOT LOADED')
        #print('DISPLAYNODES took '+str(time.time()-start))
    
    def credit_mapbox(self, obj, obj2):
        os.system('xdg-open https://www.mapbox.com/about/maps/')
    def credit_osm(self, obj, obj2):
        os.system('xdg-open http://www.openstreetmap.org/about/')
    def improvement_link(self, obj, obj2):
        os.system('xdg-open https://www.mapbox.com/map-feedback/')
    
    def addRepeaterIcon(self, repeater, minimum, maximum):
        if(float(repeater.freq) >= minimum and
           float(repeater.freq) <= maximum ):
            if repeater.isDown():
                pixbuf = self.towerDownPic
            else:
                pixbuf = self.towerPic
            self.osm.image_add(repeater.lat, repeater.lon, pixbuf)
            self.allrepeaters.append(repeater)


    def disable_cache_toggled(self, btn):
        if btn.props.active:
            self.osm.props.tile_cache = osmgpsmap.MAP_CACHE_DISABLED
        else:
            self.osm.props.tile_cache = osmgpsmap.MAP_CACHE_AUTO

    def on_show_tooltips_toggled(self, btn):
        self.show_tooltips = btn.props.active

    def load_map_clicked(self, button):
        uri = self.repouri_entry.get_text()
        format = self.image_format_entry.get_text()
        if uri and format:
            if self.osm:
                #remove old map
                self.vbox.remove(self.osm)
            try:
                self.osm = osmgpsmap.Map(
                    repo_uri=uri,
                    image_format=format
                )
            except Exception:
                print( "ERROR:" )
                self.osm = osm.Map()
            self.vbox.pack_start(self.osm, True, True, 0)
            #self.osm.connect('button_release_event', self.map_clicked)
            self.osm.show()

    def print_tiles(self):
        if self.osm.props.tiles_queued != 0:
            print( '%s tiles queued' % (self.osm.props.tiles_queued,) )
        return True

    def downloadBackground(self):
        if self.bgdl == None:
            if not(isMobileData()) or self.settingsDialog.getAllowMobile():
                self.bgdl = BackgroundDownload('https://hearham.com/nohtmlstatus.txt', self.userFile('irlp.txt'))
                self.bgdl.start()
                
                self.hearhamdl = BackgroundDownload('https://hearham.com/api/repeaters/v1', self.userFile('repeaters.json'))
                self.hearhamdl.start()
                
                self.checkUpdate = BackgroundDownload('https://hearham.com/api/updatecheck/linux', self.userFile('update.response'))
                self.checkUpdate.start()
                #Call again 10m later
            else:
                print('(not downloading, mobile)')
            GLib.timeout_add(600000, self.downloadBackground)
            if 0 == len(self.allrepeaters):
                GLib.timeout_add(10000, self.displayNodes)
        else:
            if self.bgdl.finished:
                self.displayNodes()
                if self.bgdl.success:
                    #Since we're online, do cleanup of any ancient files, clean up and also due to Mapbox TOS:
                    old = time.time() - 60*60*24*31
                    print( 'Going back to %s' % (old,))
                    for root, dirs, files in os.walk(self.osm.get_default_cache_directory()):
                        for jpg in files:
                            path = os.path.join(root, jpg)
                            if jpg.endswith('.jpg') and os.path.getmtime(path) < old:
                                print('Old, removing '+path)
                                os.remove(path)
                self.bgdl = None #and do create thread again:
                self.downloadBackground()
            

    def zoom_in_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom + 1)

    def zoom_out_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom - 1)

    def home_clicked(self, button):
        #self.getlocation() #Freezes up, odd.
        GObject.timeout_add(1, self.getlocation)
        
    def back_clicked(self, button):
        self.osm.set_center_and_zoom(self.lastLat, self.lastLon, 12)
        
    def searchToggle_clicked(self,button):
        if self.mode == 'search':
            self.mode = ''
        else:
            self.mode = 'search'
            self.search_text.grab_focus()
        self.setViews()
        
    def help_clicked(self, button):
        dlg = Gtk.MessageDialog(self, 
            0,Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            'Repeater-START is an application for amateur radio.\nWhen started, this app will try to update the latest repeaters.\n'+
            'If offline, the list will be loaded from user storage.\n'+
            'While online, you may hit "cache" and store map tiles for later use, and choose "add repeater" to contribute to the repeater database!\n'
            'All repeaters in the lower half of the screen are listed by distance, closest to the center map marker first.\n'+
            'Double click a repeater to center its position selected on the map.\n'+
            'Or click play to try to listen through a RTLSDR device.')
        response = dlg.run()
        dlg.destroy()
        
    def helpAbout_clicked(self,button):
        changed = datetime.datetime.fromtimestamp(os.path.getmtime(self.userFile('repeaters.json'))).strftime('%c')
        dlg = Gtk.MessageDialog(self, 
            0,Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            'Repeater-START v'+self.version+'\n'+
            'Showing The Amateur Repeaters Tool - The only open-source Linux desktop repeater app utilizing the open-data repeater database.\n\n'+
            'Your downloaded repeater database was updated:\n'+changed+
            '\nFor support/questions please use the Github issues or contact@hearham.live.')
        response = dlg.run()
        dlg.destroy()
    
    def pref_clicked(self,button):
        self.settingsDialog.show()
        
    def getlocation(self):
        self.lastLat = self.osm.props.latitude
        self.lastLon = self.osm.props.longitude
        try:
            clue = Geoclue.Simple.new_sync('repeaterstart',Geoclue.AccuracyLevel.EXACT,None)
            location = clue.get_location()
            self.osm.set_center_and_zoom(location.get_property('latitude'), location.get_property('longitude'), 12)
        except GLib.Error as err:
            print(err)
            GLib.idle_add(self.privacySettingsOpen)
            
    
    def privacySettingsOpen(self):
        Gdk.threads_enter()
        dlg = Gtk.MessageDialog(self, 
            0,Gtk.MessageType.WARNING,
            Gtk.ButtonsType.OK,
            'Please allow geolocation to use this feature.')
        response = dlg.run()
        dlg.destroy()
        subprocess.Popen(['gnome-control-center','privacy'])
        Gdk.threads_leave()


    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip, data=None):
        if keyboard_tip:
            return False

        if self.show_tooltips:
            #print(dir(osmgpsmap))
            #while True:
            #    print(eval(input('>')))
            #p = osmgpsmap.point_new_degrees(0.0, 0.0)
            p=self.osm.convert_screen_to_geographic(x, y)#, p)
            lat,lon = p.get_degrees()
            tooltip.set_markup("%+.4f, %+.4f" % (lat, lon ))
            return True

        return False

    def cache_clicked(self, button):
        bbox = self.osm.get_bbox()
        maxz = self.osm.props.max_zoom
        if maxz - self.osm.props.zoom > 2:
            maxz = self.osm.props.zoom + 2
        print( '%s max %s' % (self.osm.props.zoom, maxz) )
        self.osm.download_maps(
            *bbox,
            zoom_start=self.osm.props.zoom,
            zoom_end=maxz
        )
        
    def add_repeater_clicked(self, button):
        os.system('xdg-open "https://hearham.com/repeaters/add?lat=%s&lon=%s"' % (self.osm.props.latitude, self.osm.props.longitude) )

    def on_map_change(self, event):
        if self.renderedLat != self.osm.props.latitude or self.renderedLon != self.osm.props.longitude:
            #Center changed.
            self.renderedLat = self.osm.props.latitude
            self.renderedLon = self.osm.props.longitude

            t = time.time()
            text = 'Map Center: %s, latitude %s longitude %s' if self.mainScreen.get_width() > 800 else '%s, lat: %s lon: %s'
            if self.settingsDialog.getMinFilter()>-1 or self.settingsDialog.getMaxFilter()<1E99:
                text += ' (Repeaters filtered in settings)'
            self.latlon_entry.set_text(
                text % (
                    latLongToLocator(self.renderedLat, self.renderedLon),
                    round(self.osm.props.latitude, 4),
                    round(self.osm.props.longitude, 4)
                )
            )
            self.refreshListing()
            print('on_map_change time: %s' % (time.time()  - t))
    
    def refreshListing(self):
        # cursor lat,lon = self.osm.get_event_location(event).get_degrees()
        lat, lon = self.osm.props.latitude, self.osm.props.longitude
        maxkm = 500
        self.allrepeaters = sorted(self.allrepeaters, key = lambda repeater : repeater.distance(lat,lon))
        self.clearRows()
        self.playBtns = []
        added = 0
        #The settinds parser take a bit of time. Get number once.
        minimum = self.settingsDialog.getMinFilter()
        maximum = self.settingsDialog.getMaxFilter()
        for item in self.allrepeaters:
            distance = item.distance(lat,lon)
            if( distance < maxkm and 
              float(item.freq) >= minimum and
              float(item.freq) <= maximum ):
                self.addToList(item, lat,lon)
            added += 1
            if added > 100: #Listing excessively many makes it laggy, eg New England repeaters.
                break
        self.listbox.show_all()
    
    def addToList(self, repeater, lat, lon):
        row = Gtk.ListBoxRow()
        row.longitude = repeater.lon
        row.latitude = repeater.lat
        if isinstance(repeater, HearHamRepeater):
            row.repeaterID = repeater.id
            row.irlp = 0
        else:#Irlpnode:
            row.repeaterID = 0
            row.irlp = repeater.node
        # ^ for double click activate
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.add(hbox)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)
        innerhbox = Gtk.HBox()
        if float(repeater.freq) == 0:
            lbltext = "%s Reflector %s" if self.mainScreen.get_width() < 800 else "Node %s Reflector %s"
            label1 = Gtk.Label(lbltext % (repeater.node, repeater.callsign), xalign=0)
        else:
            if repeater.node:
                lbltext = "%s, %s at %smhz" if self.mainScreen.get_width() < 800 else "Node %s, %s at %smhz"
                lbltext = lbltext % (repeater.node, repeater.callsign, repeater.freq)
                label1 = Gtk.Label(lbltext, xalign=0)
                if repeater.isDown():
                    label1.set_markup('<s>'+lbltext+'</s>')
            else:
                lbltext = "%s, %smhz" % (repeater.callsign, repeater.freq)
                label1 = Gtk.Label(lbltext, xalign=0)
                if not repeater.status:
                    label1.set_markup('<s>'+lbltext+'</s>')
        try:
            int(repeater.status)
            linkknown = False
            for item in self.allrepeaters:
                if item.node == repeater.status:
                    gothere = Gtk.Button("Linked to %s " % (str(repeater.status),))
                    innerhbox.pack_start(gothere, False, False, 0)
                    gothere.connect('clicked', self.goLinkIRLP)
                    linkknown = True
            if not linkknown and int(repeater.status) >1:
                innerhbox.pack_start(Gtk.Label("Linked to %s. " % (repeater.status,), xalign=0),False, False, 0)
            label2 = Gtk.Label("PL %s, Offset %s, %s" % (repeater.pl, repeater.offset, repeater.url), xalign=0)
        except ValueError:
            #Not connected to number node
            if float(repeater.freq) == 0:
                label2 = Gtk.Label(repeater.city, xalign=0)
            else:
                label2 = Gtk.Label("%s. PL %s, Offset %s, %s" % (repeater.status, repeater.pl, repeater.offset, repeater.url), xalign=0)
        
        label3 = Gtk.Label(repeater.description, xalign=0)
        innerhbox.pack_start(label2, True, True, 0)
        
        label1.set_ellipsize(Pango.EllipsizeMode.END)
        label2.set_ellipsize(Pango.EllipsizeMode.END)
        label3.set_ellipsize(Pango.EllipsizeMode.END)
        if self.mainScreen.get_width() < 800:
            label2.modify_font(Pango.font_description_from_string("Ubuntu 10"))
            label3.modify_font(Pango.font_description_from_string("Ubuntu 10"))
        
        if self.mainScreen.get_width() < 800:
            #mobile
            label1.modify_font(Pango.font_description_from_string("Ubuntu Bold 12"))
        else:
            label1.modify_font(Pango.font_description_from_string("Ubuntu Bold 22"))
        vbox.pack_start(label1, True, True, 5)
        vbox.pack_start(innerhbox, True, True, 0)
        vbox.pack_start(label3, True, True, 5)
        km = repeater.distance(lat,lon)
        if self.settingsDialog.getUnit() == 'mi':
            km = km*.62137119
        
        distlbl = Gtk.Label( '%s %s ' % ( int(km*10)/10, self.settingsDialog.getUnit() ))
        playbtn = Gtk.Button()
        playbtn.set_image(Gtk.Image(icon_name='media-playback-start',
                      icon_size=self.PLAYSIZE))
        #playbtn.set_label('') Makes icon disappear, on many systems with button icon turned off.
        playbtn.selFrequency = repeater.freq
        if repeater.freq == self.playingfreq:
            playbtn.set_image(Gtk.Image(icon_name='media-playback-stop',
                      icon_size=self.PLAYSIZE))
        else:
            playbtn.set_image(Gtk.Image(icon_name='media-playback-start',
                      icon_size=self.PLAYSIZE))
        playbtn.connect('clicked', self.playpause)
        rightbox = Gtk.VBox()
        rightbox.pack_start(distlbl, False, True, 10)
        rightbox.pack_start(playbtn, True, True, 0)
        hbox.pack_start(rightbox, False, True, 0)
        
        #These two arrays should correspond!
        self.GTKListRows.append(row)
        self.playBtns.append(playbtn)
        self.listbox.add(row)
        
    def playpause(self, btn):
        if btn.selFrequency != self.playingfreq:
            self.playRTLSDR(btn.selFrequency)
            self.playingfreq = btn.selFrequency
            for b in self.playBtns:
                b.set_image(Gtk.Image(icon_name='media-playback-start',
                      icon_size=self.PLAYSIZE))
            #All others are stopped.
            btn.set_image(Gtk.Image(icon_name='media-playback-stop',
                      icon_size=self.PLAYSIZE))
        else:
            if self.rtllistener:
                self.rtllistener.proc.kill()
            self.playingfreq = None
            btn.set_image(Gtk.Image(icon_name='media-playback-start',
                      icon_size=self.PLAYSIZE))

    def goLinkIRLP(self, btn):
        label = btn.get_label()
        print(label)
        label = label.replace('Linked to','').strip()
        for item in self.allrepeaters:
            if item.node == label:
                self.osm.set_center(item.lat, item.lon)

    def on_button_release(self, osm, event):
        pass # Not the right lat/lon props here.

    def on_button_press(self, osm, event):
        state = event.get_state()
        lat,lon = self.osm.get_event_location(event).get_degrees()
        print('clicked %s,%s' % (lat,lon))
        near = 999999
        nearest = None
        self.allrepeaters = sorted(self.allrepeaters, key = lambda repeater : repeater.distance(lat,lon))
        cnt = 0
        return
        for item in self.allrepeaters:
            distance = item.distance(lat,lon)
            self.addToList(item, lat,lon)
            print(distance)
            cnt += 1
            if cnt > 5:
                break
        self.listbox.show_all()

        left    = event.button == 1 and state == 0
        middle  = event.button == 2 or (event.button == 1 and state & Gdk.ModifierType.SHIFT_MASK)
        right   = event.button == 3 or (event.button == 1 and state & Gdk.ModifierType.CONTROL_MASK)

        #work around binding bug with invalid variable name
        GDK_2BUTTON_PRESS = getattr(Gdk.EventType, "2BUTTON_PRESS")
        GDK_3BUTTON_PRESS = getattr(Gdk.EventType, "3BUTTON_PRESS")

        if event.type == GDK_3BUTTON_PRESS:
            if middle:
                if self.last_image is not None:
                    self.osm.image_remove(self.last_image)
                    self.last_image = None
        elif event.type == GDK_2BUTTON_PRESS:
            if left:
                self.osm.gps_add(lat, lon, heading=random.random()*360)
            if middle:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size ("poi.png", 24,24)
                self.last_image = self.osm.image_add(lat,lon,pb)
            if right:
                pass


    def playRTLSDR(self, mhz):
        if self.rtllistener:
            self.rtllistener.proc.kill()
        # -l 450 is higher squelch.
        cmd = 'rtl_fm -M fm -f '+mhz+'M -l 450 | play -r 24k -t raw -e s -b 16 -c 1 -V1 -'
        print(cmd)
        self.rtllistener = RTLSDRRun( cmd )
        self.rtllistener.start()
            
    def cleanup(self, obj):
        stateObj = {
            'lat': self.renderedLat, 
            'lon': self.renderedLon,
            'zoom': self.osm.props.zoom
        }
        with open(self.userFile('lastPosition.json'), 'w') as outfile:
            outfile.write(json.dumps(stateObj))
        if self.rtllistener:
            self.rtllistener.proc.kill()
        Gtk.main_quit()
    

if __name__ == "__main__":
    u = UI()
    u.show_all()
    u.setViews()
    if os.name == "nt": Gdk.threads_enter()
    Gtk.main()
    if os.name == "nt": Gdk.threads_leave()
