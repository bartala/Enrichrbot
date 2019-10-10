import pandas as pd
import json
import os,os.path
import tweepy
import random
from tweepy import OAuthHandler, Stream, StreamListener
from dotenv import load_dotenv
import nltk
from nltk.tokenize import RegexpTokenizer
nltk.download('stopwords')
from nltk.corpus import stopwords
import difflib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import sys
import time

load_dotenv()
PTH = os.environ.get('PTH_T') 
# PTH="/home/maayanlab/enrichrbot/Talk_Back/" # PTH="/users/alon/desktop/Talk_Back/"

CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"

# temp credentials
CONSUMER_KEY_T=os.environ.get('CONSUMER_KEY_T')
CONSUMER_SECRET_T=os.environ.get('CONSUMER_SECRET_T')
ACCESS_TOKEN_T=os.environ.get('ACCESS_TOKEN_T')
ACCESS_TOKEN_SECRET_T=os.environ.get('ACCESS_TOKEN_SECRET_T')

# enrichr credentials
CONSUMER_KEY_E=os.environ.get('CONSUMER_KEY_E')
CONSUMER_SECRET_E=os.environ.get('CONSUMER_SECRET_E')
ACCESS_TOKEN_E=os.environ.get('ACCESS_TOKEN_E')
ACCESS_TOKEN_SECRET_E=os.environ.get('ACCESS_TOKEN_SECRET_E') 

list_of_genes = pd.read_csv(os.path.join(PTH,'data/QA.csv'))
list_of_genes = list_of_genes['gene'].tolist()
list_of_genes = [x.lower() for x in list_of_genes]

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
#
#This goes to a link and takes a screenshot
def link_to_screenshot(link=None, output=None, zoom='100 %', browser=None):
  print('Capturing screenshot...')
  time.sleep(2)
  browser.get(link)
  time.sleep(5)
  browser.execute_script("document.body.style.zoom='{}'".format(zoom))
  time.sleep(5)
  os.makedirs(os.path.dirname(output), exist_ok=True)
  browser.save_screenshot(output)
  return output
#  
def CreateTweet(harmonizome_link,archs4_link,geneshot_link,pharos_link):
  # init browser
  browser = init_selenium(CHROMEDRIVER_PATH, windowSize='1600,1200')
  # create and save screenshots
  screenshots = [
    link_to_screenshot( link=harmonizome_link, output=os.path.join(PTH, "screenshots", "harmo.png"), browser=browser, zoom='0.75'),
    link_to_screenshot( link=archs4_link, output=os.path.join(PTH, "screenshots", "archs4.png"), browser=browser, zoom='0.75'),
    link_to_screenshot( link=geneshot_link, output=os.path.join(PTH, "screenshots", "gsht.png"), browser=browser, zoom='0.75'),
    link_to_screenshot( link=pharos_link, output=os.path.join(PTH, "screenshots", "pharos.png"), browser=browser, zoom='0.75'),
  ]
  browser.quit()
  return(screenshots)
# 
def Tweet(message, screenshots, tweet_id):
  auth_EnrichrBot = tweepy.OAuthHandler(CONSUMER_KEY_E, CONSUMER_SECRET_E)
  auth_EnrichrBot.set_access_token(ACCESS_TOKEN_E, ACCESS_TOKEN_SECRET_E)
  api_EnrichrBot =tweepy.API(auth_EnrichrBot, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
  if api_EnrichrBot.verify_credentials():
    if len(screenshots)==0:
      print(message)
      api_EnrichrBot.update_status(status=message, in_reply_to_status_id = tweet_id , auto_populate_reply_metadata=True)
    else:
      ps = [api_EnrichrBot.media_upload(screenshot) for screenshot in screenshots]
      media_ids_str = [p.media_id_string for p in ps]
      print(message)
      api_EnrichrBot.update_status(media_ids=media_ids_str, status = message, in_reply_to_status_id = tweet_id , auto_populate_reply_metadata=True)
  else:
    print("enrichrbot credentials validation failed")
#
class MyStreamListener(tweepy.StreamListener):
  def on_data(seld, data):
    print(data)
    data = json.loads(data)
    tweet_id = data['id_str']
    text = (data['text']).lower()
    stop_words = set(stopwords.words('english'))
    stop_words.add('botenrichr')
    stop_words.add('@')
    tokenizer = RegexpTokenizer(r'\w+')
    tokens = tokenizer.tokenize(text) # remove punctuation
    tokens = [w for w in tokens if not w in stop_words] # remove english stop words
    user_id = data['user']['id_str']
    sim = []
    screenshots = []
    # do not reply to Enrichrbot
    if user_id == '1146058388452888577':
      print("skiping this tweet by Enrichrbot")
      return True
    else:
      # find the gene name in text
      for token in tokens:
        try:
          index_value = list_of_genes.index(token)
          gene = token.upper()
          db = random.choice(['autorif','generif'])
          geneshot_link = "https://amp.pharm.mssm.edu/geneshot/index.html?searchin=" + gene + "&searchnot=&rif=" + db
          harmonizome_link = 'http://amp.pharm.mssm.edu/Harmonizome/gene/' + gene
          archs4_link = 'https://amp.pharm.mssm.edu/archs4/gene/' + gene
          pharos_link = 'https://pharos.nih.gov/targets/' + gene
          screenshots = CreateTweet(geneshot_link,harmonizome_link,archs4_link,pharos_link)
          message ="Explore prior knowledge & functional predictions for {} using:\n{}\n{}\n{}\n{}\n{}"
          message = message.format(gene.upper(),geneshot_link,harmonizome_link,archs4_link,pharos_link,"@MaayanLab @DruggableGenome @IDG_Pharos @BD2KLINCSDCIC")
          break
        except ValueError:
          index_value = -1
          sim.append( ",".join(difflib.get_close_matches(token, list_of_genes,n=1) ) )
      if (index_value==-1):
        if len(sim)>0:
          sim = list(set(sim))
          sim = [x.upper() for x in sim]
          sim = list(filter(None, sim))
          if len(sim)==0:
            message = "Please reply: @BotEnrichr gene_name. \n For example: @BotEnrichr INS"
          else:
            message = "I'm confused. Did you mean {}? Please reply: @BotEnrichr gene_name. \n For example: @BotEnrichr {}".format(" or ".join(sim), max(sim, key=len))
        else:
          message = 'please reply: @BotEnrichr gene_name. \n For example: @BotEnrichr INS'
      Tweet(message,screenshots,tweet_id)   
    return True
  #
  def on_error(self, status_code):
    if status_code == 420:
      print(status_code)
      # returning False in on_data disconnects the stream
    return False


if __name__ == '__main__':
  try:
    auth = tweepy.OAuthHandler(CONSUMER_KEY_T, CONSUMER_SECRET_T)
    auth.set_access_token(ACCESS_TOKEN_T, ACCESS_TOKEN_SECRET_T)
    api = tweepy.API(auth,wait_on_rate_limit=True,wait_on_rate_limit_notify=True)
    myStreamListener = MyStreamListener()
    myStream = Stream(api.auth, myStreamListener)
    print("listener is up")
    myStream.filter(track=['@BotEnrichr'], is_async=True)
  except Exception as e:
    print(e)
# myStream.running = False # stop stream