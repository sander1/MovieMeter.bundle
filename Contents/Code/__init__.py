# MovieMeter Metadata Agent
from time import time

MM_ENDPOINT_URI = 'http://www.moviemeter.nl/ws'
MM_API_KEY = 'fnsxd7shhmc8gefjhz2zv0nrjwjbezhj'
MM_MOVIE_PAGE = 'http://www.moviemeter.nl/film/%d'

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
    if lang == 'nl':
      response = self.proxy.film.retrieveDetails(self.get_session_key(), int(metadata.id))
      if response != None:
        metadata.year = int(response['year'])

        if Prefs['rating']:
          metadata.rating = float(response['average'])*2 # Max 5 for MovieMeter, needs max 10 for Plex
        else:
          metadata.rating = None

        metadata.genres.clear()
        if Prefs['genres']:
          for genre in response['genres']:
            metadata.genres.add(genre)

        # Get title and summary from the website, not from the API
        movie_page = HTML.ElementFromURL(MM_MOVIE_PAGE % int(metadata.id))

        if Prefs['title']:
          metadata.title = movie_page.xpath('//div[@id="centrecontent"]/h1')[0].text.rsplit('(',1)[0].strip()
        else:
          metadata.title = ''

        if Prefs['summary']:
          metadata.summary = movie_page.xpath('//div[@id="film_info"]/text()[last()]')[0].strip()
        else:
          metadata.summary = ''

        poster = response['thumbnail'].replace('/thumbs', '')
        if Prefs['poster']:
          if poster not in metadata.posters:
            img = HTTP.Request(poster)
            metadata.posters[poster] = Proxy.Preview(img)
        else:
          del metadata.posters[poster]

  def get_session_key(self):
    if self.valid_till < int(time()):
      response = self.proxy.api.startSession(MM_API_KEY)
      self.session_key = response['session_key']
      self.valid_till = int(response['valid_till'])
    return self.session_key
