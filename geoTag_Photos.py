"""
Steps to run on windows (python3 with packages):
  1.  Install anaconda3 for individual user (no admin required)
      a. https://anaconda.com/products/individual (scroll to the bottom for windows 64-bit installed)
  2.  Open 'Anaconda prompt' from the windows start menu
  3.  In a directory where you want this project loaded:
        'git clone https://github.com/cranejohnson/geoPhoto.git'
  4.  Run 'conda install -c conda-forge geojson'  to install geojson
  5.  Run 'conda install -c conda-forge exifread' to install exifread
  6.  In the geoPhoto directory run 'python geoTag_Photos.py'

"""



import sys
import xml.dom.minidom

import time
import subprocess
import configparser

import glob
import os.path
import imghdr
import zipfile
import exifread
import geomag

import webbrowser
from PIL import Image


from datetime import datetime


from geojson import Point, Feature, FeatureCollection, dump
import json




def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def GetFile(file_name):
  """Handles opening the file.

  Args:
    file_name: the name of the file to get

  Returns:
    A file
  """

  the_file = None

  try:
    the_file = open(file_name, 'rb')

  except IOError:
    the_file = None

  return the_file





def DmsToDecimal(degree_num, degree_den, minute_num, minute_den,
                 second_num, second_den):
  """Converts the Degree/Minute/Second formatted GPS data to decimal degrees.

  Args:
    degree_num: The numerator of the degree object.
    degree_den: The denominator of the degree object.
    minute_num: The numerator of the minute object.
    minute_den: The denominator of the minute object.
    second_num: The numerator of the second object.
    second_den: The denominator of the second object.

  Returns:
    A deciminal degree.
  """

  degree = float(degree_num)/float(degree_den)
  minute = float(minute_num)/float(minute_den)/60
  second = float(second_num)/float(second_den)/3600
  return degree + minute + second


def GetGps(data):
  """Parses out the GPS coordinates from the file.

  Args:
    data: A dict object representing the EXIF headers of the photo.

  Returns:
    A tuple representing the latitude, longitude, and altitude of the photo.
  """
  try:
    lat_dms = data['GPS GPSLatitude'].values
    long_dms = data['GPS GPSLongitude'].values
  except:
    print ("    No GPS Coordinates for Photo")
    return [0,0,0]


  if str(lat_dms[0]) == '0/0':
    print ("    No GPS Coordinates for Photo")
    return [0,0,0]
  latitude = DmsToDecimal(lat_dms[0].num, lat_dms[0].den,
                          lat_dms[1].num, lat_dms[1].den,
                          lat_dms[2].num, lat_dms[2].den)
  longitude = DmsToDecimal(long_dms[0].num, long_dms[0].den,
                           long_dms[1].num, long_dms[1].den,
                           long_dms[2].num, long_dms[2].den)
  if data['GPS GPSLatitudeRef'].printable == 'S': latitude *= -1
  if data['GPS GPSLongitudeRef'].printable == 'W': longitude *= -1
  altitude = None

  try:
    alt = data['GPS GPSAltitude'].values[0]
    altitude = alt.num/alt.den
    if data['GPS GPSAltitudeRef'] == 1: altitude *= -1

  except KeyError:
    altitude = 0

  return latitude, longitude, altitude


def CreateKmlDoc(title):
  """Creates a KML document."""

  kml_doc = xml.dom.minidom.Document()
  kml_element = kml_doc.createElementNS('http://www.opengis.net/kml/2.2', 'kml')
  kml_element.setAttribute('xmlns', 'http://www.opengis.net/kml/2.2')
  kml_element = kml_doc.appendChild(kml_element)
  document = kml_doc.createElement('Document')
  kml_element.appendChild(document)
  name = kml_doc.createElement('name')
  name.appendChild(kml_doc.createTextNode(title))
  document.appendChild(name)
  openstatus = kml_doc.createElement('open')
  openstatus.appendChild(kml_doc.createTextNode('1'))
  document.appendChild(openstatus)

  #style for GPS photos
  style = kml_doc.createElement('Style')
  style.setAttribute('id','GPSphoto')
  document.appendChild(style)
  lstyle = kml_doc.createElement('LabelStyle')
  style.appendChild(lstyle)
  scale = kml_doc.createElement('scale')
  scale.appendChild(kml_doc.createTextNode('0.0'))
  lstyle.appendChild(scale)
  istyle = kml_doc.createElement('IconStyle')
  style.appendChild(istyle)
  scale = kml_doc.createElement('scale')
  scale.appendChild(kml_doc.createTextNode('1.0'))
  istyle.appendChild(scale)
  icon = kml_doc.createElement('Icon')
  href = kml_doc.createElement('href')
  href.appendChild(kml_doc.createTextNode('http://maps.google.com/mapfiles/kml/pal4/icon49.png'))
  icon.appendChild(href)
  istyle.appendChild(icon)

  #style for noGPS photos
  style = kml_doc.createElement('Style')
  style.setAttribute('id','noGPSphoto')
  document.appendChild(style)
  lstyle = kml_doc.createElement('LabelStyle')
  style.appendChild(lstyle)
  scale = kml_doc.createElement('scale')
  scale.appendChild(kml_doc.createTextNode('0.0'))
  lstyle.appendChild(scale)
  istyle = kml_doc.createElement('IconStyle')
  style.appendChild(istyle)
  icon = kml_doc.createElement('Icon')
  istyle.appendChild(icon)

  folder = kml_doc.createElement('Folder')
  fname =kml_doc.createElement('name')
  fname.appendChild(kml_doc.createTextNode('Photos'))
  folder.appendChild(fname)
  folderid = kml_doc.createElement('id')
  folderid.appendChild(kml_doc.createTextNode('photos'))
  folder.appendChild(folderid)
  document.appendChild(folder)


  return kml_doc

