#!/usr/bin/python3
from Repeater import Repeater
# Deprecated. See HearHamRepeater.py for one in use.
class IRLPNode(Repeater):
    def __init__(self, line):
        """ Unpack the line to the properties of this class: """
        [self.node, self.callsign, self.city, self.state, self.country, self.status, self.record, self.install, self.lat, self.lon, self.lastupdate, self.freq, self.offset, self.pl, self.owner, self.url, self.lastchange, self.avrsstatus] = line.split('\t')
        self.lat = float(self.lat)
        self.lon = float(self.lon)
        #try:
        self.offset = float(self.offset)/1000
        #except ValueError as e:
        #    print("EEK"+e)
        if float(self.freq) == 0:
            self.description = "Owned by %s" % (self.owner,)
        else:
            self.description = "Owned by %s in %s" % (self.owner, self.city)
    
    def __str__(self):
        return 'IRLP node %s in %s, status=%s, freq=%s' % (self.node,self.city,self.status,self.freq)
