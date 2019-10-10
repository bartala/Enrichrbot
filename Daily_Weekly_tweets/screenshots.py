from dotenv import load_dotenv
import os
import os.path
import sys
import tweepy
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import requests
import time
import random
import json
load_dotenv(verbose=True)

WEEK = str(sys.argv[1])
GENESHOT_URL = 'https://amp.pharm.mssm.edu/geneshot/geneset.html?genelist='
ENRICHR_URL =  'https://amp.pharm.mssm.edu/Enrichr'
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
PTH = os.environ.get('PTH') # PTH = '/home/maayanlab/enrichrbot/' # PTH = '/users/alon/desktop/enrichrbot/'

# Submit geneset to enrichr
def submit_to_enrichr(geneset=[], description=''):
  print('Submitting to enrichr {}...'.format(geneset))
  genes_str = '\n'.join(str(v) for v in geneset)
  payload = {
      'list': (None, genes_str),
      'description': (None, description)
  }
  response = requests.post(ENRICHR_URL + '/addList', files=payload)
  if not response.ok:
      raise Exception('Error analyzing gene list')
  data = json.loads(response.text)
  enrichr_link = ENRICHR_URL + '/enrich?dataset={}'.format(data['shortId'])
  f = open(os.path.join(PTH,"screenshots/enrichr_link.txt"), "w")
  f.write(enrichr_link)
  f.close()
  return enrichr_link
 
# Submit geneset to geneshot  
def submit_to_geneshot(geneset=[]):
  print('Submitting to geneshot {}...'.format(geneset))
  # options:
    #rif:         generif/autorif (better use autorif)
    #similarity:  autorif/generif/enrichr/tagger/coexpression
    #https://amp.pharm.mssm.edu/geneshot/geneset.html?genelist=SOX2,TP53,RB1&rif=generif&similarity=tagger
  genes_str = ','.join(str(v) for v in geneset)
  geneshot_link = GENESHOT_URL + genes_str + '&rif=autorif&similarity=tagger'
  f = open(os.path.join(PTH,"screenshots/geneshot_link.txt"), "w")
  f.write(geneshot_link)
  f.close()
  return geneshot_link


def init_selenium(CHROMEDRIVER_PATH, windowSize='1080,1080'):
  print('Initializing selenium...')
  options = Options()
  options.add_argument('--headless')
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-extensions')
  options.add_argument('--dns-prefetch-disable')
  options.add_argument('--disable-gpu')
  options.add_argument('--window-size={}'.format(windowSize))
  driver = webdriver.Chrome(
    executable_path=CHROMEDRIVER_PATH,
    options=options,
  )
  return driver


#This goes to a link and takes a screenshot
def link_to_screenshot(link=None, output=None, zoom='100 %', browser=None):
  print('Capturing screenshot...')
  time.sleep(3)
  browser.get(link)
  time.sleep(6)
  browser.execute_script("document.body.style.zoom='{}'".format(zoom))
  time.sleep(6)
  os.makedirs(os.path.dirname(output), exist_ok=True)
  browser.save_screenshot(output)
  return output
  
  
# create and save screenshots of geneshot and enricht
def main_report_tweet():
  # load genelist from the network
  genes = pd.read_csv(os.path.join(PTH,'bert/data/bert_full_week_'+WEEK+'.csv'), 
                                          dtype=str, error_bad_lines=False, encoding='utf-8')
  genes = set(genes['GeneSymbol'])
  # submit geneset to enrichr
  enrichr_link = submit_to_enrichr(genes, 'Enrichr Bot weekly Submission')
  # create geneshot link
  geneshot_link = submit_to_geneshot(genes)
   # init browser
  browser = init_selenium(CHROMEDRIVER_PATH, windowSize='1200,1250')
  # obtain a screenshot
  screenshots = [
    link_to_screenshot( link=enrichr_link, output=os.path.join(PTH, "screenshots", "enrichr_week.png"), browser=browser, zoom='1'),
    link_to_screenshot( link=geneshot_link, output=os.path.join(PTH, "screenshots", "geneshot_week.png"), browser=browser, zoom='0.75'),
  ]
  browser.quit()
  
  
if __name__=='__main__':
  main_report_tweet()
