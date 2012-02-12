#!/usr/bin/env python
#######################################
# get_quad.py
# 
# Fetch the USGS quad map for a given latitude and longitude from LibreMaps.org.
# This will only work for the continental USA!
#
# Note: requires the argparse module from http://code.google.com/p/argparse/ for
# use on python versions < 2.7, as optparse will not handle negative numbers.
#
# Copyright 2011 Seth Just
# This program is free software licensed under the Creative Commons 
# Attribution-ShareAlike 3.0 Unported License. To view a copy of this license,
# visit http://creativecommons.org/licenses/by-sa/3.0/
#######################################

import urllib
from argparse import ArgumentParser

def getDRGName(lat, lon):
  # Generate the filename for a USGS 7.5x7.5 minute quad from the given latitude and longitude,
  # using the conventions descirbed at http://topomaps.usgs.gov/drg/drg_name.html
  ngrids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
  wgrids = ['1', '2', '3', '4', '5', '6', '7', '8']
  
  # we assume that we're in the US, so longitude will be negative
  assert(lon < 0)
  lon *= -1 

  dlat = int(lat)
  dlon = int(lon)

  glat = ngrids[int(8*(lat-dlat))]
  glon = wgrids[int(8*(lon-dlon))]

  return ("%2d%3d"%(dlat,dlon), glat+glon)

def getStateCode(lat, lon):
  # Get the state code for a given latitude and longitude from GeoNames.org
  # Modules for REST/XML request from GeoNames
  from xml.etree import ElementTree as ET
  
  # Request the political subdivision that the coordinates fall into
  subdiv = ET.parse(
      urllib.urlopen("http://api.geonames.org/countrySubdivision?lat=" + str(lat) + "&lng=" + str(lon) + "&username=sethjust")
      )
  
  # Try parsing the response, exit if we fail, as this is necessary information
  try:
    region = subdiv.getiterator("adminCode1")[0].text
  except:
    print "Could not get state name from GeoNames; exiting"
    exit(1)
  
  return region

def DLQuad(lat, lon, state, verbose):
  # Get the filename for the quad we're interested in
  degs, quad = getDRGName(lat, lon)

  # URLs look like http://www.archive.org/download/usgs_drg_or_45122_d6/o45122d6.tif
  #            and http://www.archive.org/download/usgs_drg_or_45122_d6/o45122d6.tfw 
  fmtdic = {"state":state, "degs":degs, "quad":quad}
  baseurl = "http://www.archive.org/download/usgs_drg_%(state)s_%(degs)s_%(quad)s/" % fmtdic
  fname = "o%(degs)s%(quad)s" % fmtdic

  if verbose:
    print "downloading quad", fname

  for ext in ['.tif', '.tfw']:
    url = baseurl+fname+ext
    urllib.urlretrieve(url, fname+ext)
    if verbose:
      print "downloaded", url
class NoGPSError (Exception): pass

def get_lat_lon():
  # GPSd Python bindings
  import gps
  
  # Create GPS object
  session = gps.gps()
  
  # Set GPS object as an iterator over reports from GPSd
  session.stream(gps.WATCH_ENABLE|gps.WATCH_NEWSTYLE)
  
  # Loop until we get a report with lat and lon. The limit of 5 loops should be more than enough -- my gps never takes more than three when it has a lock
  i = 0
  while (1):
    try:
      session.next()
      lat, lon = session.data['lat'], session.data['lon']
      break
    except:
      if (i > 5): raise NoGPSError 
      i += 1

  return [lat, lon]

#######################################
# Start Main Program
#######################################

# Parse command line options
parser = ArgumentParser(description="Get DRG USGS quad for given latitude and longitude from LibreMaps.org")

parser.add_argument("-q", "--silent", dest="verbose", action="store_false", default=True, help="don't produce any output")
parser.add_argument("-s", "--state", dest="state", default=False, help="Postal abbr. for the state in which the quad falls, so we don't need to look it up")

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-g", "--gps", dest="gps", action="store_true", default="False", help="get coordinates from GPSd")
group.add_argument("-c", "--coords", dest="coords", nargs=2, metavar="COORD", default=None, help="specify latitude N and longitude E (respectively) in decimal degrees; longitude should be negative, as all maps fall in the western hemisphere")
#group.add_argument("lat", type=float, metavar="LAT", help="latitude N in decimal degrees")
#group.add_argument("lon", type=float, metavar="LON", help="longitude E in decimal degrees (should be negative, as we're in the US)")

args = parser.parse_args()

if args.coords == None:
  try:
    args.coords = get_lat_lon()
  except NoGPSError:
    print "Could not get coordinates from GPS. Exiting."
    exit(1)

lat, lon = args.coords[0], args.coords[1]
if args.verbose:
  print "got %f, %f from GPS" % (lat, lon)

if not args.state:
  args.state = getStateCode(lat, lon)

args.state = args.state.lower()

DLQuad(lat, lon, args.state, args.verbose)
