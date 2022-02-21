#!/usr/bin/env python3
#
# Registry Updater for extensions and vocabularies
#

import datetime
import json
import os
import sys
import traceback
import urllib.request
from string import Template
from xml.etree.ElementTree import ElementTree

RS_BASE=os.getcwd()+"/"
NS_DC="http://purl.org/dc/terms/"
NS_EXT="http://rs.gbif.org/extension/"
# default issued date
MIN_DATE = datetime.date(datetime.MINYEAR, 1, 1)
PRODUCTION = 0
SANDBOX = 1

# Templates for the HTML extension list.
HTML_EXTENSION_TEMPLATE_HEADER = Template("""
<!DOCTYPE HTML>
<html>
    <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>GBIF Registered Extensions</title>
        <link rel="stylesheet" type="text/css" href="/style/human.css"/>

        <style type="text/css">
            .definition {
                background: rgba(67%, 67%, 67%, 50%);
                padding: 0.5em 0 0 0.5em;
            }
            .definition .title {
                margin-top: 0.3em;
                margin-left: 2rem;
                font-weight: bold;
                font-size: 1.2em;
            }
            .definition .body {
                background: rgba(100%, 100%, 100%, 95%);
                margin-top: 0.5em;
                padding-top: 0.5em;
                margin-left: 2em;
                padding-left: 1em;
            }
            .definition .details {
                color: grey;
                font-size: 0.8em;
            }
        </style>
    </head>
    <body>
        <header>
            <img src="/style/logo-gbif.svg" alt="GBIF" width="115" height="46"/>
            <h1>Registered Extensions</h1>
        </header>

        <p>The following extensions are the latest versions of those registered with GBIF for $environment use.</p>

        <p>The list was last updated at $last_updated, and is also available in <a href="extensions.json">JSON format</a>.</p>
""")

HTML_EXTENSION_TEMPLATE_ENTRY = Template("""
        <a id="$identifier"></a>
        <div class="definition">
            <div class="title">
                <a href="$url">$title</a>
            </div>
            <div class="body">
                <p>$description</p>

                <table class="details">
                    <tr><th>Name</th><td>$name</td></tr>
                    <tr><th>Namespace</th><td>$namespace</td></tr>
                    <tr><th>RowType</th><td>$identifier</td></tr>
                    <tr><th>Issued</th><td>$issued</td></tr>
                    <tr><th>Keywords</th><td>$subject</td></tr>
                </table>
            </div>
        </div>
""")

HTML_EXTENSION_TEMPLATE_FOOTER = Template("""
    </body>
</html>
""")

ASIS_TEMPLATE = Template("""Status: 303 See Other
Location: $location
Content-Type: $contentType

See <a href="$location">$location</a>.
""")

class Extension:
  def __init__(self):
    self.identifier = None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
    self.issued = None
    self.isLatest = False
    self.namespace = None
    self.name = None
  def __repr__(self):
    return """EXT %s Issued:%s (latest=%s) >>%s<< %s [%s]""" % (self.identifier, self.issued, self.isLatest, self.title, self.description, self.subject)

class Vocabulary:
  def __init__(self):
    self.identifier = None
    self.url = None
    self.title = None
    self.description = None
    self.subject = None
    self.issued = None
    self.isLatest = False
    self.namespace = None
    self.name = None
  def __repr__(self):
    return """VOC %s Issued:%s (latest=%s) >>%s<< %s [%s] """ % (self.identifier, self.issued, self.isLatest, self.title, self.description, self.subject)

def writeExtensions(env, dir, urls):
  j = open(dir + 'extensions.json', 'w')
  h = open(dir + 'extensions.html', 'w')
  processUrls(j, h, urls, env, 'extensions')
  j.close()
  h.close()

def writeVocabs(env, dir, urls):
  f = open(dir + 'vocabularies.json', 'w')
  processUrls(f, None, urls, env, 'thesauri')
  f.close()