def scrubKML(kml_doc):
  """
  This function looks through the KML file and finds photos without coordinates. It then
  assigns the average coordinates of the project so that if a user selects the photo
  from the menu on the left it will pop up in an average location and not at lat = 0
  lon = 0.

  Args:
    kml_doc: An XML document object.

  """

  avgLat = 0
  avgLon = 0
  avgElev = 0
  num = 0

  for node in kml_doc.getElementsByTagName('coordinates'):  # visit every node <bar />
    coordinates = node.firstChild.data

    lat,lon,elev = coordinates.split(',')
    if lat != '0':
      avgLat = float(lat) + avgLat
      avgLon = float(lon) + avgLon
      avgElev = float(elev) + avgElev
      num = num +1
  avgLat = avgLat/num
  avgLon = avgLon/num
  avgElev = avgElev/num
  for node in kml_doc.getElementsByTagName('coordinates'):  # visit every node <bar />
    coordinates = node.firstChild.data
    lat,lon,elev = coordinates.split(',')
    if lat == '0':
      node.firstChild.data = str(avgLat)+','+str(avgLon)+','+'-99999'

  return kml_doc


def CreatePhotoOverlay(kml_doc, file_name, the_file, file_iterator,resizeWidth):
  """Creates a PhotoOverlay element in the kml_doc element.

  Args:
    kml_doc: An XML document object.
    file_name: The name of the file.
    the_file: The file object.
    file_iterator: The file iterator, used to create the id.

  Returns:
    An XML element representing the PhotoOverlay.
  """



  photo_id = 'photo%s' % file_iterator
  folderId = '-'.join(splitall(file_name)[:-1])

  path,filename = os.path.split(file_name)

  fh = GetFile(file_name)
  tags = exifread.process_file(fh,details=False)
  fh.close()

  if not os.path.exists('geoPhotos'):
    os.mkdir('geoPhotos')

  print("Opening: "+file_name)

  im = Image.open(file_name)

  try:
    exif = im.info['exif']
  except:
    exif = False
    print('     No Exif Information')

  #Get image width and height and scale based on user width
  width, height = im.size

  newHeight = height/(width/resizeWidth)
  newsize = (int(resizeWidth), int(newHeight))
  im1 = im.resize(newsize)


  parts = filename.split('.')
  longname =  path.replace("/",'-')
  today = datetime.now()

  smallFileName = today.strftime("%Y%m%d")+'-'+longname+'-'+parts[0]+'_small.jpg'
  smallFileName = smallFileName.replace("--","-")
  if exif:
    im1 = im1.save('geoPhotos/'+smallFileName,'JPEG',exif=exif)
  else:
    im1 = im1.save('geoPhotos/'+smallFileName,'JPEG')

  im.close();


  try:
      timestamp = tags.get('EXIF DateTimeOriginal').__str__()
      date_obj = datetime.strptime(timestamp, '%Y:%m:%d %H:%M:%S')

  except:
      timestamp = 'No timestamp'
      date_obj = datetime.strptime("1900:1:1", '%Y:%m:%d')

  coords = GetGps(tags)

  GeoPoint = Point((coords[1],coords[0]))
  orientation = tags.get('Image Orientation').__str__()

  style = ""

  print(orientation)
  #Handle rotation in the Google earth popup
  if "180" in orientation:
      style = "style='-webkit-transform: rotate(-180deg);'"
  if "90 CCW"  in orientation:
      style = "style='-webkit-transform: rotate(90deg);'"
  if "90 CW"  in orientation:
      style = "style='-webkit-transform: rotate(90deg);'"

  kmlstyle = '#GPSphoto'
  kmlvis = '1'



  placeName = filename

  if coords[0] == 0:
    kmlstyle = '#noGPSphoto'
    kmlvis = '0'
    placeName = 'No GPS - '+filename
    #return


  po = kml_doc.createElement('Placemark')
  name = kml_doc.createElement('name')
  name.appendChild(kml_doc.createTextNode(placeName))
  snip = kml_doc.createElement('snippet')
  po.appendChild(snip)

  vis = kml_doc.createElement('visibility')
  vis.appendChild(kml_doc.createTextNode(kmlvis))

  if timestamp != 'No timestamp':
    timespan = kml_doc.createElement('TimeStamp')
    taken = kml_doc.createElement('when')
    taken.appendChild(kml_doc.createTextNode(date_obj.isoformat()))
    timespan.appendChild(taken)
    po.appendChild(timespan)

  description = kml_doc.createElement('description')
  base = os.path.splitext(file_name)[0]
  ext = os.path.splitext(file_name)[1]
  file_name = base + ext.lower()
  cdata = "<h3>Date: "+timestamp+"</h3><h3>Latitude: "+str(coords[0])+"</h3><h3>Longitude: "+str(coords[1])+"</h3><img src='geoPhotos/"+smallFileName+"' width=600 "+style+" >"

  description.appendChild(kml_doc.createCDATASection(cdata))
  po.appendChild(name)
  po.appendChild(description)
  styleurl = kml_doc.createElement('styleUrl')
  styleurl.appendChild(kml_doc.createTextNode(kmlstyle))
  po.appendChild(styleurl)

  point = kml_doc.createElement('Point')
  amode = kml_doc.createElement('altitudeMode')
  amode.appendChild(kml_doc.createTextNode('clampToGround'))
  point.appendChild(amode)

  coordtext = kml_doc.createElement('coordinates')


  value = str(coords[1])+","+str(coords[0])+","+str(coords[2])

  coordtext.appendChild(kml_doc.createTextNode(value))
  point.appendChild(coordtext)
  po.appendChild(point)


  exists = 0


  folder = kml_doc.getElementsByTagName('Folder')[0]
  for node in kml_doc.getElementsByTagName('Folder'):  # visit every node <bar />
    if node.getElementsByTagName("id"):
      name = node.getElementsByTagName("id")[0]
      if folderId == name.firstChild.data:
        folder = node
        exists = 1


  if exists == 0:
    #Folder does not exist so we need to make one
    photoPath = splitall(file_name)
    level = 0


    #remove the file name and set up folders in kml
    photoPath = photoPath[:-1]
    for part in photoPath:
      create = 1
      for node in folder.getElementsByTagName('Folder'):  # visit every node <bar />
          #print(node.toxml())
          if(node):
            name = node.getElementsByTagName("name")[0]
            if part == name.firstChild.data:
              #print('This folder Exists')
              folder = node
              create = 0
      if(create):
        nextfolder = kml_doc.createElement('Folder')
        fname =kml_doc.createElement('name')
        folderid = kml_doc.createElement('id')
        folderid.appendChild(kml_doc.createTextNode(folderId))
        fname.appendChild(kml_doc.createTextNode(part))
        nextfolder.appendChild(folderid)
        nextfolder.appendChild(fname)
        folder.appendChild(nextfolder)
        folder = nextfolder


  folder.appendChild(po)





  if "EXIF DateTimeOriginal" in tags:
      DateTime = tags.get('EXIF DateTimeOriginal').__str__()
      date_obj = datetime.strptime(DateTime, '%Y:%m:%d %H:%M:%S')
      takenTime = int(time.mktime(date_obj.timetuple()))

  else:
      takenTime = 0

  if "GPS GPSDate" in tags:
      GPSTime = tags.get('GPS GPSDate').__str__()
  else:
      GPSTime = 0

  if "GPS GPSImgDirection" in tags:
      num,den = tags.get('GPS GPSImgDirection').__str__().split( '/' )
      photoBearing = int((float(num)/float(den)))
      gm = geomag.GeoMag()
      magDec = gm.GeoMag(coords[0],coords[1]).dec
      print(magDec)
      photoBearing = photoBearing + magDec
  else:
      photoBearing = None


  return Feature(geometry=GeoPoint, properties={
      "visible"   : True,
      "bearing"   : photoBearing,
      "order"     : 0,
      "takenTime" : takenTime,
      "GPSDate"   : GPSTime,
      "Path"      : smallFileName})



