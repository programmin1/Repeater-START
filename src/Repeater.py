#!/usr/bin/python3
from math import pi, sin, cos, sqrt, atan2, radians

class Repeater:
    def distance(self, lat,lon):
        """ Distance in km """
        earthR = 6373
        dlat = radians(lat-self.lat)
        dlon = radians(lon-self.lon)
        a = sin(dlat/2)**2 + cos(radians(self.lat)) * cos(radians(lat)) * sin(dlon/2)**2
        c = 2*atan2(sqrt(a), sqrt(1-a))
        return earthR*c
        
    def isDown(self):
        return not self.status or 'DOWN' == self.status