def processUrls(fp, html, urls, env, rootElement):
  """Retrieve a list of objects by their URL, sort them by their issue
     date, update each object indicating if it is the latest issued or
     not, and write each object to the JSON file."""

  allObjects = []
  for url in urls:
    print("Processing %s" % url)
    obj = parseUrl(url)
    if obj != None:
      if obj.identifier != None:
        allObjects.append(obj)
      else:
        print("Missing identifier in %s. Ignore" % url)

  # sort by issued date, starting with newest
  allObjects = sorted(allObjects, key=getIssuedDate, reverse=True)
  # iterate through objects and indicate whether it is the latest or not
  identifiers = []
  for obj in allObjects:
    if (obj.identifier is not None and obj.identifier not in identifiers):
      identifiers.append(obj.identifier)
      obj.isLatest=True
    else:
      print("The extension or vocabulary with URL %s issued %s is deprecated or superseded by one in production" % (obj.url, obj.issued))

  # write each object to the JSON file
  fp.write('{"%s":[\n' % rootElement)
  first = True;
  for obj in allObjects:
    if (first and html):
      html.write(HTML_EXTENSION_TEMPLATE_HEADER.substitute(
          last_updated=datetime.datetime.today().strftime("%H:%M:%S on %e %B %Y"),
          environment=('production' if (env == PRODUCTION) else 'development (sandbox)')
      ))
    if (not first):
      fp.write(',\n')

    # Write Apache HTTPD asis files to allow redirects like https://rs.gbif.org/terms/1.0/Distribution → https://rs.gbif.org/extension/gbif/1.0/distribution_2022-02-02.xml
    if (obj.isLatest and obj.identifier.startswith("http://rs.gbif.org/") and "#" not in obj.identifier):
        if (env != PRODUCTION and not obj.identifier.startswith("http://rs.gbif.org/sandbox/")):
            print("Refusing to create "+obj.identifier+" from the sandbox, adding sandbox/ to path")
            path = RS_BASE + obj.identifier.replace("http://rs.gbif.org/", "sandbox/")
        else:
            path = RS_BASE + obj.identifier.replace("http://rs.gbif.org/", "")
        # Some identifiers end with /, index.asis will be served
        if (path.endswith("/")):
            path = path + "index"
        asisFile = path + ".asis"
        asisDir = os.path.dirname(asisFile)
        if not os.path.isdir(asisDir):
            os.makedirs(asisDir)
        a = open(asisFile, 'w')
        a.write(ASIS_TEMPLATE.substitute(location=obj.url.replace("http://rs.gbif.org", "https://rs.gbif.org"), contentType='text/xml'))
        a.close()

    # Write HTML extensions list
    if (obj.isLatest and html):
        t = dict(
            identifier=obj.identifier,
            url=obj.url,
            title=obj.title,
            description=obj.description,
            name=obj.name,
            namespace=obj.namespace,
            issued=obj.issued,
            subject=obj.subject,
        )
        html.write(HTML_EXTENSION_TEMPLATE_ENTRY.substitute(t))

    # Write JSON extensions list
    # name and namespace are used in the HTML list, but not the JSON.
    del(obj.name)
    del(obj.namespace)
    json.dump(obj.__dict__, fp, default=json_serial, indent=2)

    first = False;

  fp.write('\n]}')
  if (html):
      html.write(HTML_EXTENSION_TEMPLATE_FOOTER.substitute())

  return allObjects

def getIssuedDate(x):
  """Return the issued date, using default if issued date was None"""
  return x.issued or MIN_DATE

def json_serial(obj):
  """JSON serializer for objects not serializable by default JSON code
     For datime.date objects, return ISO format, e.g. yyyy-mm-dd
  """
  if isinstance(obj, datetime.date):
    serial = obj.isoformat()
    return serial

