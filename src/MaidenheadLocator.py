from __future__ import division
import re
from math import floor
#Roughly based on https://unclassified.software/files/source/MaidenheadLocator.cs

def locatorToLatLng(locator):
	locator = locator.strip().upper()
	values = False
	if re.match(r"^[A-R]{2}[0-9]{2}[A-X]{2}$", locator):
		values = {
			'lng': (ord(locator[0]) - ord('A')) * 20 + (ord(locator[2]) - ord('0'))*2 + (ord(locator[4]) - ord('A') +.5) / 12 - 180,
			'lat': (ord(locator[1]) - ord('A')) * 10 + (ord(locator[3]) - ord('0')) + (ord(locator[5]) - ord('A')+.5) / 24 - 90
		}
	elif re.match(r"^[A-R]{2}[0-9]{2}[A-X]{2}[0-9]{2}$", locator):
		values = {
			'lng': (ord(locator[0]) - ord('A')) * 20 + (ord(locator[2]) - ord('0'))*2 + (ord(locator[4]) - ord('A') ) / 12 + (ord(locator[6]) - ord('0') + .5) / 120 - 180,
			'lat': (ord(locator[1]) - ord('A')) * 10 + (ord(locator[3]) - ord('0')) + (ord(locator[5]) - ord('A') )/24 + (ord(locator[7]) - ord('0') +.5 ) / 240 - 90
		}
	elif re.match(r"^[A-R]{2}[0-9]{2}[A-X]{2}[0-9]{2}[A-X]{2}$", locator):
		values = {
			'lng': (ord(locator[0]) - ord('A')) * 20 + (ord(locator[2]) - ord('0'))*2 + (ord(locator[4]) - ord('A') ) / 12 + (ord(locator[6]) - ord('0') ) / 120 + (ord(locator[8]) - ord('A') +.5) / 120 / 24 - 180,
			'lat': (ord(locator[1]) - ord('A')) * 10 + (ord(locator[3]) - ord('0')) + (ord(locator[5]) - ord('A') )/24 + (ord(locator[7]) - ord('0') ) / 240 + (ord(locator[9]) - ord('A') +.5) / 240 / 224 - 90
		}
	return values

def latLongToLocator(lat,lon):
	locator = ''
	lat += 90
	lon += 180
	locator += chr(ord('A') + floor(lon/20))
	locator += chr(ord('A') + floor(lat/10))
	lon = lon % 20
	if lon < 0:
		lon += 20
	lat = lat % 10
	if lat < 0:
		lat += 10
	
	locator += chr(ord('0') + floor( lon/2))
	locator += chr(ord('0') + floor( lat))
	lon = lon % 2
	if lon < 0:
		lon += 2
	lat = lat % 1
	if lat < 0:
		lat += 1
	locator += chr(ord('A')+floor(lon*12))
	locator += chr(ord('A')+floor(lat * 24))
	lon = lon % (1/12)
	if lon < 0:
		lon += 1/12
	lat = lat % (1/24)
	if lat < 0:
		lat += 1/24
	return locator
