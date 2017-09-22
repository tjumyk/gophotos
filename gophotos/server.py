import base64
import glob
import json
import os
import uuid
from functools import wraps
from multiprocessing.pool import ThreadPool

import httplib2
import requests
import xmltodict
from flask import Flask, redirect, request, session, url_for, jsonify, render_template
from oauth2client import client as gc

from gophotos.upyun import UPYun

GOOGLE_CLIENT_SECRET_FILE = 'secrets/google_client.json'
GOOGLE_PHOTOS_SCOPE = 'https://picasaweb.google.com/data/'

UPYUN_SECRET_FILE = 'secrets/upyun.json'

API_ALBUMS = "https://picasaweb.google.com/data/feed/api/user/default"
API_ALBUM_PHOTOS = "https://picasaweb.google.com/data/feed/api/user/default/albumid/%s?&imgmax=1600"

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

with open('config.json') as f:
    config = json.load(f)
with open(UPYUN_SECRET_FILE) as f:
    upyun_client = UPYun(**json.load(f))

NUM_API_WORKING_THREADS = config['api_working_threads']
EXTERNAL_URL = config['external_url']

DATA_CACHE_FOLDER = config['data_cache_folder']
IMAGE_CACHE_FOLDER = config['image_cache_folder']
DATA_SHARE_FOLDER = config['data_share_folder']
IMAGE_SHARE_FOLDER = config['image_share_folder']
if not os.path.isdir(DATA_CACHE_FOLDER):
    os.makedirs(DATA_CACHE_FOLDER)
if not os.path.isdir(IMAGE_CACHE_FOLDER):
    os.makedirs(IMAGE_CACHE_FOLDER)
if not os.path.isdir(DATA_SHARE_FOLDER):
    os.makedirs(DATA_SHARE_FOLDER)
if not os.path.isdir(IMAGE_SHARE_FOLDER):
    os.makedirs(IMAGE_SHARE_FOLDER)


def _get_credentials():
    if 'credentials' not in session:
        return None
    return gc.OAuth2Credentials.from_json(session['credentials'])


def _check_authenticated():
    credentials = _get_credentials()
    return credentials is not None and not credentials.access_token_expired


@app.route('/')
def index():
    if not _check_authenticated():
        return redirect(EXTERNAL_URL + url_for('oauth2_callback'))
    return render_template('base.html')


@app.route('/shared/<sid>')
def shared_index(sid):
    return render_template('base.html')


@app.route('/oauth2callback')
def oauth2_callback():
    flow = gc.flow_from_clientsecrets(
        GOOGLE_CLIENT_SECRET_FILE,
        scope=GOOGLE_PHOTOS_SCOPE,
        redirect_uri=EXTERNAL_URL + url_for('oauth2_callback'))
    if 'code' not in request.args:
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)

    error = request.args.get('error')
    if error is not None:
        return 'OAuth2 Error: %s' % error, 401
    auth_code = request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    session['credentials'] = credentials.to_json()
    return redirect(EXTERNAL_URL + url_for('index'))