def parseUrl(url):
  """Download the XML document at a given URL. Parse the XML and
     construct either an Extension or Vocabulary depending on the
     contents of the XML document. At the end, return the object
     constructed

     URLs beginning http://rs.gbif.org are instead retrieved
     relative to this script."""
  try:
    latestUrl = url.replace('http://rs.gbif.org/', "file://"+RS_BASE)
    tree = ElementTree()
    with urllib.request.urlopen(latestUrl) as response:
      tree.parse(response)
      response.close()
    doc = tree.getroot()
    if (doc.tag == "{%s}extension"%NS_EXT):
      obj = Extension()
      obj.identifier = doc.attrib.get('rowType')
    else:
      obj = Vocabulary()
      obj.identifier = doc.attrib.get('{%s}URI'%NS_DC)
    obj.namespace = doc.attrib.get('namespace')
    obj.name = doc.attrib.get('name')
    obj.url = url
    obj.title = doc.attrib.get('{%s}title'%NS_DC)
    obj.description = doc.attrib.get('{%s}description'%NS_DC)
    obj.subject = doc.attrib.get('{%s}subject'%NS_DC)
    # convert YYYY-MM-DD string date into datetime.date object
    strDate = doc.attrib.get('{%s}issued'%NS_DC)
    if (strDate is not None):
      obj.issued = datetime.datetime.strptime(strDate, "%Y-%m-%d").date()
    return obj
  except:
    print("Oops, can't parse URL %s" % url)
    print("-"*60)
    traceback.print_exc(file = sys.stdout)
    print("-"*60)
    exit(1)
    return None


def listExtensions(basedir, baseurl):
  urls = []
  print("WALK DIR "+basedir)
  for fn in os.listdir(basedir):
    if fn.startswith("."):
      continue
    p = os.path.join(basedir,fn)
    if os.path.isdir(p):
      urls.extend( listExtensions(basedir+fn+"/", baseurl+fn+"/") )
    else:
      if (fn.lower().endswith(".xml")):
        url = baseurl+fn
        print(" found extension at "+url)
        urls.append(url)
  return urls

def listExternal(basedir):
  return json.load(open(basedir+"external.json"))

def listVocabularies(basedir, baseurl):
  urls = []
  print("WALK DIR "+basedir)
  for fn in os.listdir(basedir):
    if fn.startswith("."):
      continue
    p = os.path.join(basedir,fn)
    if os.path.isdir(p):
      urls.extend( listVocabularies(basedir+fn+"/", baseurl+fn+"/") )
    else:
      if (fn.lower().endswith(".xml")):
        url = baseurl+fn
        print(" found vocabulary at "+url)
        urls.append(url)
  return urls

if __name__ ==  "__main__":
  print("LOCATED RS.GBIF.ORG FILESYSTEM AT: "+RS_BASE)

  print("UPDATE PRODUCTION EXTENSION FILE")
  externalProd = listExternal(RS_BASE+"extension/")
  urlsCore = listExtensions(RS_BASE+"core/","http://rs.gbif.org/core/")
  urlsExt = listExtensions(RS_BASE+"extension/","http://rs.gbif.org/extension/")
  writeExtensions(PRODUCTION, RS_BASE, urlsCore+urlsExt+externalProd)
  print("UPDATE PRODUCTION VOCABULARY FILE")
  urlsVoc = listVocabularies(RS_BASE+"vocabulary/","http://rs.gbif.org/vocabulary/")
  writeVocabs(PRODUCTION, RS_BASE, urlsVoc)

  print("UPDATE SANDBOX EXTENSION FILE")
  externalDev=listExternal(RS_BASE+"sandbox/extension/")
  urlsSandbox = listExtensions(RS_BASE+"sandbox/extension/","http://rs.gbif.org/sandbox/extension/")
  urlsSandboxCore = listExtensions(RS_BASE+"sandbox/core/","http://rs.gbif.org/sandbox/core/")
  writeExtensions(SANDBOX, RS_BASE+"sandbox/", urlsCore+urlsExt+urlsSandbox+externalProd+externalDev+urlsSandboxCore)
  print("UPDATE SANDBOX VOCABULARY FILE")
  urlsVoc2 = listVocabularies(RS_BASE+"sandbox/vocabulary/","http://rs.gbif.org/sandbox/vocabulary/")
  writeVocabs(SANDBOX, RS_BASE+"sandbox/", urlsVoc+urlsVoc2)
