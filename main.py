import asyncio

from core.spiders.order_list_page_spider import OrderListPageSpider
from core.spiders.order_detail_page_spider import OrderDetailPageSpider
from core.spiders.order_detail_link_id_spider import OrderDetailLinkIDSpider
from core.browser.login_tb import LoginTB
from settings import STORE_INFO

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    o_l_p_s = OrderListPageSpider(l, b, p, f)
    o_d_p_s = OrderDetailPageSpider(l, b, p, f)
    o_d_l_id_s = OrderDetailLinkIDSpider(l, b, p, f)
    page_num = 1
    while 1:
        completed = loop.run_until_complete(o_l_p_s.get_page(page_num))
        if completed == 1:
            page_num += 1
        elif completed == 2:
            page_num = 1
        loop.run_until_complete(o_d_p_s.get_page())
        # input("阻塞进程用的，后续要删除")
