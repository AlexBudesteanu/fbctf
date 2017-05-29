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
import docker

# Create our little application :)
app = Flask(__name__)
# Read config
app.config.from_pyfile('config.py')
mysql = MySQL(app)


def connect_db():
    """Connects to the specific database."""
    return mysql.connection


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    pass

@app.route('/')
def show_entries():
    mysql_connection = connect_db()
    cursor = mysql_connection.cursor()
    cursor.execute('''SELECT * FROM fbctf.teams''')
    rv = cursor.fetchall()
    return jsonify(rv)

@app.route('/spawn')
def spawn_container():
    client = docker.from_env()
    client.containers.run('0xbeef/ctf_challenges:demo_app',
                          detach=True)

app.run(host='0.0.0.0', port=8888, debug=True)