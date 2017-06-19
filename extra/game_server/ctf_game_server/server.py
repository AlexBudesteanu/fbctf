#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

from flask import Flask, Response, abort, jsonify, request, render_template
import docker as docker_sdk
from functools import wraps
import requests
import json
from database import db_session, init_db
from models import Level
import memcache

app = Flask(__name__)
# Read config
app.config.from_pyfile('config.py')
cache = memcache.Client(['127.0.0.1:11211'], debug=0)

# bind to the docker socket
docker = docker_sdk.APIClient(base_url='unix://var/run/docker.sock')

# db init
init_db()


# Decorator Function
def check_user(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if True:  # check user here
            return func(*args, **kwargs)
        else:
            return abort(403)

    return wrap


@app.teardown_appcontext
def req_teardown(error):
    """Closes the database again at the end of the request."""
    db_session.remove()


def _insert_challenge(challenge_data):
    # insert into db
    # challenge = Level(challenge_data.get("title"), challenge_data.get("description"), challenge_data.get("points"),
    #                    "hardcoded_flag", "no hint", 0, 0, 0)
    # db_session.add(challenge)
    # db_session.commit()
    special_craft = {'action': 'create_flag', 'title': challenge_data.get("title"),
                     'description': challenge_data.get("description"), 'flag': 'whatever', 'entity_id': 0,
                     'category_id': 0, 'points': 200, 'hint': 'mhm', 'penalty': 10, 'csrf_token': "S8L00ZwNWopSYNHZzfcAV"}
    response = requests.post("http://localhost/index.php?p=admin&ajax=true",
                             data=special_craft, verify=False)
    print(response.content)


def _pull_image_tag_as_stream(tag_name):
    challenge = "{}/{}:{}".format(app.config['DOCKER_USER'], app.config['CHALLENGES_REPO'], tag_name)
    for line in docker.pull(challenge, auth_config={"Username": app.config['DOCKER_USER'],
                                                    "Password": app.config['DOCKER_PASSWORD']}, stream=True):
        print(line)
        yield "data:" + str(line) + "\n\n"
    image_data = _inspect_image_tag(challenge)
    challenge_data = image_data["Config"]["Labels"]
    _insert_challenge(challenge_data)


def _inspect_image_tag(image_tag):
    ret = docker.inspect_image(image_tag)
    return ret


def _get_image_tags(user, password, api_endpoint):
    response = requests.post("{endpoint}/users/login/".format(endpoint=api_endpoint),
                             data={'username': user, 'password': password})
    token = response.json().get('token')
    response = requests.get(
        '{endpoint}/repositories/{username}/?page_size=10000'.format(endpoint=api_endpoint, username=user),
        headers={'Authorization': 'JWT {token}'.format(token=token)})
    results = response.json().get('results')
    full_image_list = []
    for repo in results:
        repo_name = repo.get('name')
        response = requests.get(
            '{endpoint}/repositories/{username}/{repo_name}/tags/?page_size=10000'.format(endpoint=api_endpoint,
                                                                                          username=user,
                                                                                          repo_name=repo_name),
            headers={'Authorization': 'JWT {token}'.format(token=token)})
        image_tags = response.json().get('results')
        for tag in image_tags:
            image_tag = tag.get('name')
            full_image_tag = '{username}/{repository}:{tag}'.format(username=user, repository=repo_name, tag=image_tag)
            full_image_list.append(full_image_tag)
    return full_image_list


@app.route('/pull_all', methods=['GET'])
@check_user
def pull_images():
    if request.headers.get('accept') == 'text/event-stream':
        comma_separated_images = request.args.get('images')
        images = comma_separated_images.split(',')

        def stream(images):
            for image in images:
                for line in docker.pull(*image.split(':'), stream=True):
                    yield "data:" + str(line) + "\n\n"

        return Response(stream(images), mimetype='text/event-stream')
    else:
        images = _get_image_tags(app.config['DOCKER_USER'], app.config['DOCKER_PASSWORD'],
                                 app.config['DOCKER_API_SERVER'])
        return render_template('pull_images.html', images=images)


@app.route('/pull', methods=['GET'])
@check_user
def pull_image():
    tag = request.args.get('tag')
    if request.headers.get('accept') == 'text/event-stream':
        return Response(_pull_image_tag_as_stream(tag), mimetype='text/event-stream')
    else:
        return render_template('pull_images.html', tag=tag)


@app.route('/notify', methods=['POST'])
@check_user
def webhook_callback():
    data = json.loads(request.get_data())
    push_data = data['push_data']
    tag = push_data['tag']
    return render_template('pull_images.html', tag=tag)


@app.route('/inspect', methods=['GET'])
def inpect_image():
    tag = request.args.get('tag')
    data = _inspect_image_tag(tag)
    return data


@app.route('/test_db', methods=['GET'])
def test_db():
    r = Level.query.all()
    return jsonify(r)


# @app.route('/test_insert', methods=['GET'])
# def test():
#     response = requests.post("http://10.10.10.5/index.php?p=admin&ajax=true",
#                              data={'username': user, 'password': password})

app.run(host='0.0.0.0', port=8888, debug=True)
