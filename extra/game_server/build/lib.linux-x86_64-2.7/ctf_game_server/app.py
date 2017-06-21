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
from multiprocessing.pool import ThreadPool
import logging
from logging.handlers import RotatingFileHandler


application = Flask(__name__)
# Read config
application.config.from_pyfile('./config.py')

# bind to the docker socket
docker = docker_sdk.APIClient(base_url='unix://var/run/docker.sock')

# db init
init_db()

pool = ThreadPool(processes=1)

file_handler = RotatingFileHandler('/etc/game_server.logs', maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
application.logger.addHandler(file_handler)

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


@application.teardown_appcontext
def req_teardown(error):
    """Closes the database again at the end of the request."""
    db_session.remove()

@application.errorhandler(500)
def internal_error(exception):
    application.logger.error(exception)
    return render_template('internal_server_error.html', message=exception), 500

def _log_in(username, password):
    print('PERFORMING LOGIN')
    data = {'action': 'login_team', 'password': password, 'teamname': username}
    response = requests.post("https://localhost/index.php?p=index&ajax=true",
                             data=data, verify=False)
    assert response.status_code == 200
    # force reconect to the database
    db_session.remove()
    init_db()


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


def _pull_image(tag_name):
    try:
        challenge = "{}/{}:{}".format(application.config['DOCKER_USER'], application.config['CHALLENGES_REPO'], tag_name)
        response = docker.pull(challenge, auth_config={"Username": application.config['DOCKER_USER'],
                                                    "Password": application.config['DOCKER_PASSWORD']})
        if('up to date' in response or 'Downloaded newer' in response):
            image_data = _inspect_image_tag(challenge)
            challenge_data = image_data["Config"]["Labels"]
            session_cookies = _get_cookies(application.config['DEFAULT_ADMIN_TEAM_ID'])
            if len(session_cookies) > 0:
                pass
            else:
                # perform login
                _log_in(application.config['ADMIN_USER'], application.config['ADMIN_PASSWORD'])
                session_cookies = _get_cookies(application.config['DEFAULT_ADMIN_TEAM_ID'])
            latest_admin_session_cookie = session_cookies[0]
            session = latest_admin_session_cookie.get('cookie')
            csrf_token = latest_admin_session_cookie.get('csrf_token')
            _insert_challenge(challenge_data, session, csrf_token)
        else:
            raise Exception('failed to pull image from repository.')
    except Exception as ex:
        application.logger.error(str(ex))


def _pull_image_tag_as_stream(tag_name):
    challenge = "{}/{}:{}".format(application.config['DOCKER_USER'], application.config['CHALLENGES_REPO'], tag_name)
    for line in docker.pull(challenge, auth_config={"Username": application.config['DOCKER_USER'],
                                                    "Password": application.config['DOCKER_PASSWORD']}, stream=True):
        print(line)
        yield "data:" + str(line) + "\n\n"
    image_data = _inspect_image_tag(challenge)
    challenge_data = image_data["Config"]["Labels"]
    session_cookies = _get_cookies(application.config['DEFAULT_ADMIN_TEAM_ID'])
    if len(session_cookies) > 0:
        pass
    else:
        # perform login
        _log_in(application.config['ADMIN_USER'], application.config['ADMIN_PASSWORD'])
        session_cookies = _get_cookies(application.config['DEFAULT_ADMIN_TEAM_ID'])
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
    full_tag_list = []
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
            full_tag_list.append(str(image_tag))
    return full_tag_list


@application.route('/pull_all', methods=['GET'])
@check_user
def pull_images():
    tags = _get_image_tags(application.config['DOCKER_USER'], application.config['DOCKER_PASSWORD'],
                           application.config['DOCKER_LOGIN_SERVER'])
    return render_template('pull_all_images.html', tags=tags)


@application.route('/pull', methods=['GET'])
@check_user
def pull_image():
    print("------------------------------------------------------------------------")
    tag = request.args.get('tag')
    print("pulling {}".format(tag))
    if request.headers.get('accept') == 'text/event-stream':
        return Response(_pull_image_tag_as_stream(tag), mimetype='text/event-stream')
    else:
        return render_template('pull_image.html', tag=tag)


@application.route('/notify', methods=['POST'])
@check_user
def webhook_callback():
    data = json.loads(request.get_data())
    push_data = data['push_data']
    tag = push_data['tag']
    pool.apply_async(_pull_image, (tag,))
    return "OK"


@application.route('/test', methods=['GET'])
@check_user
def test():
    # special_craft = {'action': 'create_flag', 'title': "title_test_flask",
    #                  'description': "description", 'flag': 'whatever', 'entity_id': 0,
    #                  'category_id': 0, 'points': 200, 'hint': 'mhm', 'penalty': 10,
    #                  'csrf_token': "2cCvxfKT6Gu6w0oT34r6yk"}
    #cookie_list = _get_cookies(1)
    #print(cookie_list)
    # print("CONTAINER SPAWN REQUESTED")
    # data = json.loads(request.get_data())
    # print(data)
    # return "OK"
    # response = requests.post("http://10.10.10.5/index.php?p=admin&ajax=true",
    #                           data={'username': user, 'password': password})\
    tags = ["tag1", "bof", "binary_easy"]
    tags_string = ','.join(tags)
    return render_template('test.html', tags=tags)

if __name__=="__main__":
    application.run(host='0.0.0.0')
