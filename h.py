import os

from flask import Flask, request, redirect, session, url_for

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

app = Flask(__name__);
app.config['SECRET_KEY'] = os.urandom(64)

client_id = '558b7977acac4731ae97fe08f7fc2b01'
client_secret = '1ee0e6564db24b71bb884373b0ac5bb2'
redirect_uri = 'http://127.0.0.1:9090/callback'
scope = 'playlist-read-private streaming user-top-read'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
sp = Spotify(auth_manager=sp_oauth)

def check_spotify_auth(sp_oauth, cache_handler):
    """
    Checks if the Spotify token is valid.
    If not, returns a redirect response to Spotify auth URL.
    Otherwise, returns None.
    """
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return None

@app.route('/')
def home():
    auth_redirect = check_spotify_auth(sp_oauth, cache_handler)
    if auth_redirect:
        return auth_redirect
    
    return redirect(url_for('get_playlists'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))


# @app.route('/get_recommendations')
# def get_recommendations():

@app.route('/get_playlists')
def get_playlists():
    check_spotify_auth(sp_oauth, cache_handler)
    top_artists = sp.current_user_top_artists(limit=20, offset=0, time_range='short_term')

    playlists = sp.current_user_playlists()

    playlists_info = []
    for pl in playlists['items']:
        playlist_name = pl['name']
        playlist_image = pl['images'][0]['url']
        # Fetch tracks for this playlist
        tracks = sp.playlist_items(pl['id'], limit=1)  # just the first track
        
        if tracks['items']:
            first_track = tracks['items'][0]['track']['name']
        else:
            first_track = "No tracks"
        
        playlists_info.append((playlist_name, playlist_image,first_track))

    playlists = ["Playlist 1", "Playlist 2", "Playlist 3"]
    
    top_artists_html = "<ul>"
    for artist in top_artists["items"]:
        top_artists_html += f"<li>{artist['name']}</li>"
    top_artists_html += "</ul>"

    playlist_html = "".join(
    f'<li><h3>{name}</h3><img src="{image}" width="200"><h3>{first_track}</h3></li>'
    for name, image, first_track in playlists_info if image
)
    
    return f"""
    <html>
        <head>
            <title>Your Playlists</title>
            <style>
                body {{
                    font-family: yagiza;
                    background-color: #FFE1E0;
                    color: white;
                    text-align: center;
                }}
                h1 {{
                    color: #7F55B1;
                }}
                ul {{
                    list-style: none;
                    padding: auto;
                    display: flex;
                    flex-wrap: wrap;
                    margin-right: auto;
                    margin-left: auto;
                }}
                li {{
                    padding: 10px;
                    margin: 5px 0;
                    background-color: #F49BAB;
                    border-radius: 5px;
                    width: 200px;
                    margin-left: auto;
                    margin-right: auto;
                    font-family: arial;
                    color: #9B7EBD;
                }}
            </style>
        </head>
        <body>
            <h1>Your Top Artists</h1>
            <ul>
                {top_artists_html}
            </ul>
            <h1>Your Playlists</h1>
            <ul>
                {playlist_html}
            </ul>
        </body>
    </html>
    """
    return top_artists_html
    return playlists_html

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(port=9090, debug=True) 
