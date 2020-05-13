import asyncio
import subprocess

from db.my_sql import MySql
from settings import TEST_SERVER_DB_TEST
from tools.tools_method import time_now, time_ago
from tools.kill_pyppeteer_temp_file import kill_temp_file
from settings import SPIDER_ADDRESS


async def run():
    while 1:
        ms = MySql(db_setting=TEST_SERVER_DB_TEST)
        ms.update(t="spider_monitor",
                  set={"latest_time": time_now()},
                  c={"spider_address": SPIDER_ADDRESS})
        restart_signal = ms.get_one(t="spider_monitor", cn=["restart_signal"], c={"spider_address": SPIDER_ADDRESS})
        if SPIDER_ADDRESS == "3_floor":
            sql = "SELECT MAX(updateTime) as updateTime,fromStore FROM tb_order_spider WHERE fromStore IN ('KY','TB') GROUP BY fromStore"
        else:
            sql = "SELECT MAX(updateTime) as updateTime,fromStore FROM tb_order_spider WHERE fromStore IN ('YJ','YK') GROUP BY fromStore"
        results = MySql.cls_get_dict(sql=sql)
        t = time_ago(minutes=15)
        for result in results:
            if str(result['updateTime']) < t:
                restart_signal = 1
                break
        if restart_signal:
            restart()
        del ms


def restart():
    kill_temp_file()
    cmd_list = [
        "ping www.baidu.com",
        "taskkill /F /IM chrome.exe",
        "shutdown -r -t 60",
        "taskkill /F /IM python.exe",
    ]
    for cmd in cmd_list:
        x = subprocess.run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)


if __name__ == '__main__':
    # restart()
    asyncio.run(run())
