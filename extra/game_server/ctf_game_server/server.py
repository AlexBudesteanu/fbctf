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
from models import Level, Session
import re
from sqlalchemy import desc
import time


app = Flask(__name__)
# Read config
app.config.from_pyfile('config.py')

# bind to the docker socket
docker = docker_sdk.APIClient(base_url='unix://var/run/docker.sock')

# db init
init_db()

# Decorator Function
def check_user(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        cookie_list = request.cookies
        print(cookie_list)
        if True:  # check user here
            return func(*args, **kwargs)
        else:
            return abort(403)

    return wrap


@app.teardown_appcontext
def req_teardown(error):
    """Closes the database again at the end of the request."""
    db_session.remove()


def _log_in(username, password):
    pass


def _get_cookies(team_id=None):
    cookies = Session.query.order_by(desc(Session.created_ts)).all()
    cookie_list = []
    for cookie in cookies:
        cookie_raw = cookie.__repr__()
        cookie_data = cookie_raw['data']
        list_of_tuples = [re.split("\|s:[0-9]+:", item) for item in
                          cookie_data.split(';')[:-1]]  # values are wrapped in double quotes
        cookie_data_dict = dict(list_of_tuples)
        # replace double quotes from data dict
        for key, value in cookie_data_dict.items():
            cookie_data_dict[key] = value.replace('"', '')
        del cookie_raw['data']
        cookie_dict = cookie_raw.copy()
        cookie_dict.update(cookie_data_dict)
        if team_id:
            if cookie_dict['team_id'] == str(team_id):
                cookie_list.append(cookie_dict)
        else:
            cookie_list.append(cookie_dict)

    return cookie_list


def _insert_challenge(challenge_data, session, csrf_token):
    print('INSERTING CHALLENGE')
    cookies = {"FBCTF": session}
    data = {'action': 'create_flag', 'title': challenge_data.get("title"),
            'description': challenge_data.get("description"), 'flag': 'whatever', 'entity_id': 0,
            'category_id': 1, 'points': 200, 'hint': 'mhm', 'penalty': 10,
            'csrf_token': csrf_token}
    response = requests.post("https://localhost/index.php?p=admin&ajax=true",
                             data=data, cookies=cookies, verify=False)
    assert response.status_code == 200


def _pull_image_tag_as_stream(tag_name):
    challenge = "{}/{}:{}".format(app.config['DOCKER_USER'], app.config['CHALLENGES_REPO'], tag_name)
    for line in docker.pull(challenge, auth_config={"Username": app.config['DOCKER_USER'],
                                                    "Password": app.config['DOCKER_PASSWORD']}, stream=True):
        yield "data:" + str(line) + "\n\n"
    image_data = _inspect_image_tag(challenge)
    challenge_data = image_data["Config"]["Labels"]
    session_cookies = _get_cookies(app.config['DEFAULT_ADMIN_TEAM_ID'])
    if len(session_cookies) > 0:
        pass
    else:
        # perform login
        print('PERFORMING LOGIN')
        data = {'action': 'login_team', 'password': app.config['ADMIN_PASSWORD'], 'teamname': app.config['ADMIN_USER']}
        response = requests.post("https://localhost/index.php?p=index&ajax=true",
                                 data=data, verify=False)
        assert response.status_code == 200
        # force reconect to the database
        db_session.remove()
        init_db()
        session_cookies = _get_cookies(app.config['DEFAULT_ADMIN_TEAM_ID'])
    latest_admin_session_cookie = session_cookies[0]
    session = latest_admin_session_cookie.get('cookie')
    csrf_token = latest_admin_session_cookie.get('csrf_token')
    _insert_challenge(challenge_data, session, csrf_token)


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


@app.route('/test', methods=['GET'])
@check_user
def test():
    # special_craft = {'action': 'create_flag', 'title': "title_test_flask",
    #                  'description': "description", 'flag': 'whatever', 'entity_id': 0,
    #                  'category_id': 0, 'points': 200, 'hint': 'mhm', 'penalty': 10,
    #                  'csrf_token': "2cCvxfKT6Gu6w0oT34r6yk"}
    #cookie_list = _get_cookies(1)
    #print(cookie_list)
    print("CONTAINER SPAWN REQUESTED")
    data = json.loads(request.get_data())
    print(data)
    return "OK"
    # response = requests.post("http://10.10.10.5/index.php?p=admin&ajax=true",
    #                          data={'username': user, 'password': password})


app.run(host='0.0.0.0', port=8888, debug=True)
