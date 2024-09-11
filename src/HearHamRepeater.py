#!/usr/bin/python3
from Repeater import Repeater

class HearHamRepeater(Repeater):
    def __init__(self, jsonObject):
        """ Unpack the line to the properties of this class: """
        self.id = jsonObject['id']
        self.callsign = jsonObject['callsign']
        self.description = jsonObject['description']
        self.owner = jsonObject['callsign']
        self.status = jsonObject['operational']
        self.url = 'https://hearham.com/repeaters/'+str(jsonObject['id'])
        self.mode = jsonObject['mode']
        self.node = jsonObject['internet_node']
        self.group = jsonObject['group']
        self.lat = float(jsonObject['latitude'])
        self.lon = float(jsonObject['longitude'])
        self.city = jsonObject['city']
        self.pl = jsonObject['encode']
        self.freq = jsonObject['frequency']/1000000
        self.offset = jsonObject['offset']/1000000
