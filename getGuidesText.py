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

"""
DATADIR = './guideData'
DB_NAME = 'insert Name here'
DB_HOST = 'localhost'
DB_USER = 'emily'

DB = postgresql.open(host=DB_HOST, database=DB_NAME, user=DB_USER)
"""
# Fetch the html that you want to extract information from
guideFile = urlopen("http://biblio-dev.laurentian.ca/research/guides")
guideHtml = guideFile.read()
guideFile.close()

# Filter the URLs you want
soup = BeautifulSoup(guideHtml)
guideAll = soup.find_all(href=re.compile("/research/guides/"))

# Store wanted URLs in an array for further processing
guideLinks = []
for link in guideAll:
  guideLinks.append(link.get('href'))

# Get details and full text from each of the guide pages
for i in guideLinks:
  if i == 'http://biblio.laurentian.ca/research/guides/math-and-computer-science': continue
  pageFile = urlopen("http://biblio-dev.laurentian.ca" + i)
  pageHtml = pageFile.read()
  pageFile.close()

  text = BeautifulSoup(pageHtml)
  ocr = text.get_text()
  title = text.title.string
  link = 'http://biblio-dev.laurentian.ca' + i
  print(text.title.string)
