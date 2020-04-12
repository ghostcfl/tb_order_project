import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.spiders.order_detail_link_id_spider import OrderDetailLinkIDSpider
from core.browser.login_tb import LoginTB
from settings import STORE_INFO


async def task_1(list_spider, detail_spider, link_id_spider):
    page_num = 1
    while 1:
        completed = await list_spider.get_page(page_num)
        if completed == 1:
            page_num += 1
        elif completed == 2:
            page_num = 1
        await detail_spider.get_page(),
        await link_id_spider.run()


async def task_2(o_d_p_s, o_d_l_id_s):
    while 1:
        await asyncio.sleep(30)
        await o_d_p_s.get_page(),
        await o_d_l_id_s.run()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    o_l_p_s = OrderListPageSpider(l, b, p, f)
    o_d_p_s = OrderDetailPageSpider(l, b, p, f)
    o_d_l_id_s = OrderDetailLinkIDSpider(l, b, p, f)

    tasks = [
        task_1(o_l_p_s, o_d_p_s, o_d_l_id_s),
        # task_2(o_d_p_s, o_d_l_id_s)
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    # input("阻塞进程用的，后续要删除")
