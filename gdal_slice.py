#!/usr/bin/env python
#######################################
# gdal_slice.py
# 
# Python rewrite of gdal_slice.sh to slice a large GeoTIFF into 1280x1024 chunks
# for use by GPSDrive using GDAL's python bindings.
#
# Copyright 2011 Seth Just
# This program is free software licensed under the Creative Commons 
# Attribution-ShareAlike 3.0 Unported License. To view a copy of this license,
# visit http://creativecommons.org/licenses/by-sa/3.0/
#######################################

def getLatLon(indataset, pixel, line):
  # Calculates latitude and longitude for the center of a given pixel in the image.
  # From https://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/tolatlong.py

  # Read geotransform matrix and calculate ground coordinates
  geomatrix = indataset.GetGeoTransform()
  X = geomatrix[0] + geomatrix[1] * pixel + geomatrix[2] * line
  Y = geomatrix[3] + geomatrix[4] * pixel + geomatrix[5] * line

  # Shift to the center of the pixel
  X += geomatrix[1] / 2.0
  Y += geomatrix[5] / 2.0

  # Build Spatial Reference object based on coordinate system, fetched from the
  # opened dataset
  srs = osr.SpatialReference()
  srs.ImportFromWkt(indataset.GetProjection())

  srsLatLong = srs.CloneGeogCS()
  ct = osr.CoordinateTransformation(srs, srsLatLong)
  (lon, lat, height) = ct.TransformPoint(X, Y)
  
  return lat, lon

#######################################
# Start Main Program
#######################################

import os

# GDAL Modules
from osgeo import gdal, gdal_array, osr

# Parse command line options
from optparse import OptionParser
parser = OptionParser("Usage: %prog [options] FILENAME")

#parser.add_option("-f", "--fmt", "--format", dest="fmt", default="png", help="format in which to output map tiles. FMT must be one of {}")
# unimplemented, as gpsdrive will read most formats. currently this script will write to TIFF

parser.add_option("-o", "--overlap", dest="overlap", type="int", default=33, help="percentage tiles will overlap. should be at least 20%")

parser.add_option("-a", "--add", dest="add", action="store_true", default=False, help="write map info to map_koord.txt in current working directory")

parser.add_option("-m", "--map", action="store_const", const="map", default="map", dest="mtype", help="use *_map folders for output; use if input image is UTM. Default behavior")
parser.add_option("-t", "--topo", action="store_const", const="top", dest="mtype", help="use *_top folders for output; use if input image is not UTM")

parser.add_option("-v", "--verbose", action="count", dest="verbose", default=0, help="enable debugging output")

options, args = parser.parse_args()

if options.verbose > 2:
  print "Command line options:", options

try: assert(len(args) == 1)
except AssertionError:
  print "Error: You must provide a FILENAME!\n"
  parser.print_help()
  exit(1)

filename = args[0]

# Open file with GDAL
data = gdal.Open( filename, gdal.GA_ReadOnly )
if (data == None):
  print "Failed to open", filename, "for read."
  exit(1)

# Get image size
width = data.RasterXSize
height = data.RasterYSize

# Get data band
band = data.GetRasterBand(1)
color = band.GetRasterColorTable() # So that color data will be copied from files that use it

# Get pixel scale
geotransform = data.GetGeoTransform()
try: assert(geotransform[1] == geotransform[5]*-1)
except AssertionError:
  print "WARNING! WARNING! Pixel size differs in X and Y axes! Using X scale for scale factor"
scale = int(0.5 + (geotransform[1] * 2817.947378))

# Create output driver
#driver = data.GetDriver()
driver = gdal.GetDriverByName( "GTiff" )

# Create folder for output files
outpath = filename.split('.')[0] + "_" + options.mtype + "/"
gdal.Mkdir(outpath, os.stat('.').st_mode)

# Create file for writing map_koords
draftkoordfile = open(outpath + "map_koord_draft.txt", "w")

# Set up iteration over image grid
xsize, ysize = 1280, 1024

dx = int(xsize - (options.overlap * xsize / 100.0))
dy = int(ysize - (options.overlap * ysize / 100.0))

xseq = range(0, width-xsize, dx)
xseq.append(width - xsize)

yseq = range(0, height-ysize, dy)
yseq.append(height - ysize)

if options.verbose > 1:
  print "X intervals:", map(lambda x: (x, x+xsize), xseq)
  print "Y intervals:", map(lambda y: (y, y+ysize), yseq)

# Loop over image, generating subimages
for xoff in xseq:
  for yoff in yseq:
    # Set filename
    outfile = outpath + filename.split('.')[0] + "_" + str(xoff) + "_" + str(yoff) + ".tif"
    
    # Read tile data
    tile = band.ReadAsArray(xoff, yoff, xsize, ysize)
    
    # Create outfile
    out = driver.Create(outfile, xsize, ysize, 1)
    
    # Write data to file
    outband = out.GetRasterBand(1)
    outband.SetRasterColorTable(color)
    outband.WriteArray(tile)
    outband.FlushCache()

    lat, lon = getLatLon(data, xoff+(xsize/2), yoff+(ysize/2))
    draftkoordfile.write("%s %f %f %d\n" % (outfile, lat, lon, scale))

    if options.verbose:
      print "created", outfile, "with coords", "%.5f, %.5f" % (lat, lon)

draftkoordfile.flush()

if not options.add:
  exit()

mapkoordpath = "map_koord.txt"
if os.path.isfile(mapkoordpath):
  try:
    mapkoordfile = open(mapkoordpath, "r")
  except:
    print "Failed to open", mapkoordpath
    print "Not adding output to", mapkoordpath
    exit(1)
else: 
    print "Could not find", mapkoordpath
    print "Not adding output to", mapkoordpath
    exit(1)

if options.verbose:
  print "Merging", draftkoordfile.name, "into", mapkoordfile.name

# Initialize a dict
d = {}

# Read mapkoordfile into the dict
for l in mapkoordfile:
  p = l.split()
  d[p[0]] = l.strip()

# We know this exists, we just created it -- now we read it back in
draftkoordfile = open(outpath + "map_koord_draft.txt", "r")

# Read new values into dict
for l in draftkoordfile:
  p = l.split()
  d[p[0]] = l.strip()

# Open the koordfile for writing
mapkoordfile = open(mapkoordpath, "w")

for k in sorted(d.keys()):
#  print d[k]
  mapkoordfile.write(d[k]+"\n")
