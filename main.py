import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider, DelayOrderUpdate
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.spiders.order_detail_link_id_spider import OrderDetailLinkIDSpider
from core.browser.login_tb import LoginTB
from settings import STORE_INFO
from tools.tools_method import delete, my_async_sleep
from db.my_sql import MySql


async def task_1(list_spider, detail_spider):
    page_num = 1
    while 1:
        completed = await list_spider.get_page(page_num)
        if completed == 1:
            page_num += 1
        elif completed == 2:
            page_num = 1
        await detail_spider.get_page()

        await asyncio.sleep(15)


def async_run(shop_code):
    delete(shop_code + "headers")
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO[shop_code]))
    o_l_p_s = OrderListPageSpider(l, b, p, f)
    o_d_p_s = OrderDetailPageSpider(l, b, p, f)

    tasks = [
        task_1(o_l_p_s, o_d_p_s),
        OrderDetailLinkIDSpider.run(l, b, p, f),
        DelayOrderUpdate.run(l, b, p, f)
    ]
    loop.run_until_complete(asyncio.wait(tasks))


def run(shop_code):
    delete(shop_code + "headers")
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO[shop_code]))
    o_l_p_s = OrderListPageSpider(l, b, p, f)
    o_d_p_s = OrderDetailPageSpider(l, b, p, f)
    o_d_l_id_s = OrderDetailLinkIDSpider(l, b, p, f)
    d_o_u = DelayOrderUpdate(l, b, p, f)
    page_num = 1
    while 1:
        completed = loop.run_until_complete(o_l_p_s.get_page(page_num))
        if completed == 1:
            page_num += 1
        elif completed == 2:
            page_num = 1
        my_async_sleep(20, random_sleep=True)
        loop.run_until_complete(o_d_l_id_s.save_link_id())
        loop.run_until_complete(o_d_p_s.get_page())
        loop.run_until_complete(d_o_u.get_page())
        MySql.cls_update(t="tb_order_spider", set={"isDetaildown": 0},
                         c={"isDetaildown": 2, "fromStore": f})
        MySql.cls_update(t="tb_order_spider", set={"isVerify": 0},
                         c={"isVerify": 2, "fromStore": f})
