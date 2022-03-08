import json

import requests
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pymongo import MongoClient
import jwt
import datetime
import base64

import hashlib

from dotenv import load_dotenv
import os

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util
import pprint

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.environ.get("MONGO_DB_KEY"))
db = client.dbsparta

SECRET_KEY = os.environ.get("SECRET_KEY")

# lastFM 전용
API_KEY = os.environ.get("API_KEY")
BASE_URL = "https://ws.audioscrobbler.com/2.0/"

# 스포티파이 api 정보 가져오기
# BASE_URL = "https://api.spotify.com/v1/"
#
# client_id = "5871a40d99e946baa4a50c47fde5587a"
# client_secret = os.environ.get("SPOTIFY_SECRET")
# endpoint = "https://accounts.spotify.com/api/token"
#
# encoded = base64.b64encode("{}:{}".format(client_id, client_secret).encode('utf-8')).decode('ascii')
# headers = {"Authorization": "Basic {}".format(encoded)}
# payload = {"grant_type": "client_credentials"}
# response = requests.post(endpoint, data=payload, headers=headers)
# access_token = json.loads(response.text)['access_token']
# headers = {"Authorization": "Bearer {}".format(access_token)}


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        return render_template('index.html', nickname=user_info["nick"])
        # return redirect(url_for("main", nickname=user_info["nick"]))
    except jwt.ExpiredSignatureError:
        return render_template('index.html', nickname="anon")
    except jwt.exceptions.DecodeError:
        return render_template('index.html', nickname="anon")

# # 페이지 렌더링 (lastFM)
@app.route('/main')
def main():

    # 처음 보여줄 컨텐츠를 담은 api 주소 ( top artist )
    LAST_URL = "?method=chart.gettopartists&api_key=" + API_KEY + "&format=json"

    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})

        r = requests.get(BASE_URL + LAST_URL)
        response = r.json()

        top_artist = response['artists']['artist']

        return render_template('main.html', nickname=user_info["nick"], artist=top_artist)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# # # 메인 렌더링 (spotify)
# @app.route('/main')
# def main():
#
#     params = {
#         "seed_artists":
#     }
#
#     r = requests.get(BASE_URL + "recommendations", params=)


# 검색 lastFM
@app.route('/main/<keyword>')
def searchMain(keyword):
    r = requests.get(BASE_URL + "?method=artist.gettopalbums&artist=" + keyword + "&api_key=" + API_KEY + "&format=json")
    response = r.json()
    albums = response["topalbums"]["album"]
    return render_template('main.html', keyword=keyword, albums=albums)

# 검색 spotify
# @app.route('/main/<keyword>')
# def spoti_search(keyword):
#     params = {
#         "q": keyword,
#         "type": "artist",
#     }
#     r = requests.get("https://api.spotify.com/v1/search", params=params, headers=headers)
#     response = r.json()
#     print(response)
#     # return jsonify(response)
    # artistId = response["artists"]["items"][0]["id"]
    # # artistId = "4aawyAB9vmqN3uQ7FjRGTy"
    # print(artistId)
    #
    # pprint.pprint(response)
    # getAlbum = requests.get("https://api.spotify.com/v1/albums/" + artistId, headers=headers)
    # res = getAlbum.json()
    # return jsonify(res)
#
# #test
# @app.route('/main/test/<keyword>')
# def test(keyword):
#     getAlbum = requests.get("https://api.spotify.com/v1/albums/" + keyword, headers=headers)
#     res = getAlbum.json()
#     return jsonify(res)


# 앨범의 상세정보
@app.route('/detail/<artist>/<album>')
def detail(artist, album):

    LAST_URL = "?method=album.getinfo&artist=" + artist + "&album=" + album + "&api_key=" + API_KEY + "&format=json"

    r = requests.get(BASE_URL + LAST_URL)
    response = r.json()
    res_album = response["album"]
    print(res_album)

    return render_template('detail.html', album=res_album, a_name=album)

@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/mypage')
def mypage():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        return render_template('mypage.html', nickname=user_info["nick"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 회원가입
@app.route('/api/register', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive})

    return jsonify({'result': 'success'})

# 로그인
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    if result is not None:
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=10000)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
