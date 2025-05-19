# File: maze_of_me/test_spotify.py
from oauth.spotify import SpotifyCollector

def main():
    sc = SpotifyCollector()
    sc.authenticate()      # opens URL → paste redirect URL here
    sc.fetch_and_save()    # writes spotify data to user_profile.json

if __name__ == "__main__":
    main()
