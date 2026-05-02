#!/usr/bin/python3
import csv
import os
from gi.repository import GdkPixbuf

from Repeater import Repeater
from RepeaterStartCommon import userFile
import urllib

class CsvRepeaterListing():
    """ Hold repeater listing and list of repeaters """
    def __init__(self, filename):
        start = True
        data = False
        with open(filename) as csvfile:
            for row in csv.reader(csvfile, delimiter=',', quotechar='"'):
                if start:
                    if row[0].lower() == 'name':
                        self.name = row[1]
                    if row[0].lower().strip() == 'icon':
                        self.icon = row[1]
                #Which mode - top name, columns or data parsing?
                nonempty = [x for x in row if x]
                if len(nonempty) == 0:
                    start = False #separator
                elif not start and not data:
                    #Reading data, mode now:
                    self.cols = row
                    data = True
                    self.repeaters = []
                elif data:
                    r = Repeater()
                    setattr(r, 'node', '')
                    setattr(r, 'status', True) # up by default
                    setattr(r, 'irlp', 0) #not
                    for i in range(len(self.cols)):
                        #Set each attribute
                        setattr(r, self.cols[i], row[i])
                        if self.cols[i].find('freq') == 0:
                            setattr(r, 'freq', row[i])
                        if self.cols[i].find('lat') == 0:
                            setattr(r, 'lat', float(row[i]))
                        if self.cols[i].find('lon') == 0:
                            setattr(r, 'lon', float(row[i]))
                        if self.cols[i] == 'encode':
                            setattr(r, 'pl', row[i])
                        if self.cols[i].find('active') == 0:
                            active = False
                            if row[i].lower().find('active')==0:
                                active = True
                            if row[i].lower().find('true')==0:
                                active = True
                            if row[i].lower().find('up')==0:
                                active = True
                            setattr(r, 'status', active)
                            
                    self.repeaters.append(r)
        if not os.path.exists(self.iconFile()):
            #try:
            urllib.request.urlretrieve(self.icon, self.iconFile())
            #except:
            #    print('FAILED Download '+self.icon)
    def iconFile(self):
        """ Full filepath of expected icon file """
        return userFile('rpt-'+self.name)
    
    def getIcon(self):
        """ The downloaded icon to render for this particular tower type """
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.iconFile(),width=21,height=21,preserve_aspect_ratio=True)
        return pixbuf
                    
    def __str__(self):
        return ("Name: %s\nIcon: %s\nRepeaters: %s" % (self.name, self.icon, len(self.repeaters)) )
                