def require_authenticated(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _check_authenticated():
            return jsonify({'error': 'You have not been authenticated'}), 403
        return f(*args, **kwargs)

    return decorated


def request_api(api_path):
    credentials = _get_credentials()
    if credentials is None:
        raise RuntimeError("Credentials must be initialized before API request")

    http_auth = credentials.authorize(httplib2.Http())
    headers = {'GData-Version': '3'}

    rid = base64.b64encode(api_path.encode(), b'-_').decode()
    data_path = os.path.join(DATA_CACHE_FOLDER, "%s.json" % rid)
    cached_data = None
    if os.path.isfile(data_path):  # we have cached data
        with open(data_path) as f:
            cached_data = json.load(f)
        headers['If-None-Match'] = cached_data['etag']

    resp, content = http_auth.request(api_path, headers=headers)
    status = resp.status
    print('Request \"%s\" --> [%d]' % (api_path, status))
    if status == 304:
        data = cached_data['data']
    elif status == 200:
        data = xmltodict.parse(content)
        etag = None
        for k, v in data.items():
            etag = v.get('@gd:etag')  # try to extract the top-level etag
            break
        if etag is not None:
            with open(data_path, 'w') as f:
                f.write(json.dumps({
                    'etag': etag,
                    'data': data
                }))
    else:
        raise RuntimeError(content)
    return data


@app.route('/api/albums')
@require_authenticated
def get_albums():
    return jsonify(_get_albums())


def _get_albums():
    data = request_api(API_ALBUMS)
    albums = []
    for album_data in data['feed']['entry']:
        a_etag = album_data['@gd:etag']
        aid = album_data['gphoto:id']
        title = album_data['title']
        published = album_data['published']
        updated = album_data['updated']
        num_photos = int(album_data['gphoto:numphotos'])

        media_data = album_data['media:group']
        content_data = media_data['media:content']
        content = {
            'type': content_data['@type'],
            'url': content_data['@url']
        }
        thumbnail_data = media_data['media:thumbnail']
        thumbnail = {
            'height': thumbnail_data['@height'],
            'width': thumbnail_data['@width'],
            'url': thumbnail_data['@url']
        }

        # optional bytesUsed
        bytes_used_str = album_data.get('gphoto:bytesUsed')
        bytes_used = None
        if bytes_used_str is not None:
            bytes_used = int(bytes_used_str)

        # optional albumType
        atype = album_data.get('gphoto:albumType')
        # album type can be 'InstantUpload', 'ProfilePhotos', 'Blogger' or None (normal album)
        if atype is not None:
            continue  # skip all the special albums

        albums.append({
            'id': aid,
            'etag': a_etag,
            'title': title,
            'publish_time': published,
            'update_time': updated,
            'num_photos': num_photos,
            'content': content,
            'thumbnail': thumbnail,
            'bytes_used': bytes_used
        })
    return albums


@app.route('/api/albums/<aid>/photos')
@require_authenticated
def get_photos(aid):
    return jsonify(_get_photos(aid))


def _get_photos(aid):
    data = request_api(API_ALBUM_PHOTOS % aid)
    photos = []
    for photo_data in data['feed']['entry']:
        pid = photo_data['gphoto:id']
        p_etag = photo_data['@gd:etag']
        title = photo_data['title']
        published = photo_data['published']
        updated = photo_data['updated']
        # aid = photo_data['gphoto:albumid']
        width = int(photo_data['gphoto:width'])
        height = int(photo_data['gphoto:height'])
        size = int(photo_data['gphoto:size'])
        version = int(photo_data['gphoto:imageVersion'])

        content_data = photo_data['content']
        content = {
            'url': content_data['@src'],
            'type': content_data['@type']
        }

        exif_tags_data = photo_data.get('exif:tags')
        exif_tags = None
        if exif_tags_data is not None:
            exif_tags = {}
            for k, v in exif_tags_data.items():
                name = k[5:]  # remove prefix "exif:"
                if name in ['exposure', 'focallength', 'fstop']:
                    exif_tags[name] = float(v)
                elif name in ['iso', 'time']:
                    exif_tags[name] = int(v)
                elif name in ['flash']:
                    exif_tags[name] = v.lower() == 'true'
                else:
                    exif_tags[name] = v

        geo_data = photo_data.get('georss:where', {}).get('gml:Point', {}).get('gml:pos')
        geo = None
        if geo_data is not None:
            pos_strs = geo_data.split()
            geo = {
                'latitude': float(pos_strs[0]),
                'longitude': float(pos_strs[1])
            }

        min_thumbnail_width = width
        min_thumbnail = None
        for thumbnail_data in photo_data['media:group']['media:thumbnail']:
            t_width = int(thumbnail_data['@width'])
            if t_width < min_thumbnail_width:
                min_thumbnail_width = t_width
                t_height = int(thumbnail_data['@height'])
                url = thumbnail_data['@url']
                min_thumbnail = {
                    'width': t_width,
                    'height': t_height,
                    'url': url
                }

        photos.append({
            'id': pid,
            'etag': p_etag,
            'version': version,
            'title': title,
            'publish_time': published,
            'update_time': updated,
            'width': width,
            'height': height,
            'size': size,
            'exif_tags': exif_tags,
            'geo': geo,
            'content': content,
            'thumbnail': min_thumbnail
        })
    return photos


def _get_album(aid):
    albums = _get_albums()  # very inefficient, i'm lazy now
    for a in albums:
        if a['id'] == aid:
            return a
    return None


@app.route('/api/share-album/<aid>')
@require_authenticated
def share_album(aid):
    album = _get_album(aid)
    if album is None:
        return jsonify(error='Album [id=%s] was not found' % aid), 404

    photos = _get_photos(album['id'])
    pool = ThreadPool(NUM_API_WORKING_THREADS)
    pool.starmap(_download_and_distribute_photo, ((album, photo) for photo in photos))

    # TODO also update album thumbnail url

    data = {
        'album': album,
        'photos': photos
    }

    share_id = str(uuid.uuid4())
    data_file = os.path.join(DATA_SHARE_FOLDER, '%s.json' % share_id)
    with open(data_file, 'w') as f:
        f.write(json.dumps(data))
    url = url_for('shared_index', sid=share_id)
    return jsonify(sid=share_id, url=url, external_url=EXTERNAL_URL + url)


def _download_and_distribute_photo(album, photo):
    content_data = photo['content']
    content_type = content_data['type']
    url = content_data['url']
    ind = url.rindex('.')
    ext = url[ind + 1:].lower()
    if len(ext) > 4:
        ext = ''
    file_path = '%s/%s.%s' % (album['id'], photo['id'], ext)
    prompt_id = 'Album: %s (id=%s), Photo: %s (id=%s)' % (album['title'], album['id'], photo['title'], photo['id'])
    print('[Retrieving Photo] %s' % prompt_id)
    content = requests.get(url).content
    print('[Distributing Photo to UPYun] %s' % prompt_id)
    upyun_client.upload_file_content(file_path, content, content_type)
    photo['content']['_upyun_path'] = file_path
    new_url = upyun_client.get_url(file_path)
    photo['content']['url'] = new_url
    ratio = photo['width'] / photo['height']
    photo['thumbnail'] = {
        'url': new_url + '!tiny',
        'width': 80,
        'height': int(80 / ratio)
    }


@app.route('/api/shared-albums')
@require_authenticated
def get_all_shared_albums():
    shares = []
    for data_file in glob.iglob(os.path.join(DATA_SHARE_FOLDER, '*.json')):
        sid = os.path.splitext(os.path.basename(data_file))[0]
        url = url_for('shared_index', sid=sid)
        external_url = EXTERNAL_URL + url
        with open(data_file) as f:
            data = json.load(f)
        shares.append({
            'aid': data['album']['id'],
            'sid': sid,
            'url': url,
            'external_url': external_url
        })
    return jsonify(shares)


@app.route('/api/shared-albums/<sid>', methods=['GET'])
def get_shared_album(sid):
    data_file = os.path.join(DATA_SHARE_FOLDER, '%s.json' % sid)
    if not os.path.isfile(data_file):
        return jsonify(error='Shared album [key=%s] was not found' % sid), 404
    with open(data_file) as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/shared-albums/<sid>', methods=['DELETE'])
def delete_shared_album(sid):
    data_file = os.path.join(DATA_SHARE_FOLDER, '%s.json' % sid)
    if not os.path.isfile(data_file):
        return jsonify(error='Shared album [key=%s] was not found' % sid), 404

    with open(data_file) as f:
        data = json.load(f)
    album = data['album']
    photos = data['photos']
    pool = ThreadPool(NUM_API_WORKING_THREADS)
    pool.starmap(_delete_photo_file, ((album, photo) for photo in photos))
    os.remove(data_file)
    return "", 204


def _delete_photo_file(album, photo):
    prompt_id = 'Album: %s (id=%s), Photo: %s (id=%s)' % (album['title'], album['id'], photo['title'], photo['id'])
    print('[Removing Photo from UPYun] %s' % prompt_id)
    upyun_client.remove_file(photo['content']['_upyun_path'])


def run_server():
    app.run(**config['server'])
