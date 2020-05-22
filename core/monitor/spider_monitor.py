import asyncio
import subprocess
from subprocess import check_output

from db.my_sql import MySql
from settings import TEST_SERVER_DB_TEST, SPIDER_ADDRESS, MAIL_RECEIVERS
from tools.tools_method import time_now, time_ago
from tools.kill_pyppeteer_temp_file import kill_temp_file
from tools.mail import mail


async def run():
    while 1:
        update()
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
            ms.update(t="spider_monitor",
                      set={"restart_signal": 0},
                      c={"spider_address": SPIDER_ADDRESS})
            restart()
        del ms
        await asyncio.sleep(60)


def update():
    ms = MySql(db_setting=TEST_SERVER_DB_TEST)
    update_signals = ms.get_dict(t="spider_monitor", cn=["spider_address", "update_signal"])
    for update_signal in update_signals:
        if update_signal['update_signal']:
            result = check_output(['git', 'pull'])
            ms.update(t='spider_monitor',
                      set={"update_signal": 0, "update_result": result.decode('utf-8').strip()},
                      c={"spider_address": update_signal['spider_address']})


def restart():
    kill_temp_file()
    cmd_list = [
        "ping www.baidu.com",
        "taskkill /F /IM chrome.exe",
        "shutdown -r -t 60",
        "taskkill /F /IM python.exe",
    ]
    mail(SPIDER_ADDRESS + "爬虫自动重启", "", MAIL_RECEIVERS)
    for cmd in cmd_list:
        x = subprocess.run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)


if __name__ == '__main__':
    # restart()
    asyncio.run(run())
