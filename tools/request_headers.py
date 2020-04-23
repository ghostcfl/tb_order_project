# 获得随机的user_agent的请求头
import requests
import shelve
import random
import os
from pyquery import PyQuery


def get_request_headers():
    """
    获取随机的请求头
    :return: headers
    """
    with shelve.open(os.path.dirname(__file__)+"/user_agent/data") as db:
        user_agents = db['user_agent']
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "item.taobao.com",
        "Upgrade-Insecure-Requests": "1",
    }
    return headers

def set_user_agent():
    """
    通过useragentstring.com爬取user_agents，并存储在本地文件中
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'http://useragentstring.com/pages/useragentstring.php',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    params = (
        ('typ', 'Browser'),
    )

    response = requests.get('http://useragentstring.com/pages/useragentstring.php', headers=headers, params=params)
    html = response.text
    doc = PyQuery(html)
    items = doc("ul li a").items()
    list_browsers = [item.text() for item in items if len(item.text()) > 80]
    print(list_browsers)
    with shelve.open(os.path.dirname(__file__)+"/user_agent/data") as db:
        db['user_agent'] = list_browsers
