#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Flaskr + Babel + PhraseApp
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    Modified Flask demo app showing localization with Flask-Babel and PhraseApp
"""

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask import jsonify
from flask_mysqldb import MySQL
import docker as docker_sdk
from functools import wraps

# Create our little application :)
app = Flask(__name__)
# Read config
app.config.from_pyfile('config.py')
mysql = MySQL(app)
docker = docker_sdk.from_env()

# Decorator Function
def check_user(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if True: # check user here
            return func(*args, **kwargs)
        else:
            return abort(403)
    return wrap

def connect_db():
    """Connects to the specific database."""
    return mysql.connection

@app.teardown_appcontext
def req_teardown(error):
    """Closes the database again at the end of the request."""
    pass

def _assert_login():
    logged_in = True if docker.info().get("Username") else False
    return logged_in

def _docker_login():
    rv = docker.login(username=app.config['DOCKER_USER'], password=app.config['DOCKER_PASSWORD'])
    print(rv)

@app.route('/')
@check_user
def show_entries():
    mysql_connection = connect_db()
    cursor = mysql_connection.cursor()
    cursor.execute('''SELECT * FROM fbctf.teams''')
    rv = cursor.fetchall()
    return jsonify(rv)


@app.route('/spawn_containers')
@check_user
def spawn_containers():
    docker.ping()
    if not _assert_login():
        _docker_login()
        print(docker.info().get('Username'))
    print(docker.images.list("{}/{}".format(app.config['DOCKER_USER'], app.config['DOCKER_PASSWORD'])))
    return "OK"

@app.route('/pull')
@check_user
def pull_image():
    if not _assert_login():
        _docker_login()
    image = docker.images.pull("0xbeef/ctf_challenges", "demo_app")
    print(image.tags)
    return "OK"

@app.route('/search')
@check_user
def search():
    if not _assert_login():
        _docker_login()
    resp = docker.images.list()
    for r in resp:
        print(r)
    return "OK"

app.run(host='0.0.0.0', port=8888, debug=True)