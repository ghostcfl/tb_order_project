import time
import datetime
import schedule

from core.spiders.store_search_page_spider import StoreSearchPageSpider
from tools.tools_method import time_zone

if __name__ == '__main__':
    t = time_zone(["18:00"])
    if datetime.datetime.now() > t[0]:
        StoreSearchPageSpider.run()
    schedule.every().day.at("18:00").do(StoreSearchPageSpider.run)
    while 1:
        schedule.run_pending()
        s = time.asctime()
        print(s[11:19], end="")
        time.sleep(1)
        print("\r", end="", flush=True)

# def run():
#     stroe_info = random.choice(list(STORE_INFO.values()))
#
#     loop = asyncio.get_event_loop()
#     login, browser, page, from_store = loop.run_until_complete(LoginTB.run(**stroe_info))
#     s = StoreSearchPageSpider(login, browser, page, from_store)
#     shop_ids = [
#         "115443253",
#         "131282813",
#         "197444037",
#         "33817767",
#         "34933991",
#         "60299985",
#         "68559944",
#     ]
#     write("exit_signal", 0)
#     for s_id in shop_ids:
#         loop.run_until_complete(s.get_page(s_id))
#         exit_signal = read("exit_signal")
#         if exit_signal:
#             break
#     loop.run_until_complete(browser.close())
#
#
# if __name__ == '__main__':
#     run()
#
#     schedule.every(1).seconds.do(run)
#     while 1:
#         schedule.run_pending()
#         time.sleep(1)