def CreateKmlFile(baseDir,file_names, new_file_name,resizeWidth,title):
  """Creates the KML Document with the PhotoOverlays, and writes it to a file.
  Args:
    file_names: A list object of all the names of the files.
    new_file_name: A string of the name of the new file to be created.
  """
  features = []
  files = {}

  kml_doc = CreateKmlDoc(title)

  for file_name in file_names:
    the_file = GetFile(baseDir+'/'+file_name)
    if the_file is None:
     print ("'%s' is unreadable\n" % file_name)
     file_names.remove(file_name)
     continue
    else:
     files[file_name] = the_file
     the_file.close()



  file_iterator = 0

  for key in sorted(files.keys()):
  #for key in files.iterkeys():
    print('-------------------------------')
    print('Working on File: ' + str(key) )
    GeoFeature = CreatePhotoOverlay(kml_doc, key, files[key], file_iterator,resizeWidth)
    features.append(GeoFeature)
    file_iterator += 1

  #Put the photos points in order by datetime of photo
  features.sort(key=extract_time)
  num = 0;
  for feat in features:
    feat['properties']['order'] = num;
    num = num + 1;


  kml_doc = scrubKML(kml_doc)
  kml_file = open(new_file_name, 'w')
  kml_file.write(kml_doc.toprettyxml())
  feature_collection = FeatureCollection(features)
  return feature_collection

