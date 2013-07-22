MM_ENDPOINT_URI = 'http://www.moviemeter.nl/ws'
MM_API_KEY = 'fnsxd7shhmc8gefjhz2zv0nrjwjbezhj'
MM_MOVIE_PAGE = 'http://www.moviemeter.nl/film/%d'

def Start():
  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Plex Media Server/%s' % Platform.ServerVersion

class MovieMeterAgent(Agent.Movies):
  name = 'MovieMeter'
  languages = [Locale.Language.Dutch]
  primary_provider = False
  contributes_to = [
    'com.plexapp.agents.imdb',
    'com.plexapp.agents.themoviedb'
  ]

  def __init__(self):
    Agent.Movies.__init__(self)
    self.proxy = XMLRPC.Proxy(MM_ENDPOINT_URI, 'iso-8859-1')
    self.valid_till = 0

  def search(self, results, media, lang):
    if lang == 'nl':
      if media.primary_agent == 'com.plexapp.agents.themoviedb':
        imdb_id = Core.messaging.call_external_function(
          'com.plexapp.agents.themoviedb',
          'MessageKit:GetImdbId',
          kwargs = dict(
            tmdb_id = media.primary_metadata.id,
            lang = lang
          )
        )
      else:
        imdb_id = media.primary_metadata.id

      # Lookup the MovieMeter movie id using the IMDb id
      try:
        mm_id = self.proxy.film.retrieveByImdb(self.get_session_key(), imdb_id)
        results.Append(MetadataSearchResult(id=mm_id, score=100))
      # If we can't find the MovieMeter movie id using the IMDb id, try to find the MovieMeter movie id by doing a search for movie title
      except:
        search = self.proxy.film.search(self.get_session_key(), media.primary_metadata.title)
        for result in search:
          mm_id = result['filmId']
          score = int(result['similarity'].split('.')[0])

          if result.has_key('year'):
            score = score - abs(media.primary_metadata.year - int(result['year']))

          if result.has_key('directors_text'):
            directors_text = String.StripDiacritics(result['directors_text'])
            for director in media.primary_metadata.directors:
              director = String.StripDiacritics(director)
              if Regex(director, Regex.IGNORECASE).search(directors_text):
                score = score + 10
                break

          results.Append(MetadataSearchResult(id=mm_id, score=score))
          results.Sort('score', descending=True)

  def update(self, metadata, media, lang):
    if lang == 'nl':
      response = self.proxy.film.retrieveDetails(self.get_session_key(), int(metadata.id))
      if response:
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
          metadata.title = movie_page.xpath('//h1[@itemprop="name"]/text()')[0].rsplit('(',1)[0].strip()
        else:
          metadata.title = ''

        if Prefs['summary']:
          try:
            metadata.summary = String.StripTags( movie_page.xpath('//p[@itemprop="description"]/text()')[0].strip() )
          except:
            metadata.summary = ''
        else:
          metadata.summary = ''

        poster = response['thumbnail'].replace('/thumbs', '')
        if Prefs['poster']:
          if poster not in metadata.posters:
            img = HTTP.Request(poster)
            metadata.posters[poster] = Proxy.Preview(img)
        else:
          del metadata.posters[poster]

        if Prefs['content_rating']:
          try:
            kijkwijzer = movie_page.xpath('//img[contains(@src, "kijkwijzer")]/@alt')[0]
            if kijkwijzer.split(' ')[0] in ['6', '9', '12', '16']:
              metadata.content_rating = 'nl/%s' % kijkwijzer.split(' ')[0]
            elif kijkwijzer == 'alle leeftijden':
              metadata.content_rating = 'nl/AL'
            else:
              metadata.content_rating = ''
          except:
            metadata.content_rating = ''
        else:
          metadata.content_rating = ''

  def get_session_key(self):
    if self.valid_till < Datetime.TimestampFromDatetime(Datetime.Now()):
      response = self.proxy.api.startSession(MM_API_KEY)
      self.session_key = response['session_key']
      self.valid_till = int(response['valid_till'])
    return self.session_key
