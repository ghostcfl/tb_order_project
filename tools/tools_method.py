import re
import time
import datetime
import random
import shelve
import os
import asyncio


def time_format(format_string="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(format_string)


def my_sleep(seconds=60, random_sleep=None):
    if random_sleep:
        seconds = random.uniform(1, seconds)
    print(time_format() + " | ", end="", flush=True)
    while seconds > 1:
        time.sleep(1)
        print(">", end="", flush=True)
        seconds -= 1
    print("")
    time.sleep(seconds)


async def my_async_sleep(seconds=60, random_sleep=None):
    if random_sleep:
        seconds = random.uniform(1, seconds)
    print(time_format() + " | ", end="", flush=True)
    while seconds > 1:
        await asyncio.sleep(1)
        print(">", end="", flush=True)
        seconds -= 1
    print("")
    await asyncio.sleep(seconds)


def time_zone(args):
    time_list = []
    for t in args:
        d_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + t, '%Y-%m-%d%H:%M')
        time_list.append(d_time)
    return time_list


def yesterday(time_str):
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    yesterday = today - oneday
    return str(yesterday) + " " + time_str


def store_trans(string, action='code_2_name'):
    result_dict = {
        "code_2_name": {
            "YK": "玉佳企业店",
            "KY": "开源电子",
            "TB": "赛宝电子",
            "YJ": "玉佳电子",
        },
        "code_2_id": {
            "YK": "197444037",
            "KY": "115443253",
            "TB": "34933991",
            "YJ": "68559944",
        }
    }

    return result_dict[action][string]


def format_tb_name(string):
    string.strip().replace("&plusmn;", "±").replace("&Phi;", "Φ").replace("&Omega;", "Ω") \
        .replace("&mdash;", "—").replace("&deg;", "°").replace("&times;", "×") \
        .replace("&mu;", "μ").replace("&nbsp;", "").replace("（", "(").replace("）", ")")
    return string


def format_attribute(attriblue_list):
    temp = []
    for k in range(len(attriblue_list)):
        try:
            attriblue_list[k]['name']
        except KeyError:
            n = len(temp)
            temp[n - 1] += attriblue_list[k]['value'].replace("&Omega", "Ω").replace("&middot", "·")
        else:
            temp.append(
                attriblue_list[k]['value'].replace("&Omega", "Ω").replace("&middot", "·")
            )
        temp_ga = "-".join(temp)
        return temp_ga.replace("（", "(").replace("）", ")")


def status_format(string):
    list_name = ["等待买家付款", "买家已付款", "交易关闭", "已发货", "交易成功"]
    for i in list_name:
        a = re.search(i, string)
        if a:
            if a.group() == "已发货":
                temp = "卖家已发货"
            else:
                temp = a.group()
            return temp


def write(flag, value):
    path = os.path.dirname(__file__) + "/data"
    if not os.path.exists(path):
        os.mkdir(path)

    with shelve.open(path + "/data") as db:
        db[flag] = value


def read(flag):
    path = os.path.dirname(__file__) + "/data"
    if not os.path.exists(path):
        os.mkdir(path)
    try:
        with shelve.open(path + "/data") as db:
            try:
                return db[flag]
            except KeyError:
                return 0
    except FileNotFoundError:
        return 0


def delete(flag):
    path = os.path.dirname(__file__) + "/data"
    if not os.path.exists(path):
        os.mkdir(path)
    try:
        with shelve.open(path + "/data") as db:
            try:
                del db[flag]
            except KeyError:
                pass
    except FileNotFoundError:
        pass