def extract_time(json):
    try:
        # Also convert to int since update_time will be string.  When comparing
        # strings, "10" is smaller than "2".
        return int(json['properties']['takenTime'])
    except KeyError:
        return 0




def main():

  rcode = subprocess.call([sys.executable, 'getInput.py'])

  geoPhotoDir = os.path.dirname(os.path.realpath(__file__))


  config = configparser.ConfigParser()
  config.readfp(open(r'parameters.input'))
  baseDir = config.get('geoPhoto', 'dir')
  webtitle = config.get('geoPhoto', 'title')
  description = config.get('geoPhoto', 'description')


  resizeWidth = int(config.get('geoPhoto', 'width'))

  print(baseDir)


  #value = input("Please enter path to top photo directory [enter for current directory]:")
  if len(baseDir) < 1:
    baseDir =os.getcwd()
  #print(f'You entered {value}')
  os.chdir(baseDir)
  filelist = []
  outFileName = os.path.split(baseDir)[1]
  print(outFileName)
  for subdir, dirs, files in os.walk(baseDir):
    for file in files:
        toss, file_extension = os.path.splitext(os.path.relpath(subdir+'/'+file))
        if 'geoPhotos' in subdir:
            continue
        if(imghdr.what(os.path.relpath(subdir+'/'+file)) == 'jpeg'):
          filelist.append(os.path.relpath(subdir+'/'+file,baseDir))
        else:
          print('File: '+os.path.relpath(subdir+'/'+file)+' is not an image file')

  print("Completed directory scan. Processing images...\n")
  filelist.sort()
  kmlFileName = time.strftime("GeoTagged_Photos_Processed %Y_%m_%d.kml")

  args = sys.argv[1:]
  if len(filelist) < 1:
    print ("No 'jpg' or 'jpeg' files found in directory")

  else:
    title = os.path.split(os.getcwd())[1]
    geoJsonCollection = CreateKmlFile(baseDir,filelist,kmlFileName,resizeWidth,title)
    geoJsonCollection['title'] = webtitle
    geoJsonCollection['description'] = description
    geoJsonCollection['processed'] = int(time.time())

    #input file
    fin = open(geoPhotoDir+"/LeafletMap_template.html", "rt")
    #output file to write the result to
    fout = open(baseDir+"/geoPhotos/"+title+"_map.html", "wt")
    #for each line in the input file
    for line in fin:
      #read replace the string and write to output file
      fout.write(line.replace('"<GEOJSON_PHOTOS>"', json.dumps(geoJsonCollection)))
    #close input and output files
    fin.close()
    fout.close()

    metaOut = open(baseDir+"/geoPhotos/"+title+".json", "wt")

    metaOut.write(json.dumps(geoJsonCollection, indent=4))
    metaOut.close()

    #timestr = time.strftime(baseDir+"/GeoTagged_Photos_Processed %Y_%m_%d.kmz")
    timestr = baseDir+"/"+title+".kmz"
    zf = zipfile.ZipFile(timestr, mode='w')
    kmlSmallImages = os.listdir('geoPhotos/')
    for file in kmlSmallImages:
      zf.write('geoPhotos/'+file)


    zf.write(kmlFileName)
    #zf.write("geoPhotos/"+title+"_map.html")
    #zf.write("geoPhotos/"+title+".json")
    zf.close()

  #remove kml file as it is not needed
  if os.path.exists(kmlFileName):
    os.remove(kmlFileName)

  print("Completed processing images...\n\n")
  print("Important:\nOpen "+baseDir+"/geoPhotos/"+title+".html in a browser window to test output.\n")
  print("Open "+baseDir+"/geoPhotos/"+title+".kmz in google earth.\n\n")


if __name__ == '__main__':
  main()
