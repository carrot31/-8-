import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
import jwt
import datetime
from werkzeug.utils import secure_filename

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


# 첫 대문 , 토큰이 발급돼있는 상태라면 로그인 버튼 대신 username 글자가 표시됨
@app.route('/')
def title():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload['id']})
        if user_info is not None:
            return render_template('title.html', text=user_info["username"])
        else:
            return render_template('title.html', text="Login")

    except jwt.ExpiredSignatureError:
        return render_template('title.html', text="Login")
    except jwt.exceptions.DecodeError:
        return render_template('title.html', text="Login")

# /login 렌더링
@app.route('/login')
def login():
    return render_template('login.html')

# 회원가입 시 db에 동일한 아이디가 있는지 검사
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# 로그인 로직 / 아이디 비밀번호 일치하면 토큰 발급
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입 DB 저장
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png", # 프로필 사진 기본 이미지
        "profile_info": ""                                          # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

# 토큰 검사 후 마이페이지로 이동
@app.route('/mypage/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    print(username)
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": payload['id']})

        print(user_info)

        return render_template('mypage.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))


@app.route('/update_profile', methods=['POST'])
def save_img():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload["id"]
        name_receive = request.form["name_give"]
        about_receive = request.form["about_give"]
        new_doc = {
            "profile_name": name_receive,
            "profile_info": about_receive
        }
        if 'file_give' in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/public/"+file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({'username': payload['id']}, {'$set':new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login.html"))


# 페이지 렌더링 (lastFM)
@app.route('/main')
def main():
    # 처음 보여줄 컨텐츠를 담은 api 주소 ( top artist )
    LAST_URL = "?method=chart.gettopartists&api_key=" + API_KEY + "&format=json"
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload['id']})

        r = requests.get(BASE_URL + LAST_URL)
        response = r.json()
        top_artist = response['artists']['artist']


        return render_template('main.html', user_info=user_info, artist=top_artist)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# 검색 lastFM
@app.route('/main/<keyword>')
def searchMain(keyword):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload['id']})

        r = requests.get(
            BASE_URL + "?method=artist.gettopalbums&artist=" + keyword + "&api_key=" + API_KEY + "&format=json")
        response = r.json()

        albums = response["topalbums"]["album"]
        return render_template('main.html', keyword=keyword, albums=albums, user_info=user_info)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))



# 앨범의 상세정보
@app.route('/detail/<artist>/<album>')
def detail(artist, album):

    LAST_URL = "?method=album.getinfo&artist=" + artist + "&album=" + album + "&api_key=" + API_KEY + "&format=json"

    r = requests.get(BASE_URL + LAST_URL)
    response = r.json()
    res_album = response["album"]
    print(res_album)

    return render_template('detail.html', album=res_album, a_name=album)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
