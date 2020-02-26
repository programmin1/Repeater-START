#!/usr/bin/python3
from Repeater import Repeater

class IRLPNode(Repeater):
    def __init__(self, line):
        """ Unpack the line to the properties of this class: """
        [self.node, self.callsign, self.city, self.state, self.country, self.status, self.record, self.install, self.lat, self.lon, self.lastupdate, self.freq, self.offset, self.pl, self.owner, self.url, self.lastchange, self.avrsstatus] = line.split('\t')
        self.lat = float(self.lat)
        self.lon = float(self.lon)
        self.offset = int(self.offset)/1000
        if float(self.freq) == 0:
            self.description = "Owned by %s" % (self.owner,)
        else:
            self.description = "Owned by %s in %s" % (self.owner, self.city)
    
