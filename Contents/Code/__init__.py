# MovieMeter Metadata Agent
from time import time

MM_ENDPOINT_URI = 'http://www.moviemeter.nl/ws'
MM_API_KEY = 'fnsxd7shhmc8gefjhz2zv0nrjwjbezhj'

def Start():
  HTTP.CacheTime = CACHE_1DAY

class MovieMeterAgent(Agent.Movies):
  name = 'MovieMeter'
  languages = ['nl']
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']

  def __init__(self):
    Agent.Movies.__init__(self)
    self.proxy = XMLRPC.Proxy(MM_ENDPOINT_URI, 'iso-8859-1')
    self.valid_till = 0

  def search(self, results, media, lang):
    mm_id = self.proxy.film.retrieveByImdb(self.get_session_key(), media.primary_metadata.id) # media.primary_metadata.id = IMDb-id
    if mm_id != None:
      results.Append(MetadataSearchResult(id=mm_id, score=100))

  def update(self, metadata, media, lang):
    response = self.proxy.film.retrieveDetails(self.get_session_key(), int(metadata.id))
    if response != None:
      metadata.title = unicode(response['title']).replace(u'\u0092', u'\u2019')
      metadata.year = int(response['year'])
      metadata.summary = unicode(response['plot']).replace(u'\u0092', u'\u2019')
      metadata.rating = float(response['average'])*2 # Max 5 for MovieMeter, needs max 10 for Plex

  def get_session_key(self):
    if self.valid_till < int(time()):
      response = self.proxy.api.startSession(MM_API_KEY)
      self.session_key = response['session_key']
      self.valid_till = int(response['valid_till'])

    return self.session_key
