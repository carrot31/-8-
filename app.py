import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
import jwt
import datetime

import hashlib

from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.environ.get("MONGO_DB_KEY"))
db = client.dbsparta

SECRET_KEY = os.environ.get("SECRET_KEY")

# lastFM 전용
API_KEY = os.environ.get("API_KEY")
BASE_URL = "https://ws.audioscrobbler.com/2.0/"

@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        return render_template('index.html', nickname=user_info["nick"])
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

# 검색 lastFM
@app.route('/main/<keyword>')
def searchMain(keyword):
    r = requests.get(BASE_URL + "?method=artist.gettopalbums&artist=" + keyword + "&api_key=" + API_KEY + "&format=json")
    response = r.json()

    print(response)

    if 'error' in response.keys():
        return render_template('main.html', msg="404")
    else:
        albums = response["topalbums"]["album"]
        return render_template('main.html', keyword=keyword, albums=albums)

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

@app.route('/mypage/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": username}, {"_id": False})

        return render_template('mypage.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))

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
