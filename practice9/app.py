import json
import pymysql
from requests import HTTPError
from secrets import token_hex
from flask import jsonify

from practice10.main import auth
from flask import Flask, request, Response

from util.error import ErrorHandler

app = Flask(__name__)

INVALID_TOKEN = 401
SERVER_ERROR = 500
BAD_REQUEST = 400
NOT_FOUND = 404
VERIFY_EMAIL = 600


def conn():
    return pymysql.connect(host='us-cdbr-iron-east-01.cleardb.net',
                           user='b40fd74efb18c2',
                           password='e2547e43',
                           db='heroku_4a4d86265c8552e',
                           use_unicode=True,
                           charset='utf8',
                           cursorclass=pymysql.cursors.DictCursor)


@app.route('/getComicOffset')
def getComicOffset():
    token = request.headers.get('token')
    offset = request.args.get('offset')
    count = request.args.get('count')

    connection = conn()
    cursor = connection.cursor()

    try:

        if not token:
            return error_return(ErrorHandler('Invalid Request', status_code=BAD_REQUEST))
        if validToken(cursor, token):
            cursor.execute("SELECT * FROM comic LIMIT %s,%s" % (offset, count))
            comics = cursor.fetchall()
            for comic in comics:
                cursor.execute("SELECT * FROM genre WHERE idcomic = %s" % comic['id'])
                comic['genre'] = cursor.fetchall()
            cursor.close()
            return Response(json.dumps(comics), mimetype='application/json')
        else:
            cursor.close()
            return error_return(ErrorHandler('Invalid Token', status_code=INVALID_TOKEN))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


@app.route('/getComic')
def getComic():
    token = request.headers.get('token')
    after = request.args.get('after')
    limit = request.args.get('limit')

    connection = conn()
    cursor = connection.cursor()

    try:
        if not token:
            return error_return(ErrorHandler('Invalid Request', status_code=BAD_REQUEST))

        if validToken(cursor, token):
            if after:
                cursor.execute("SELECT * FROM comic WHERE comic.id > %s LIMIT %s" % (str(after), str(limit)))
            else:
                cursor.execute("SELECT * FROM comic LIMIT %s" % (str(limit)))
            comics = cursor.fetchall()
            for comic in comics:
                cursor.execute("SELECT * FROM genre WHERE idcomic = %s" % comic['id'])
                comic['genre'] = cursor.fetchall()
            return Response(json.dumps(comics), mimetype='application/json')
        else:
            return error_return(ErrorHandler('Invalid Token', status_code=INVALID_TOKEN))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


@app.route('/getComicImage/<int:id>')
def getComicImage(id):
    token = request.headers.get('token')
    after = request.args.get('after')
    limit = request.args.get('limit')

    connection = conn()
    cursor = connection.cursor()
    try:
        if not token:
            return error_return(ErrorHandler('Invalid Request', status_code=BAD_REQUEST))

        if validToken(cursor, token):
            if after:
                cursor.execute("SELECT * FROM linkimage WHERE idcomic = %s AND linkimage.id > %s LIMIT %s" % (
                    str(id), after, limit))
            else:
                cursor.execute("SELECT * FROM linkimage WHERE idcomic = %s LIMIT %s" % (
                    str(id), limit))

            data = cursor.fetchall()
            return Response(json.dumps(data), mimetype='application/json')
        else:
            return error_return(ErrorHandler('Invalid Token', status_code=INVALID_TOKEN))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


@app.route('/register', methods=['PUT'])
def register():
    data = request.json
    connection = conn()
    cursor = connection.cursor()
    try:
        user = auth.create_user_with_email_and_password(data['email'], data['password'])
        auth.send_email_verification(user['idToken'])
        sql = "INSERT INTO `user` (name, email, token_firebase, token) VALUES (%s, %s, %s, %s)"
        val = (data['name'], data['email'], user['idToken'], '')
        cursor.execute(sql, val)
        connection.commit()
        return Response(json.dumps('Please verify email !!!'),mimetype='application/json')
    except HTTPError as e:
        response = e.args[0].response
        error = response.json()['error']['message']
        return error_return(ErrorHandler(error, status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.json

    connection = conn()
    cursor = connection.cursor()

    try:
        user = auth.sign_in_with_email_and_password(data['email'], data['password'])
        token_firebase = user['idToken']
        print(token_firebase)
        info = auth.get_account_info(token_firebase)
        user = info['users'][0]
        if user['emailVerified']:
            cursor.execute(
                "SELECT user.id FROM user WHERE email = %s",
                (data['email'],)
            )
            id = cursor.fetchone()['id']
            if id:
                utoken = token_hex(32)
                sql = "UPDATE user SET token = %s WHERE id = %s"
                val = (utoken, str(id))
                cursor.execute(sql, val)
                connection.commit()
                return Response(json.dumps(utoken), mimetype='application/json')
            else:
                return error_return(ErrorHandler('User Not Found', status_code=NOT_FOUND))
        else:
            return error_return(ErrorHandler('Email not verify !!!', status_code=VERIFY_EMAIL))
    except HTTPError as e:
        response = e.args[0].response
        error = response.json()['error']['message']
        return error_return(ErrorHandler(error, status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


@app.route('/resetPassword', methods=['POST'])
def resetPassword():
    try:
        data = request.json
        auth.send_password_reset_email(data['email'])
        return Response(json.dumps('Please check email !!!'),mimetype='application/json')
    except HTTPError as e:
        response = e.args[0].response
        error = response.json()['error']['message']
        return error_return(ErrorHandler(error, status_code=SERVER_ERROR))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))


@app.route('/sendEmailVerify', methods=['POST'])
def sendEmailVerify():
    try:
        data = request.json
        user = auth.sign_in_with_email_and_password(data['email'], data['password'])
        auth.send_email_verification(user['idToken'])
        return Response()
    except HTTPError as e:
        response = e.args[0].response
        error = response.json()['error']['message']
        return error_return(ErrorHandler(error, status_code=SERVER_ERROR))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))


@app.route('/userInfo', methods=['POST'])
def userInfo():
    token = request.headers.get('token')
    connection = conn()
    cursor = connection.cursor()

    try:

        if not token:
            return error_return(ErrorHandler('Invalid Request', status_code=BAD_REQUEST))

        if validToken(cursor, token):
            cursor.execute(
                "SELECT tbUser.id,tbUser.name,tbUser.email,(SELECT link FROM picture WHERE id_user = tbUser.id) as avarta FROM user AS tbUser WHERE token = %s",
                token
            )
            data = cursor.fetchone()
            return Response(json.dumps(data), mimetype='application/json')
        else:
            return error_return(ErrorHandler('Invalid Token', status_code=INVALID_TOKEN))
    except Exception as e:
        return error_return(ErrorHandler(str(e), status_code=SERVER_ERROR))
    finally:
        connection.close()
        cursor.close()


def validToken(cursor, token):
    cursor.execute(
        "SELECT COUNT(*) FROM user WHERE token = %s",
        token
    )
    count = cursor.fetchone()
    return count['COUNT(*)'] == 1


@app.errorhandler(ErrorHandler)
def error_return(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    app.run()
