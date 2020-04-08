import re
import time
import datetime
import random


def time_format(format_string):
    return datetime.datetime.now().strftime(format_string)


def my_sleep(seconds=60, random_sleep=None):
    if random_sleep:
        seconds = random.uniform(1, seconds)
    print(time_format("%Y-%d-%m %H:%M:%S") + " | ", end="", flush=True)
    while seconds > 1:
        time.sleep(1)
        print(">", end="", flush=True)
        seconds -= 1
    print("")
    time.sleep(seconds)


def time_zone(args):
    time_list = []
    for t in args:
        d_time = datetime.datetime.strptime(str(datetime.datetime.now().date()) + t, '%Y-%m-%d%H:%M')
        time_list.append(d_time)
    return time_list


def store_trans(string):
    if string == "YK":
        return '玉佳企业店'
    elif string == "KY":
        return "开源电子"
    elif string == "SC":
        return '微信商城'
    elif string == "VP":
        return '批发'
    elif string == "YJ":
        return "玉佳电子"
    elif string == "TB":
        return "赛宝电子"


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
