import requests
from core.spiders.base_spider import BaseSpider
from settings import TEST_SERVER_DB_TEST
from db.my_sql import MySql
from tools.logger import logger


class OrderDetailLinkIDSpider(BaseSpider):
    async def run(self):
        global ms
        ms = MySql()
        sql = """SELECT url,a.orderNo FROM tb_order_detail_spider a
            JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
            WHERE link_id="1" AND b.`fromStore`='%s' AND a.url IS NOT NULL
            ORDER BY b.createTime DESC"""
        results = MySql.get(sql=sql)
        for result in results:
            data = await self._get_json(result['orderNo'])
            sub_orders = data["data"]["subOrderViewDTOs"]
            for so in sub_orders:
                order_no = so["orderNoStr"]
                link_id = so["itemId"]
                logger.info(link_id)
                sql = "select goodsCode from tb_order_detail_spider where url like '%%%s%%'" % (order_no)
                goodsCode = ms.get_one(sql=sql)
                del sql
                sql = "update tb_order_detail_spider set link_id='%s' where url like '%%%s%%'" % (link_id, order_no)
                ms.update(sql=sql)
                del sql
                await self.update_into_price_tb(goodsCode, link_id)

    async def update_into_price_tb(self, goodsCode, link_id):
        global ms
        sql = "SELECT SpiderDate FROM prices_tb WHERE link_id='{}'" \
              "AND stockid='{}' AND flag NOT IN ('del','XiaJia')" \
            .format(link_id, goodsCode)
        res = ms.get(sql=sql)

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
