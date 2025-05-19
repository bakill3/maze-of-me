from oauth.spotify import SpotifyCollector
sc = SpotifyCollector()
sc.authenticate()
sc.fetch_and_save()
