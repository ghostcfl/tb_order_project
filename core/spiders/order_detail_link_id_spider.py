import asyncio
import datetime
import requests
import re
from jsonpath import jsonpath

from core.spiders.base_spider import BaseSpider
from settings import TEST_SERVER_DB_TEST
from db.my_sql import MySql
from tools.logger import logger
from model import PriceTBItem


class OrderDetailLinkIDSpider(BaseSpider):
    manager_page = None

    async def intercept_response(self, res):
        req = res.request
        pattern = r'https://item.manager.taobao.com/taobao/manager/fastEdit.htm'
        if req.method == "POST" and re.search(pattern, res.url):
            data = await res.json()
            await self.parse(data)

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
        do_it = 0
        sql = "SELECT SpiderDate FROM prices_tb WHERE link_id='{}'" \
              "AND stockid='{}' AND flag NOT IN ('del','XiaJia')" \
            .format(link_id, goodsCode)
        res = ms.get(sql=sql)
        if res:
            spider_date = res[0][0]
            days = 1
            if spider_date != '0000-00-00 00:00:00' and spider_date:
                days = (datetime.datetime.now() - spider_date).days
            if not spider_date or spider_date == '0000-00-00 00:00:00' or days > 14:
                do_it = 1
        else:
            do_it = 1
        if do_it:
            await self.do_it(link_id)

    async def do_it(self, link_id):
        base = "https://item.manager.taobao.com/taobao/manager/render.htm"
        pages = await self.browser.pages()
        for page in pages:
            if re.search(r"render.htm", page.url):
                self.manager_page = page
                break
        if not self.manager_page:
            self.manager_page = await self.login.new_page()

        try:
            await self.manager_page.goto(base)
        except Exception as e:
            logger.error(str(e) + "manager_page_error")
            return

        await self.manager_page.waitForSelector("input[name='queryItemId']", timeout=0)
        await self.manager_page.keyboard.press('Escape')
        for _ in range(20):
            await self.manager_page.keyboard.press("Delete")
            await self.manager_page.keyboard.press("Backspace")
        await self.manager_page.type("input[name='queryItemId']", link_id)
        await asyncio.sleep(2)
        await self.manager_page.click(".filter-footer button:first-child")
        await asyncio.sleep(2)
        await self.manager_page.setRequestInterception(True)
        self.manager_page.on('request', self.intercept_request)
        self.manager_page.on('response', self.intercept_response)
        await self.manager_page.click(".next-table-row td:nth-child(2) div.product-desc-hasImg span:nth-child(2) i")
        await asyncio.sleep(600)

    async def parse(self, data):
        if not jsonpath(data, '$..skuOuterIdTable'):
            price_tb_item = PriceTBItem()
            price_tb_item.description = jsonpath(data, '$..textTitle')
            price_tb_item.stockid = jsonpath(data, '$..outerId')
            print(price_tb_item)
        else:
            tables = jsonpath(data, '$..skuOuterIdTable.dataSource')
            for table in tables[0]:
                price_tb_item = PriceTBItem()
                price_tb_item.description = jsonpath(data, '$..textTitle')
                price_tb_item.skuId = jsonpath(table, '$..skuId')
                price_tb_item.stockid = jsonpath(table, '$..skuOuterId')
                print(price_tb_item)

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
    loop.run_until_complete(o_d_l_id_s.do_it("598514844544"))
