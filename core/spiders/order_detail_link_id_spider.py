import asyncio
import datetime
import requests
import re
import json
from pyquery import PyQuery
from jsonpath import jsonpath

from core.spiders.base_spider import BaseSpider
from settings import TEST_SERVER_DB_TEST, FAST_EDIT_BTN
from db.my_sql import MySql
from tools.logger import logger
from model import PriceTBItem


class OrderDetailLinkIDSpider(BaseSpider):
    manager_page = None
    item_page = None
    price_tb_items = []

    async def intercept_response(self, res):
        req = res.request
        pattern = r'https://item.manager.taobao.com/taobao/manager/fastEdit.htm'
        if req.method == "POST" and re.search(pattern, res.url):
            data = await res.json()
            link_id = req.postData.split("=")[-1]
            await self.parse_manager_page(data, link_id)
        else:
            main_body = re.search(r'https://item.taobao.com/item.htm', req.url)
            detail_skip = re.search(r'https://detailskip.taobao.com', req.url)
            rate = re.search(r'https://rate.taobao.com', req.url)
            if main_body:
                content = await res.text()
                await self.parse_item_page(content=content)
            if detail_skip:
                detail = await res.text()
                await self.parse_item_page(detail=detail)
            if rate:
                rate = await res.text()
                await self.parse_item_page(rate=rate)

    async def run(self):
        self.completed = 0
        sql = """SELECT url,a.orderNo FROM tb_order_detail_spider a
            JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
            WHERE link_id="1" AND b.`fromStore`='%s' AND a.url IS NOT NULL
            ORDER BY b.createTime DESC""" % (self.fromStore)
        results = MySql.cls_get_dict(sql=sql)
        for result in results:
            data = await self._get_json(result['orderNo'])
            sub_orders = data["data"]["subOrderViewDTOs"]
            for so in sub_orders:
                ms = MySql()
                order_no = so["orderNoStr"]
                link_id = so["itemId"]
                sql = "select goodsCode from tb_order_detail_spider where url like '%%%s%%'" % (order_no)
                goodsCode = ms.get_one(sql=sql)
                sql = "update tb_order_detail_spider set link_id='%s' where url like '%%%s%%'" % (link_id, order_no)
                ms.update(sql=sql)
                await self.update_into_price_tb(goodsCode, link_id)

    async def update_into_price_tb(self, goodsCode, link_id):
        do_it = 0
        sql = "SELECT SpiderDate FROM prices_tb WHERE link_id='{}'" \
              "AND stockid='{}' AND flag NOT IN ('del','XiaJia')" \
            .format(link_id, goodsCode)
        res = MySql.cls_get(sql=sql)
        if res:
            spider_date = res[0][0]
            logger.info(spider_date)
            days = 1
            if spider_date != '0000-00-00 00:00:00' and spider_date:
                days = (datetime.datetime.now() - spider_date).days
            if not spider_date or spider_date == '0000-00-00 00:00:00' or days > 14:
                do_it = 1
        else:
            do_it = 1
        if do_it:
            logger.info(link_id)
            await self.do_it(link_id)
        else:
            self.completed = 3
        while 1:
            if self.completed == 3:
                break
            await asyncio.sleep(1)

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
            if not re.search(r"render.htm", self.manager_page.url):
                await self.manager_page.goto(base)
        except Exception as e:
            logger.error(str(e) + "manager_page_error")
            return
        while 1:
            await self.manager_page.waitForSelector("input[name='queryItemId']", timeout=0)
            await self.manager_page.keyboard.press('Escape')
            await self.manager_page.focus("input[name='queryItemId']")
            for _ in range(20):
                await self.manager_page.keyboard.press("Delete")
                await self.manager_page.keyboard.press("Backspace")
            await self.manager_page.type("input[name='queryItemId']", str(link_id),
                                         {'delay': self.login.input_time_random()})
            await self.manager_page.click(".filter-footer button:first-child")
            await self.manager_page.waitForResponse("https://item.manager.taobao.com/taobao/manager/table.htm")
            await asyncio.sleep(1)
            await self.manager_page.setRequestInterception(True)
            self.manager_page.on('request', self.intercept_request)
            self.manager_page.on('response', self.intercept_response)
            try:
                await self.manager_page.waitForSelector(FAST_EDIT_BTN)
                await self.manager_page.click(FAST_EDIT_BTN)
            except Exception as e:
                str(e)
                continue
            else:
                break
        while 1:
            if self.completed == 3:
                break
            await asyncio.sleep(1)

    async def parse_manager_page(self, data, link_id):
        self.price_tb_items = []
        if not jsonpath(data, '$..skuOuterIdTable'):
            price_tb_item = PriceTBItem()
            price_tb_item.link_id = link_id
            price_tb_item.description = jsonpath(data, '$..textTitle')[0]
            price_tb_item.stockid = jsonpath(data, '$..outerId')[0]
            self.price_tb_items.append(price_tb_item)
        else:
            tables = jsonpath(data, '$..skuOuterIdTable.dataSource')
            for table in tables[0]:
                price_tb_item = PriceTBItem()
                price_tb_item.link_id = link_id
                price_tb_item.description = jsonpath(data, '$..textTitle')[0]
                price_tb_item.skuId = str(jsonpath(table, '$..skuId')[0])
                price_tb_item.stockid = jsonpath(table, '$..skuOuterId')[0]
                # print(price_tb_item)
                self.price_tb_items.append(price_tb_item)
        await self.goto_tb_item_page()

    async def goto_tb_item_page(self):
        link_id = self.price_tb_items[0].link_id
        base = r"https://item.taobao.com/item.htm"
        pages = await self.browser.pages()
        for page in pages:
            if re.search(base, page.url):
                self.item_page = page
                break
        if not self.item_page:
            self.item_page = await self.login.new_page()
            await self.manager_page.bringToFront()
        try:
            await self.item_page.setRequestInterception(True)
            self.item_page.on('request', self.intercept_request)
            self.item_page.on('response', self.intercept_response)
            await self.item_page.goto(base + "?id=" + link_id)
        except Exception as e:
            logger.error(str(e) + "item_page_error")
            return
        while 1:
            if self.completed == 3:
                break
            await asyncio.sleep(1)

    async def parse_item_page(self, content=None, detail=None, rate=None):

        if content:
            sku_map = re.search('skuMap.*?(\{.*)', content)
            shop_id = re.search('rstShopId.*?(\d+)', content).group(1)
            doc = PyQuery(content)
            items = doc("li[data-value]").items()
            logger.debug(items)
            attr_map = {}
            if items:
                for item in items:
                    attr_map[item.attr('data-value')] = item.find('span').text()
            if sku_map:
                sku_dict = json.loads(sku_map.group(1))
                for k, v in sku_dict.items():
                    for price_tb_item in self.price_tb_items:
                        if price_tb_item.skuId == v.get('skuId'):
                            price_tb_item.price_tb = v.get('price')
                            price_tb_item.shop_id = shop_id
                            price_tb_item.attribute_map = k
                            price_tb_item.attribute = "-".join(
                                [attr_map.get(r) for r in re.sub('^;|;$', "", k).split(";")])
            else:
                self.price_tb_items[0].shop_id = shop_id
                self.price_tb_items[0].price_tb = doc('input[name="current_price"]').val()
            self.completed = 1
        if detail:
            while 1:
                if self.completed == 1:
                    break
                await asyncio.sleep(1)
            logger.debug(detail)
            data = re.search('uccess\((.*?)\);', detail)
            x = json.loads(data.group(1))
            promo_data = jsonpath(x, '$..promoData')
            if promo_data and promo_data[0]:
                for k, v in promo_data[0].items():
                    for price_tb_item in self.price_tb_items:
                        if k == price_tb_item.attribute_map:
                            price_tb_item.promotionprice = jsonpath(v, '$..price')[0]
                            price_tb_item.sales = jsonpath(x, '$..soldTotalCount')[0]
                            price_tb_item.typeabbrev = self.fromStore
            self.completed = 2
        if rate:
            while 1:
                if self.completed == 2:
                    break
                await asyncio.sleep(1)
            logger.debug(rate)
            ms = MySql()
            for price_tb_item in self.price_tb_items:
                count = re.search('(\d+)', rate)
                if count:
                    price_tb_item.rates = count.group(1)
                price_tb_item.save(ms)
            self.completed = 3

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
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['TB']))
    o_d_l_id_s = OrderDetailLinkIDSpider(l, b, p, f)
    loop.run_until_complete(o_d_l_id_s.do_it(""))
    loop.run_until_complete(o_d_l_id_s.run())
