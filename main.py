import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider
from core.spiders.delay_order_spider import DelayOrderUpdate
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.spiders.order_detail_link_id_spider import OrderDetailLinkIDSpider
from core.spiders.item_manage_page_spider import ItemManagePageSpider
from core.browser.login_tb import LoginTB
from settings import STORE_INFO
from tools.tools_method import delete, my_async_sleep
from tools.logger import logger
from db.my_sql import MySql


# async def task_1(list_spider, detail_spider):
#     page_num = 1
#     while 1:
#         completed = await list_spider.get_page(page_num)
#         if completed == 1:
#             page_num += 1
#         elif completed == 2:
#             page_num = 1
#         await detail_spider.get_page()
#
#         await asyncio.sleep(15)
#
#
# def async_run(shop_code):
#     delete(shop_code + "headers")
#     loop = asyncio.get_event_loop()
#     l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO[shop_code]))
#     o_l_p_s = OrderListPageSpider(l, b, p, f)
#     o_d_p_s = OrderDetailPageSpider(l, b, p, f)
#
#     tasks = [
#         task_1(o_l_p_s, o_d_p_s),
#         OrderDetailLinkIDSpider.run(l, b, p, f),
#         DelayOrderUpdate.run(l, b, p, f)
#     ]
#     loop.run_until_complete(asyncio.wait(tasks))


def run(shop_code):
    loop = asyncio.get_event_loop()
    login, browser, page, from_store = loop.run_until_complete(LoginTB.run(**STORE_INFO[shop_code]))

    list_page = page
    list_page_spider = OrderListPageSpider(login, browser, list_page, from_store)

    detail_page = loop.run_until_complete(login.new_page())
    detail_page_spider = OrderDetailPageSpider(login, browser, detail_page, from_store)

    link_id_page = loop.run_until_complete(login.new_page())
    link_id_spider = OrderDetailLinkIDSpider(login, browser, link_id_page, from_store)

    delay_order_page = loop.run_until_complete(login.new_page())
    delay_order_spider = DelayOrderUpdate(login, browser, delay_order_page, from_store)

    manager_page = loop.run_until_complete(login.new_page())
    manager_page_spider = ItemManagePageSpider(login, browser, delay_order_page, from_store)

    page_num = 1
    while 1:
        try:
            completed = loop.run_until_complete(list_page_spider.get_page(page_num))
            if completed == 1:
                page_num += 1
            elif completed == 2:
                MySql.cls_update(t="tb_order_spider", set={"isDetaildown": 0},
                                 c={"isDetaildown": 2, "fromStore": from_store})
                MySql.cls_update(t="tb_order_spider", set={"isVerify": 0},
                                 c={"isVerify": 2, "fromStore": from_store})
                page_num = 1
            elif completed == 'exit':
                break
            loop.run_until_complete(my_async_sleep(20, random_sleep=True))
            loop.run_until_complete(link_id_spider.save_link_id())
            # loop.run_until_complete(manager_page_spider.do_it())
            loop.run_until_complete(detail_page_spider.get_page())
            exit_loop = loop.run_until_complete(delay_order_spider.get_page())
            if exit_loop == 'exit':
                break
        except Exception as e:
            logger.error(str(e))
            break

    loop.run_until_complete(browser.close())
    # loop.close()
