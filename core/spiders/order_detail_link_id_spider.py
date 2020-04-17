import asyncio
import json
import re

from core.spiders.base_spider import BaseSpider
from db.my_sql import MySql
from tools.logger import logger
from tools.tools_method import store_trans, my_async_sleep, read
from model import PriceTBItem
from core.spiders.item_manage_page_spider import ItemManagePageSpider


class OrderDetailLinkIDSpider(BaseSpider):

    async def save_link_id(self):
        ms = MySql()
        link_id_new_list = []
        self.completed = 0
        sql = """SELECT url,a.orderNo FROM tb_order_detail_spider a
            JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
            WHERE link_id="1" AND b.`fromStore`='{}' AND a.url IS NOT NULL
            GROUP BY a.orderNo
            ORDER BY b.createTime DESC""".format(self.fromStore)
        results = ms.get_dict(sql=sql)
        if results:
            for result in results:
                logger.info("link_id_spider-" + result['orderNo'])
                data = await self._get_json(result['orderNo'])
                if not data:
                    return 0
                sub_orders = data["data"]["subOrderViewDTOs"]
                for so in sub_orders:
                    price_tb_item = PriceTBItem()
                    price_tb_item.link_id = so["itemId"]

                    order_no = so["orderNoStr"]
                    sql = "select * from tb_order_detail_spider where url like '%%{}%%'".format(order_no)
                    res = ms.get_dict(sql=sql)[0]

                    price_tb_item.stockid = res['goodsCode']
                    price_tb_item.description = res['tbName']
                    price_tb_item.price_tb = res['unitPrice']
                    price_tb_item.shop_id = store_trans(string=self.fromStore, action="code_2_id")
                    price_tb_item.attribute = res['goodsAttribute']
                    price_tb_item.typeabbrev = self.fromStore
                    sql = "update tb_order_detail_spider set link_id='{}' where url like '%{}%'".format(
                        price_tb_item.link_id, order_no
                    )
                    ms.update(sql=sql)
                    price_tb_item.save(ms)
                    await my_async_sleep(3, True)

    async def _get_json(self, order_no):
        url = 'https://smf.taobao.com/promotionmonitor/orderPromotionQuery.htm?orderNo=' + order_no
        await self.page.bringToFront()
        try:
            await self.page.goto(url)
        except Exception as e:
            logger.error(order_no + " link_id_error " + str(e))
            return 0
        else:
            content = await self.page.content()
            return json.loads(re.findall("<body>(.*?)</body>", content)[0])

    @classmethod
    async def run(cls, login, browser, page, from_store):
        while 1:
            link_id_spider = OrderDetailLinkIDSpider(login, browser, page, from_store)
            await link_id_spider.save_link_id()
            await my_async_sleep(15)


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    r = OrderDetailLinkIDSpider(l, b, p, f)
    # loop.run_until_complete(OrderDetailLinkIDSpider.run(l, b, p, f))
    g = loop.run_until_complete(r.get_json('598093679034153502'))
    print(g)
