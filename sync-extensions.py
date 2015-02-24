#!/usr/bin/env python

# ****************************************
# +++  Registry Updater for
# +++  Extensions and Vocabularies
# ****************************************


import sys, string, urllib, traceback, os, json
from xml.etree.ElementTree import ElementTree


RS_BASE="/var/www/rs.gbif.org/"
NS_DC="http://purl.org/dc/terms/"
NS_EXT="http://rs.gbif.org/extension/"


class Extension:
  def __init__(self):
    self.identifier=None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
  def __repr__(self):
    return """EXT %s >>%s<< %s [%s]""" % (self.identifier,self.title,self.description,self.subject)
    
class Vocabulary:
  def __init__(self):
    self.identifier = None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
  def __repr__(self):
    return """VOC %s >>%s<< %s [%s]""" % (self.identifier,self.title,self.description,self.subject)


def writeExtensions(dir, urls):
  f = open(dir + 'extensions.json', 'w')
  processUrls(f, urls, 'extensions')
  f.close()

def writeVocabs(dir, urls):
  f = open(dir + 'vocabularies.json', 'w')
  processUrls(f, urls, 'thesauri')
  f.close()

def processUrls(fp, urls, rootElement):
  fp.write('{"%s":[\n' % rootElement)
  first = True;
  for url in urls:
    print "\nProcessing %s" % url
    obj = parseUrl(url)
    if (obj is not None):
      if (not first):
        fp.write(',\n')
      json.dump(obj.__dict__, fp)
      first = False;
  fp.write('\n]}')
  

def parseUrl(url):
  try:
    f = urllib.urlopen(url)
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

def listExternal():
  return json.load(open(RS_BASE+"extension/external.json"))

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
  external=listExternal()
  urlsCore = listExtensions(RS_BASE+"core/","http://rs.gbif.org/core/");
  urlsExt  = listExtensions(RS_BASE+"extension/","http://rs.gbif.org/extension/");
  writeExtensions(RS_BASE, urlsCore+urlsExt+external)  
  print 'UPDATE PRODUCTION VOCABULARY FILE'
  urlsVoc = listVocabularies(RS_BASE+"vocabulary/","http://rs.gbif.org/vocabulary/");
  writeVocabs(RS_BASE, urlsVoc)

  print 'UPDATE SANDBOX EXTENSION FILE'
  urlsSandbox = listExtensions(RS_BASE+"sandbox/extension/","http://rs.gbif.org/sandbox/extension/");
  urlsSandboxCore = listExtensions(RS_BASE+"sandbox/core/","http://rs.gbif.org/sandbox/core/");
  writeExtensions(RS_BASE+'sandbox/', urlsCore+urlsExt+urlsSandbox+external+urlsSandboxCore)  
  print 'UPDATE SANDBOX VOCABULARY FILE'
  urlsVoc2 = listVocabularies(RS_BASE+"sandbox/vocabulary/","http://rs.gbif.org/sandbox/vocabulary/");
  writeVocabs(RS_BASE+'sandbox/', urlsVoc+urlsVoc2)
  
