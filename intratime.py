import json
import requests


API_URL = "http://newapi.intratime.es"
API_LOGIN_PATH = "/api/user/login"
API_CLOCKING_PATH = "/api/user/clocking"
API_HEADER = {
    "Accept": "application/vnd.apiintratime.v1+json",
    "Content-Type": "application/x-www-form-urlencoded",
    "charset": "utf8"
}


def get_login_token(username, password):
    login_api_url = f"{API_URL}{API_LOGIN_PATH}"
    payload = f"user={username}&pin={password}"
    try:
        request = requests.post(login_api_url, data=payload, headers=API_HEADER)
        token = json.loads(request.text)['USER_TOKEN']

    except:
        raise ValueError("Invalid username or password")

    return token


def clocking(action, token, date_time, location):
    api_action = get_action(action)
    clocking_api_url = f"{API_URL}{API_CLOCKING_PATH}"
    API_HEADER.update({"token": token})

    payload = f"user_action={api_action}&user_use_server_time=False&user_timestamp={date_time}&user_gps_coordinates={location}"
    request = requests.post(clocking_api_url, data=payload, headers=API_HEADER)
    if request.status_code == 201:
        return f"[ACTION] {action} [TIME] {date_time}"

    else:
        raise ValueError("Registration failed, please try again")


def get_action(action):
    switcher = {
        "in": 0,
        "out": 1,
        "pause": 2,
        "return": 3,
    }

    return switcher.get(action, None)
