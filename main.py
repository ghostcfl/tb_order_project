import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.browser.login_tb import LoginTB
from settings import STORE_INFO

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    olps = OrderListPageSpider(l, b, p, f)
    odps = OrderDetailPageSpider(l, b, p, f)
    page_num = 1
    while 1:
        completed = loop.run_until_complete(olps.get_page(page_num))
        if completed == 1:
            page_num += 1
        elif completed == 2:
            page_num = 1
        loop.run_until_complete(odps.get_page())
        input("阻塞进程用的，后续要删除")
