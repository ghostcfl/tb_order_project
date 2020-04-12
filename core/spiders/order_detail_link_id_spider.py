import asyncio
import datetime
import requests

from core.spiders.base_spider import BaseSpider
from db.my_sql import MySql
from tools.logger import logger
from tools.tools_method import store_trans
from model import PriceTBItem
from core.spiders.item_manage_page_spider import ItemManagePageSpider


class OrderDetailLinkIDSpider(BaseSpider):

    async def run(self):
        ms = MySql()
        self.completed = 0
        sql = """SELECT url,a.orderNo FROM tb_order_detail_spider a
            JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
            WHERE link_id="1" AND b.`fromStore`='{}' AND a.url IS NOT NULL
            ORDER BY b.createTime DESC""".format(self.fromStore)
        results = ms.get_dict(sql=sql)
        for result in results:
            data = await self._get_json(result['orderNo'])
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
                # print(price_tb_item.__str__())
                do_it = price_tb_item.save(ms)
                if do_it:
                    await ItemManagePageSpider.run(self.login, self.browser, self.page, self.fromStore, price_tb_item.link_id)
                sql = "update tb_order_detail_spider set link_id='{}' where url like '%{}%'".format(
                    price_tb_item.link_id, order_no
                )
                # print(sql)
                ms.update(sql=sql)

                # do_it = 0
                # sql = "SELECT SpiderDate FROM prices_tb WHERE link_id='{}'" \
                #       "AND stockid='{}' AND flag NOT IN ('del','XiaJia')" \
                #     .format(price_tb_item.link_id, price_tb_item.stockid)
                # res = ms.get(sql=sql)
                # if res:
                #     spider_date = res[0][0]
                #     logger.info(spider_date)
                #     days = 1
                #     if spider_date != '0000-00-00 00:00:00' and spider_date:
                #         days = (datetime.datetime.now() - spider_date).days
                #     if not spider_date or spider_date == '0000-00-00 00:00:00' or days > 14:
                #         do_it = 1
                # else:
                #     do_it = 1
                # if do_it:
                #     logger.info(price_tb_item.link_id)

    async def _get_json(self, order_no):
        url = 'https://smf.taobao.com/promotionmonitor/orderPromotionQuery.htm?orderNo=' + order_no
        cookies = await self.login.get_cookie(self.page)
        user_agent = await self.browser.userAgent()
        headers = {
            'User-Agent': user_agent,
            'Cookie': cookies
        }
        r = requests.get(url=url, headers=headers)
        x = r.json()
        return x


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    o_d_l_id_s = OrderDetailLinkIDSpider(l, b, p, f)
    loop.run_until_complete(o_d_l_id_s.run())
