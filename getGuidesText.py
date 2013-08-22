#!/usr/bin/env python3
"""
Due to the Drupal databases being on the crazy side, it seems
to be easier to crawl the guides and extract the information 
and text we need and store it in a table together.
"""

from bs4 import BeautifulSoup
from urllib.request import urlopen

import datetime
import json
import os
import os.path
import postgresql
import re
import time
import urllib.parse
import urllib.request


DATADIR = './guideData'
DB_NAME = 'guideDB'
DB_HOST = 'localhost'
DB_USER = 'postgres'

DB = postgresql.open(host=DB_HOST, database=DB_NAME, user=DB_USER)


# Fetch the English Guides to extract information from
guideFile = urlopen("http://biblio-dev.laurentian.ca/research/guides")
guideHtml = guideFile.read()
guideFile.close()

# Fetch the French Guides to extract information from
guideFrFile = urlopen("http://biblio-dev.laurentian.ca/research/fr/guides")
guideFrHtml = guideFrFile.read()
guideFrFile.close()

# Filter the English URLs you want
soup = BeautifulSoup(guideHtml)
guideAll = soup.find_all(href=re.compile("/research/guides/"))
# Home page does not have the /guides in the URL
# so in order for it to be included, must extract it 
# individually
guideService = soup.find_all(href=re.compile("/research/services"))
guideAll.append(guideService[0])

# Filter the French URLs you want
soupFr = BeautifulSoup(guideFrHtml)
guideFrAll = soupFr.find_all(href=re.compile("/research/fr/guides/"))
# Get the French Home page as well
guideServiceFr = soupFr.find_all(href=re.compile("research/fr/services"))
guideFrAll.append(guideServiceFr[0])

# Store wanted URLs in an array for further processing
GUIDELINKS = []
for link in guideAll:
  GUIDELINKS.append(link.get('href'))
for link in guideFrAll:
  GUIDELINKS.append(link.get('href'))

def init_db():
  # Initialize the database

  DB.execute("DROP TABLE IF EXISTS guide")
  DB.execute("""
    CREATE TABLE guide (title TEXT, url TEXT, ocr TEXT, 
    tsv TSVECTOR)
  """)
  DB.execute("CREATE INDEX tsv_idx ON guide USING GIN(tsv)")
  DB.execute("""
    CREATE TRIGGER tsv_update BEFORE INSERT OR UPDATE ON guide
    FOR EACH ROW EXECUTE PROCEDURE
    tsvector_update_trigger(tsv, 'pg_catalog.english', ocr)
  """)

def load_db(details):
  # Add the information to the database

  if 'text' not in details:
    print("ERR: Got to load_db. No text found for %s" % (details['title']))
    return

  ins = DB.prepare("""
    INSERT INTO guide(title, url, ocr)
    VALUES ($1, $2, $3)
  """)
  ins(
    details['title'],
    details['link'],
    details['text']
  ) 

def get_fulltext(link):
  # Get all the text from the page

  urlFile = urlopen("http://biblio-dev.laurentian.ca" + link)
  fileHtml = urlFile.read()
  urlFile.close()

  text = BeautifulSoup(fileHtml)

  fname = os.path.join(DATADIR, 'fulltext/', text.title.string + '.json')
  if os.access(fname, os.R_OK):
    contents = open(fname, "rb").read()
  else:
    try:
      contents = text.get_text()
      out = open(fname, "w")
    except Exception as exc:
      print("Err: Failed to get full-text for" + text.title.string)
      return ''
    else:
      with out:
        out.write(contents)

  # Repair hyphenation at column boundaries
  try:
    contents = contents.decode('utf-8')
    contents = re.sub(r'-\s*$\n', '', contents, flags=re.MULTILINE)
  except Exception as exc:
    print("WARN: Failed to decode full-text of" + text.title.string)
    contents = str(contents)

  return contents

def get_details(link):
  # Get the page details for the Research Guides

  pageFile = urlopen("http://biblio-dev.laurentian.ca" + link)
  pageHtml = pageFile.read()
  pageFile.close()

  info = BeautifulSoup(pageHtml)

  details = {}
  dts = bytearray()

  # Need to isolate just the title of the guide
  fullTitle = info.title.string
  parts = re.split('\|', fullTitle)
  title = parts[0]

  fname = os.path.join(DATADIR,'details/', title + '.json')
  if os.access(fname, os.R_OK):
    dts = open(fname, "rb").read()
  else:
    time.sleep(1)
    try:
      dts = '{"title":' + title + ', "link":"http://biblio-dev.laurentian.ca' + link + '}'
      out = open(fname, "w")
    except Exception as exc:
      print("ERR: In get_details. Could not fetch details for" + link)
      return None
    else:
      with out:
        out.write(dts)

  # grab the title of the page
  details['title'] = title
  # store the url for the page
  details['link'] = str(link)
  # Get the page text
  details['text'] = get_fulltext(link)

  return details

def get_page(link):
  # Get an indiviual page from the list of all guides

  details = get_details(link)
  if details:
    load_db(details)

if __name__ == "__main__":
  os.makedirs(DATADIR, exist_ok=True)
  os.makedirs(os.path.join(DATADIR, 'details'), exist_ok=True)
  os.makedirs(os.path.join(DATADIR, 'fulltext'), exist_ok=True)
  init_db()
  for l in GUIDELINKS:
    if l == 'http://biblio.laurentian.ca/research/guides/math-and-computer-science': continue
    if l == 'http://biblio.laurentian.ca/research/fr/guides/informatique-et-math%C3%A9matiques': continue
    get_page(l)
