#!/usr/bin/env python

# ****************************************
# +++  Registry Updater for
# +++  Extensions and Vocabularies
# ****************************************


import sys, string, urllib, traceback, os, json, datetime
from xml.etree.ElementTree import ElementTree
from urllib import FancyURLopener

RS_BASE="/var/www/rs.gbif.org/"
NS_DC="http://purl.org/dc/terms/"
NS_EXT="http://rs.gbif.org/extension/"
# default issued date 
MIN_DATE = datetime.date(datetime.MINYEAR, 1, 1)

class Extension:
  def __init__(self):
    self.identifier=None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
    self.issued=None
    self.isLatest=False
  def __repr__(self):
    return """EXT %s Issued:%s (latest=%s) >>%s<< %s [%s]""" % (self.identifier,self.issued,self.isLatest,self.title,self.description,self.subject)
    
class Vocabulary:
  def __init__(self):
    self.identifier = None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
    self.issued = None
    self.isLatest=False
  def __repr__(self):
    return """VOC %s Issued:%s (latest=%s) >>%s<< %s [%s] """ % (self.identifier,self.issued,self.isLatest,self.title,self.description,self.subject)

class UrlOpener(FancyURLopener):
  version = 'GBIF sync extensions'

def writeExtensions(dir, urls):
  f = open(dir + 'extensions.json', 'w')
  processUrls(f, urls, 'extensions')
  f.close()

def writeVocabs(dir, urls):
  f = open(dir + 'vocabularies.json', 'w')
  processUrls(f, urls, 'thesauri')
  f.close()

def processUrls(fp, urls, rootElement):
  """Retrieve a list of objects by their url, sort them by their issued 
     date, update each object indicating if it is the latest issued or 
     not, and write each object to the JSON file"""
  fp.write('{"%s":[\n' % rootElement)
  allObjects = [] 
  for url in urls:
    print "Processing %s" % url
    obj = parseUrl(url)
    if obj != None:
        if obj.identifier != None:
            allObjects.append(obj) 
        else:
            print "Missing identifier in %s. Ignore" % url
  # sort by issued date, starting with newest dates
  allObjects = sorted(allObjects, key=getIssuedDate, reverse=True)
  # iterate through objects and indicate whether it is the latest or not
  identifiers = [] 
  for obj in allObjects:
    if (obj.identifier is not None and obj.identifier not in identifiers):
      identifiers.append(obj.identifier) 
      obj.isLatest=True
    else:
      print 'The extension or vocabulary with URL %s issued %s is deprecated or superseded by one in production' % (obj.url, obj.issued)
  # write each object to the JSON file
  first = True;
  for obj in allObjects:
    if (not first):
      fp.write(',\n')
    json.dump(obj.__dict__, fp, default=json_serial)
    first = False;
  fp.write('\n]}')
  return allObjects

def getIssuedDate(x):
  """Return the issued date, using default if issued date was None"""
  return x.issued or MIN_DATE

def json_serial(obj):
  """JSON serializer for objects not serializable by default json code
     For datime.date objects, return ISO format, e.g. yyyy-mm-dd
  """
  if isinstance(obj, datetime.date):
    serial = obj.isoformat()
    return serial

def parseUrl(url):
  """Download the XML document at a given URL. Parse the XML and
     construct either an Extension or Vocabulary depending on the
     contents of the XML document. At the end, return the object 
     constructed""" 
  try:
    f = UrlOpener().open(url)
    tree = ElementTree()
    tree.parse(f)
    f.close()
    doc = tree.getroot()
    if (doc.tag=="{%s}extension"%NS_EXT):
      obj=Extension()
      obj.identifier=doc.attrib.get('rowType')
    else:
      obj=Vocabulary()
      obj.identifier=doc.attrib.get('{%s}URI'%NS_DC)
    obj.url=url
    obj.title=doc.attrib.get('{%s}title'%NS_DC)
    obj.description=doc.attrib.get('{%s}description'%NS_DC)
    obj.subject=doc.attrib.get('{%s}subject'%NS_DC)
    # convert YYYY-MM-DD string date into datetime.date object
    strDate=doc.attrib.get('{%s}issued'%NS_DC) 
    if (strDate is not None):
      obj.issued=datetime.datetime.strptime(strDate, "%Y-%m-%d").date()
    return obj
  except:
    print "Oops, cant parse url %s" % url
    print '-'*60
    traceback.print_exc(file=sys.stdout)
    print '-'*60
    return None
  

def listExtensions(basedir, baseurl):
  urls = []
  print "WALK DIR "+basedir
  for fn in os.listdir(basedir):
    if fn.startswith("."):
      continue
    p=os.path.join(basedir,fn)
    if os.path.isdir(p):
      urls.extend( listExtensions(basedir+fn+"/", baseurl+fn+"/") )
    else:
      if (fn.lower().endswith(".xml")):
        url = baseurl+fn
        print " found extension at "+url
        urls.append(url)
  return urls

def listExternal(basedir):
  return json.load(open(basedir+"external.json"))

def listVocabularies(basedir, baseurl):
  urls = []
  print "WALK DIR "+basedir
  for fn in os.listdir(basedir):
    if fn.startswith("."):
      continue
    p=os.path.join(basedir,fn)
    if os.path.isdir(p):
      urls.extend( listVocabularies(basedir+fn+"/", baseurl+fn+"/") )
    else:
      if (fn.lower().endswith(".xml")):
        url = baseurl+fn
        print " found vocabulary at "+url
        urls.append(url)
  return urls
  
if __name__ ==  "__main__":
  print 'LOCATED RS.GBIF.ORG FILESYSTEM AT: '+RS_BASE
  
  print 'UPDATE PRODUCTION EXTENSION FILE'
  externalProd=listExternal(RS_BASE+"extension/")
  urlsCore = listExtensions(RS_BASE+"core/","http://rs.gbif.org/core/")
  urlsExt  = listExtensions(RS_BASE+"extension/","http://rs.gbif.org/extension/")
  writeExtensions(RS_BASE, urlsCore+urlsExt+externalProd)
  print 'UPDATE PRODUCTION VOCABULARY FILE'
  urlsVoc = listVocabularies(RS_BASE+"vocabulary/","http://rs.gbif.org/vocabulary/")
  writeVocabs(RS_BASE, urlsVoc)

  print 'UPDATE SANDBOX EXTENSION FILE'
  externalDev=listExternal(RS_BASE+"sandbox/extension/")
  urlsSandbox = listExtensions(RS_BASE+"sandbox/extension/","http://rs.gbif.org/sandbox/extension/")
  urlsSandboxCore = listExtensions(RS_BASE+"sandbox/core/","http://rs.gbif.org/sandbox/core/")
  writeExtensions(RS_BASE+'sandbox/', urlsCore+urlsExt+urlsSandbox+externalProd+externalDev+urlsSandboxCore)  
  print 'UPDATE SANDBOX VOCABULARY FILE'
  urlsVoc2 = listVocabularies(RS_BASE+"sandbox/vocabulary/","http://rs.gbif.org/sandbox/vocabulary/")
  writeVocabs(RS_BASE+'sandbox/', urlsVoc+urlsVoc2)
