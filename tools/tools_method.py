import time
import datetime


def time_format(format_string):
    return datetime.datetime.now().strftime(format_string)


def my_sleep(seconds=60):
    print(time_format("%Y-%d-%m %H:%M:%S") + " | ", end="", flush=True)
    for _ in range(int(seconds)):
        time.sleep(1)
        print(">", end="", flush=True)
    print("")
    time.sleep(1)


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



