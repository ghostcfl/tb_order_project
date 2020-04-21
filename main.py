import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider
from core.spiders.delay_order_spider import DelayOrderUpdate
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.spiders.order_detail_link_id_spider import OrderDetailLinkIDSpider
from core.spiders.item_manage_page_spider import ItemManagePageSpider
from core.spiders.captcha_check import CaptchaCheck
from core.browser.login_tb import LoginTB
from settings import STORE_INFO
from tools.tools_method import delete, my_async_sleep
from tools.logger import logger
from db.my_sql import MySql


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
    item_page = loop.run_until_complete(login.new_page())
    manager_page_spider = ItemManagePageSpider(login, browser, manager_page,item_page, from_store)
    tasks = [
        taks_1(browser, delay_order_spider, detail_page_spider, manager_page_spider, from_store, link_id_spider,
               list_page_spider),
        # CaptchaCheck.run()
    ]
    loop.run_until_complete(asyncio.wait(tasks))


async def taks_1(browser, delay_order_spider, detail_page_spider, manager_page_spider, from_store, link_id_spider,
                 list_page_spider):
    page_num = 1
    while 1:
        try:
            completed = await list_page_spider.get_page(page_num)
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
            await my_async_sleep(20, random_sleep=True)
            await link_id_spider.save_link_id()
            await manager_page_spider.do_it()
            await detail_page_spider.get_page()
            exit_loop = await delay_order_spider.get_page()
            if exit_loop == 'exit':
                break
        except Exception as e:
            logger.error(str(e))
            break
    await browser.close()
