# http request tool
import requests


def http_request():
    request = requests.request("GET", "http://www.baidu.com")
    print(request.text)