#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Flaskr + Babel + PhraseApp
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    Modified Flask demo app showing localization with Flask-Babel and PhraseApp
"""

from flask import Flask, Response, abort, jsonify, stream_with_context, send_file, request, render_template
from flask_mysqldb import MySQL
import docker as docker_sdk
from functools import wraps
import requests

# Create our little application :)
app = Flask(__name__)
# Read config
app.config.from_pyfile('config.py')
mysql = MySQL(app)
docker = docker_sdk.APIClient(base_url='unix://var/run/docker.sock')

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

def _docker_login():
    rv = docker.login(username=app.config['DOCKER_USER'], password=app.config['DOCKER_PASSWORD'])
    print(rv)

def _get_image_tags(user, password, api_endpoint):
    response = requests.post("{endpoint}/users/login/". format(endpoint=api_endpoint), data={'username': user, 'password': password})
    token = response.json().get('token')
    response = requests.get('{endpoint}/repositories/{username}/?page_size=10000'.format(endpoint = api_endpoint, username=user),
                            headers={'Authorization': 'JWT {token}'.format(token=token)})
    results = response.json().get('results')
    full_image_list = []
    for repo in results:
        repo_name = repo.get('name')
        response = requests.get(
            '{endpoint}/repositories/{username}/{repo_name}/tags/?page_size=10000'.format(endpoint=api_endpoint, username=user,
                                                                                                         repo_name=repo_name),
            headers={'Authorization': 'JWT {token}'.format(token=token)})
        image_tags = response.json().get('results')
        for tag in image_tags:
            image_tag = tag.get('name')
            full_image_tag = '{username}/{repository}:{tag}'.format(username=user, repository=repo_name, tag=image_tag)
            full_image_list.append(full_image_tag)
    return full_image_list

@app.route('/')
@check_user
def show_entries():
    mysql_connection = connect_db()
    cursor = mysql_connection.cursor()
    cursor.execute('''SELECT * FROM fbctf.teams''')
    rv = cursor.fetchall()
    return jsonify(rv)

@app.route('/pull')
@check_user
def pull_images():
    if request.headers.get('accept') == 'text/event-stream':
        comma_separated_images = request.args.get('images')
        images = comma_separated_images.split(',')
        def stream(images):
            for image in images:
                for line in docker.pull(*image.split(':'), stream = True):
                    yield "data:" + str(line) + "\n\n"
        return Response(stream(images), mimetype= 'text/event-stream')
    else:
        _docker_login()  # do not perform login every time
        images = _get_image_tags(app.config['DOCKER_USER'], app.config['DOCKER_PASSWORD'],
                                 app.config['DOCKER_API_SERVER'])
        return render_template('spawn_containers.html', images = images)

def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

@app.route('/spawn', methods=['POST'])
@check_user
def spawn_container():
    name = request.form['yourname']
    email = request.form['youremail']
    return "yeah_boy"


@app.route('/page')
def get_page():
    return send_file('templates/spawn_containers.html')

app.run(host='0.0.0.0', port=8888)