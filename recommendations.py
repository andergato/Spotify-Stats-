import os

from flask import Flask, request, redirect, session, url_for, flash

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.exceptions import SpotifyException

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
# Load Tailwind CSS for modern, responsive styling
app.config['TAILWIND'] = '<script src="https://cdn.tailwindcss.com"></script>'

# Replace with your actual client_id and client_secret
# To make this code runnable, you must enter valid credentials
client_id = 'b7d2af954e614088810d626fd02f9a55' 
client_secret = '5347729d50a94cb3b21f5013c268fa2f'
redirect_uri = 'http://127.0.0.1:9090/callback'
# The scope is sufficient for this example, but more complex apps might need more.
scope = 'playlist-read-private,streaming'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)

def get_spotify_instance():
    """
    Ensures a valid Spotify instance is available.
    Raises a redirect response if the token is expired or missing.
    """
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        raise redirect(auth_url)
    
    # Check if the token is expired and refresh it
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])

    # Instantiate the Spotify object with the valid token
    return Spotify(auth=token_info['access_token'])

@app.route('/')
def home():
    # Redirect to either get_playlists or get_recommendations
    # after the initial authentication
    return redirect(url_for('get_playlists'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))

@app.route('/get_playlists')
def get_playlists():
    # Get a Spotify instance with a valid token
    try:
        sp = get_spotify_instance()
    except Exception as e:
        # Catch the raised redirect object and return it
        if isinstance(e, type(redirect(url_for('home')))):
            return e
        return f"Authentication error: {e}"

    playlists_info = []
    try:
        playlists = sp.current_user_playlists()
        for pl in playlists['items']:
            playlist_name = pl['name']
            playlist_image = pl['images'][0]['url'] if pl['images'] else ''
            tracks = sp.playlist_items(pl['id'], limit=1)
            first_track = tracks['items'][0]['track']['name'] if tracks['items'] else "No tracks"
            playlists_info.append((playlist_name, playlist_image, first_track))
    except SpotifyException as e:
        return f"Error fetching playlists: {e.msg}"

    playlist_html = "".join(
        f'<li class="bg-gray-800 p-4 rounded-lg shadow-lg w-48 text-left">'
        f'<h3 class="mt-2 text-lg font-semibold text-white truncate">{name}</h3>'
        f'<img src="{image}" alt="{name} cover" class="rounded-md w-full h-auto mt-2">'
        f'<p class="text-sm text-gray-400 mt-2">First Track: {first_track}</p></li>'
        for name, image, first_track in playlists_info
    )

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your Playlists</title>
            {app.config['TAILWIND']}
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
                body {{ font-family: 'Inter', sans-serif; }}
            </style>
        </head>
        <body class="bg-gray-900 text-white min-h-screen flex flex-col items-center p-8">
            <h1 class="text-4xl font-bold text-green-500 mb-8">Your Playlists</h1>
            <ul class="flex flex-wrap justify-center gap-6 max-w-7xl w-full">
                {playlist_html}
            </ul>
            <a href="{url_for('get_recommendations')}" class="mt-8 text-green-500 hover:text-green-400 font-semibold transition-colors duration-200">Get Recommendations</a>
            <a href="{url_for('logout')}" class="mt-4 text-red-500 hover:text-red-400 font-semibold transition-colors duration-200">Logout</a>
        </body>
    </html>
    """

@app.route('/get_recommendations')
def get_recommendations():
    try:
        sp = get_spotify_instance()
    except Exception as e:
        if isinstance(e, type(redirect(url_for('home')))):
            return e
        return f"Authentication error: {e}"

    recommendations = {}
    try:
        available_genres = sp.recommendation_genre_seeds()
        
        seeds_to_use = []
        if 'pop' in available_genres:
            seeds_to_use.append('pop')
        if 'rock' in available_genres:
            seeds_to_use.append('rock')
        
        if not seeds_to_use and len(available_genres) >= 2:
            seeds_to_use = available_genres[:2]
        elif not seeds_to_use and len(available_genres) == 1:
            seeds_to_use = available_genres[:1]
        
        if seeds_to_use:
            recommendations = sp.recommendations(seed_genres=seeds_to_use, limit=10)
        else:
            return "No valid genre seeds found to generate recommendations."

    except SpotifyException as e:
        return f"Error fetching recommendations: {e.msg}"

    tracks_info = []
    for track in recommendations.get('tracks', []):
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        album_image = track['album']['images'][0]['url']
        tracks_info.append({
            'name': track_name,
            'artist': artist_name,
            'image': album_image
        })

    tracks_html = "".join(
        f"""
        <div class="bg-gray-800 p-4 rounded-lg shadow-lg w-48 text-left">
            <img src="{track['image']}" alt="{track['name']} album art" class="rounded-md w-full h-auto">
            <h3 class="mt-2 text-lg font-semibold text-white truncate">{track['name']}</h3>
            <p class="text-sm text-gray-400">{track['artist']}</p>
        </div>
        """ for track in tracks_info
    )

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Spotify Recommendations</title>
            {app.config['TAILWIND']}
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
                body {{ font-family: 'Inter', sans-serif; }}
            </style>
        </head>
        <body class="bg-gray-900 text-white min-h-screen flex flex-col items-center p-8">
            <h1 class="text-4xl font-bold text-green-500 mb-8">Recommended Tracks</h1>
            <div class="flex flex-wrap justify-center gap-6 max-w-7xl w-full">
                {tracks_html}
            </div>
            <a href="{url_for('get_playlists')}" class="mt-8 text-green-500 hover:text-green-400 font-semibold transition-colors duration-200">View Playlists</a>
            <a href="{url_for('logout')}" class="mt-4 text-red-500 hover:text-red-400 font-semibold transition-colors duration-200">Logout</a>
        </body>
    </html>
    """

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(port=9090, debug=True)
