#!/usr/bin/python3
"""
Repeater START - Showing The Amateur Repeaters Tool
(C) 2019 Luke Bryan.
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
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango
import time
import random
from gi.repository import cairo

from gi.repository import Geoclue
import math
import shutil
import urllib.request
from math import pi, sin, cos, sqrt, atan2, radians

from IRLPNode import IRLPNode
from HearHamRepeater import HearHamRepeater

GObject.threads_init()
Gdk.threads_init()

from threading import Thread

from gi.repository import OsmGpsMap as osmgpsmap
print( "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap._version))

assert osmgpsmap._version == "1.0"

class DummyMapNoGpsPoint(osmgpsmap.Map):
    def do_draw_gps_point(self, drawable):
        pass
GObject.type_register(DummyMapNoGpsPoint)

        
class RTLSDRRun(Thread):
    def __init__(self, cmd):
        Thread.__init__(self)
        self.cmd = cmd
        
    def run(self):
        #cmd = 'rtl_fm -M fm -f '+self.freq+'M -l 202 | play -r 24k -t raw -e s -b 16 -c 1 -V1 -'
        cmds = self.cmd.split('|')
        self.proc = subprocess.Popen(cmds[0].split(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        subprocess.check_output(cmds[1].split(),stdin=self.proc.stdout)
        for line in iter(self.proc.stdout.readline, b''):
            line = line.decode('utf-8')
            #print(line)

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



class DummyLayer(GObject.GObject, osmgpsmap.MapLayer):
    def __init__(self):
        GObject.GObject.__init__(self)

    def do_draw(self, gpsmap, gdkdrawable):
        pass
        #Gdk.cairo_set_source_pixbuf(cr, pixbuf, 10, 10)
        #surface=Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        
        #surface = cairo.ImageSurface(
        #    cairo.FORMAT_RGB24, 10, 10)
        #dc = cairo.Context(surface)
        #dc = cairo.
        #dc.set_source_rgb(1, 1, 1)
        #dc.paint()
        #gpsmap.do_draw_gps_point(gpsmap,surface)
        #REPL to explore eg "dir(gpsmap)"
        #while True:
        #    print("enter")
        #    print(eval(input()))

    def do_render(self, gpsmap):
        pass
        #image = Gtk.Image()
        #image.set_from_file('signaltower.svg')
        #pixbuf = image.get_pixbuf()
        #gpsmap.image_add(42.32, -122.87, pixbuf)
        

    def do_busy(self):
        return False

    def do_button_press(self, gpsmap, gdkeventbutton):
        return False
GObject.type_register(DummyLayer)

class UI(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.version = '0.3'
        self.set_default_size(500, 500)
        self.connect('destroy', self.cleanup)
        self.set_title('RepeaterSTART GPS Mapper')
        self.vbox = Gtk.VBox(False, 0)
        self.add(self.vbox)
        self.unit = 'mi' #or km
        self.renderedLat = None
        self.renderedLon = None
        
        self.rtllistener = None
        self.playingfreq = None
        self.PLAYSIZE = Gtk.IconSize.BUTTON
        
        self.mainScreen = Gdk.Screen.get_default()
        self.osm = osmgpsmap.Map(
            repo_uri='https://api.mapbox.com/styles/v1/programmin/ck7jtie300p7e1iqi1ow2yvi3/tiles/256/#Z/#X/#Y?access_token=pk.eyJ1IjoicHJvZ3JhbW1pbiIsImEiOiJjazdpaXVpMTEwbHJ1M2VwYXRoZmU3bmw4In0.3UpUBsTCOL5zvvJ1xVdJdg',
                image_format='jpg'
        )#user_agent="mapviewer.py/%s" % osmgpsmap._version)
        osd = osmgpsmap.MapOsd(
                        show_dpad=True,
                        show_zoom=True,
                        show_crosshair=True)
        
        icon_app_path = '/usr/share/icons/hicolor/scalable/apps/repeaterSTART.svg'
        if os.path.exists(icon_app_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_app_path)
            surface=Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        
        self.osm.layer_add(
                    osd
        )
        self.osm.layer_add(
                    DummyLayer()
        )
        #Adding image in the render code causes infinite loop.
        icon_app_path = '/usr/share/icons/hicolor/scalable/apps/repeaterSTART.svg'
        if os.path.exists(icon_app_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_app_path)
            self.set_icon(pixbuf)
        
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
        
        help_button = Gtk.Button()
        help_button.set_image(Gtk.Image(icon_name='help-browser',
                      icon_size=21))
        help_button.connect('clicked', self.help_clicked)
        help_about_button = Gtk.Button()
        help_about_button.set_image(Gtk.Image(icon_name='help-about',
                      icon_size=21))
        help_about_button.connect('clicked', self.helpAbout_clicked)
        
        home_button.connect('clicked', self.home_clicked)
        back_button = Gtk.Button(stock=Gtk.STOCK_GO_BACK)
        back_button.connect('clicked', self.back_clicked)
        
        cache_button = Gtk.Button('Cache')
        cache_button.connect('clicked', self.cache_clicked)
        add_button = Gtk.Button('Add Repeater')
        add_button.connect('clicked', self.add_repeater_clicked)
        
        overlay = Gtk.Overlay()
        overlay.add(self.osm)
        top_container = Gtk.VBox()
        leftright_container = Gtk.HBox()
        mapboxlogo = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale('mapbox.svg',width=80,height=25,preserve_aspect_ratio=True))
        leftright_container.pack_start(mapboxlogo, False, False, 0)
        leftright_container.pack_end(self.linkLabel(' Improve this map', self.improvement_link), False, False, 0)
        leftright_container.pack_end(self.linkLabel(' (c) openstreetmap ', self.credit_osm), False, False, 0)
        leftright_container.pack_end(self.linkLabel(' (c) mapbox ', self.credit_mapbox), False, False, 0)
        
        top_container.pack_end(leftright_container, False, False, 0)
        self.vbox.pack_start(overlay, True, True, 0)
        overlay.add_overlay(top_container)
        overlay.set_overlay_pass_through(top_container,True)
        #overlay.set_overlay_pass_through(mapboxlink,False)
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(home_button, False, True, 0)
        hbox.pack_start(back_button, False, True, 0)
        hbox.pack_start(cache_button, False, True, 0)
        hbox.pack_start(add_button, False, True, 0)
        hbox.pack_start(help_button, False, True, 0)
        hbox.pack_start(help_about_button, False, True, 0)

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

        GObject.timeout_add(500, self.print_tiles)
        GObject.timeout_add(1000, self.downloadBackground)
        self.bgdl = None

        self.listbox = Gtk.ListBox()

        #listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        self.vbox.pack_start(scrolled, True, True, 0)
        self.GTKListRows = []
        self.playBtns = []
        GObject.idle_add(self.updateMessage)
        
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
        self.osm.image_remove_all()
        self.allrepeaters = []
        irlpfile = self.userFile('irlp.txt')
        repeatersfile = self.userFile('repeaters.json')
        if os.path.exists(irlpfile):
            with open(irlpfile) as repfile:
                for line in repfile:
                    try:
                        self.addRepeaterIcon(IRLPNode(line))
                    except ValueError as e:
                        print(e)
        else:
            print('WARNING IRLP FILE NOT LOADED')
        if os.path.exists(repeatersfile):                
            for repeater in json.load(open(repeatersfile)):
                #IRLP has been done in direct pull above.
                if repeater['group'] != 'IRLP':
                    self.addRepeaterIcon(HearHamRepeater(repeater))
        else:
            print('WARNING REPEATERS FILE NOT LOADED')
    
    def credit_mapbox(self, obj, obj2):
        os.system('xdg-open https://www.mapbox.com/about/maps/')
    def credit_osm(self, obj, obj2):
        os.system('xdg-open http://www.openstreetmap.org/about/')
    def improvement_link(self, obj, obj2):
        os.system('xdg-open https://www.mapbox.com/map-feedback/')
    
    def addRepeaterIcon(self, repeater):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale('signaltower.svg',width=20,height=20,preserve_aspect_ratio=True)
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
            self.bgdl = BackgroundDownload('https://hearham.com/nohtmlstatus.txt', self.userFile('irlp.txt'))
            self.bgdl.start()
            
            self.hearhamdl = BackgroundDownload('https://hearham.com/api/repeaters/v1', self.userFile('repeaters.json'))
            self.hearhamdl.start()
            
            self.checkUpdate = BackgroundDownload('https://hearham.com/api/updatecheck/linux', self.userFile('update.response'))
            self.checkUpdate.start()
            #Call again 10m later
            GObject.timeout_add(600000, self.downloadBackground)
            if 0 == len(self.allrepeaters):
                GObject.timeout_add(10000, self.displayNodes)
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
        
    def help_clicked(self, button):
        dlg = Gtk.MessageDialog(self, 
            0,Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            'Repeater-START is an application for amateur radio.\nWhen started, this app will try to update the latest repeaters.\n'+
            'If offline, the list will be loaded from user storage.\n'+
            'While online, you may hit "cache" and store map tiles for later use, and choose "add repeater" to contribute to the repeater database!\n'
            'All repeaters in the lower half of the screen are listed by distance, closest to the center map marker first.')
        response = dlg.run()
        dlg.destroy()
        
    def helpAbout_clicked(self,button):
        dlg = Gtk.MessageDialog(self, 
            0,Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            'Repeater-START v'+self.version+'\n'+
            'Showing The Amateur Repeaters Tool - The only open-source Linux desktop repeater app utilizing the open-data repeater database.')
        response = dlg.run()
        dlg.destroy()
        
    def getlocation(self):
        self.lastLat = self.osm.props.latitude
        self.lastLon = self.osm.props.longitude
        clue = Geoclue.Simple.new_sync('repeaterstart',Geoclue.AccuracyLevel.EXACT,None)
        location = clue.get_location()
        self.osm.set_center_and_zoom(location.get_property('latitude'), location.get_property('longitude'), 12)

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
        if maxz - self.osm.props.zoom > 3:
            maxz = self.osm.props.zoom + 3
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
            text = 'Map Center: latitude %s longitude %s' if self.mainScreen.get_width() > 800 else 'lat: %s lon: %s'
            self.latlon_entry.set_text(
                text % (
                    round(self.osm.props.latitude, 4),
                    round(self.osm.props.longitude, 4)
                )
            )
            # cursor lat,lon = self.osm.get_event_location(event).get_degrees()
            lat, lon = self.osm.props.latitude, self.osm.props.longitude
            maxkm = 500
            self.allrepeaters = sorted(self.allrepeaters, key = lambda repeater : repeater.distance(lat,lon))
            for r in self.GTKListRows:
                r.destroy()
            self.playBtns = []
            added = 0
            for item in self.allrepeaters:
                distance = item.distance(lat,lon)
                if( distance < maxkm):
                    self.addToList(item, lat,lon)
                added += 1
                if added > 100: #Listing excessively many makes it laggy, eg New England repeaters.
                    break
            self.listbox.show_all()
            print('time: %s' % (time.time()  - t))
    
    def addToList(self, repeater, lat, lon):
        row = Gtk.ListBoxRow()
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
                label1 = Gtk.Label(lbltext % (repeater.node, repeater.callsign, repeater.freq), xalign=0)
            else:
                lbltext = "%s, %smhz" % (repeater.callsign, repeater.freq)
                label1 = Gtk.Label(lbltext, xalign=0)
        try:
            int(repeater.status)
            for item in self.allrepeaters:
                if item.node == repeater.status:
                    gothere = Gtk.Button("Linked to "+item.node)
                    innerhbox.pack_start(gothere, False, False, 0)
                    gothere.connect('clicked', self.goLinkIRLP)
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
        if self.unit == 'mi':
            km = km*.62137119
        
        distlbl = Gtk.Label( '%s %s ' % ( int(km*10)/10, self.unit ))
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
        label = label.replace('Linked to ','')
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
            #if distance < near:
            #    nearest = item
            #    near = distance
        # print( "nearest: "+str(near))
        # print( nearest.node )
        # print( nearest.callsign )
        # print( nearest.state )
        # print( nearest.freq )
        # print( nearest.owner )
        # print( nearest.url )
        # print( '================' )

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
        if self.rtllistener:
            self.rtllistener.proc.kill()
        Gtk.main_quit()
    

if __name__ == "__main__":
    u = UI()
    u.show_all()
    if os.name == "nt": Gdk.threads_enter()
    Gtk.main()
    if os.name == "nt": Gdk.threads_leave()
