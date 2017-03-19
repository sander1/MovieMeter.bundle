API_KEY = 'fnsxd7shhmc8gefjhz2zv0nrjwjbezhj'
API_MOVIE_URL = 'https://www.moviemeter.nl/api/film/%%s?api_key=%s' % (API_KEY)
API_SEARCH_URL = 'https://www.moviemeter.nl/api/film/?q=%%s&api_key=%s' % (API_KEY)
MOVIE_URL = 'https://www.moviemeter.nl/film/%s'

def Start():

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Plex Media Server/%s' % Platform.ServerVersion
  HTTP.Headers['Cookie'] = 'cok=1'

class MovieMeterAgent(Agent.Movies):

  name = 'MovieMeter'
  languages = [Locale.Language.Dutch]
  primary_provider = False
  contributes_to = [
    'com.plexapp.agents.imdb',
    'com.plexapp.agents.themoviedb'
  ]

  def search(self, results, media, lang):

    # In case 'Plex Movie' is the primary agent
    if media.primary_agent == 'com.plexapp.agents.imdb':
      imdb_id = media.primary_metadata.id

    # In case 'The Movie Database' is the primary agent
    elif media.primary_agent == 'com.plexapp.agents.themoviedb':
      imdb_id = Core.messaging.call_external_function(
        'com.plexapp.agents.themoviedb',
        'MessageKit:GetImdbId',
        kwargs = dict(
          tmdb_id = media.primary_metadata.id,
          lang = lang
        )
      )

    else:
      return None

    # Lookup the MovieMeter movie id using the IMDb id
    try:
      json_obj = JSON.ObjectFromURL(API_MOVIE_URL % (imdb_id))
      mm_id = json_obj['id']
      results.Append(MetadataSearchResult(id=str(mm_id), score=100))

    # If we can't find the MovieMeter movie id using the IMDb id, try to find the MovieMeter movie id by doing a search for movie title
    except:
      title = String.Quote(media.primary_metadata.title)

      try:
        json_obj = JSON.ObjectFromURL(API_SEARCH_URL % (title))
      except:
        return None

      for result in json_obj:

        score = 100
        mm_id = result['id']

        if 'year' in result:
          score = score - abs(media.primary_metadata.year - int(result['year']))

        results.Append(MetadataSearchResult(id=str(mm_id), score=score))
        results.Sort('score', descending=True)

  def update(self, metadata, media, lang):

    json_obj = JSON.ObjectFromURL(API_MOVIE_URL % (metadata.id))

    if 'message' not in json_obj:

      if Prefs['title']:
        metadata.title = json_obj['display_title']
      else:
        metadata.title = None

      if Prefs['summary']:
        metadata.summary = json_obj['plot']
      else:
        metadata.summary = None

      metadata.year = json_obj['year']

      if Prefs['rating']:
        metadata.rating = float(json_obj['average']) * 2 # Max 5 for MovieMeter, needs max 10 for Plex
      else:
        metadata.rating = None

      if Prefs['rating'] and Prefs['append_rating'] and Prefs['summary']:
        metadata.summary = '%s  ★  %s' % (round(metadata.rating, 1), metadata.summary)

      metadata.genres.clear()
      if Prefs['genres']:
        for genre in json_obj['genres']:
          metadata.genres.add(genre)

      poster = json_obj['posters']['large']
      if Prefs['poster']:
        if poster not in metadata.posters:
          img = HTTP.Request(poster)
          metadata.posters[poster] = Proxy.Preview(img)
      else:
        del metadata.posters[poster]

      if Prefs['content_rating']:

        movie_page = HTML.ElementFromURL(MOVIE_URL % metadata.id)

        try:
          kijkwijzer = movie_page.xpath('//div[contains(@class, "rating_")]/@title')[0]

          if kijkwijzer.split(' ')[0] in ['6', '9', '12', '16']:
            metadata.content_rating = 'nl/%s' % kijkwijzer.split(' ')[0]
          elif kijkwijzer == 'alle leeftijden':
            metadata.content_rating = 'nl/AL'
          else:
            metadata.content_rating = None

        except:
          metadata.content_rating = None

      else:
        metadata.content_rating = None
