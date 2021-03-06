import re
import json
import asyncio
from pyquery import PyQuery
from jsonpath import jsonpath
from pyppeteer import errors

from settings import FAST_EDIT_BTN
from core.spiders.base_spider import BaseSpider
from tools.logger import logger
from tools.tools_method import store_trans, time_now
from model import PriceTBItem
from db.my_sql import MySql


class ItemManagePageSpider(BaseSpider):
    manager_page = None
    item_page = None
    price_tb_items = []

    def __init__(self, login, browser, page, item_page, fromStore):
        super().__init__(login, browser, page, fromStore)
        self.item_page = item_page

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

    async def do_it(self):
        shop_id = store_trans(self.fromStore, 'code_2_id')
        ms = MySql()
        sql = "select link_id from prices_tb where need_to_update=1 and shop_id='{}' limit 1".format(shop_id)
        link_id = ms.get_one(sql=sql)
        if not link_id:
            return 0
        await self.page.bringToFront()

        try:
            if not re.search("https://item.manager.taobao.com/taobao/manager/render.htm", self.page.url):
                await self.page.goto("https://item.manager.taobao.com/taobao/manager/render.htm?tab=on_sale")
        except Exception as e:
            logger.error(str(e) + "manager_page_error")
            return
        while 1:
            await self.page.waitForSelector("input[name='queryItemId']", timeout=0)
            await self.page.keyboard.press('Escape')
            await self.page.focus("input[name='queryItemId']")
            for _ in range(20):
                await self.page.keyboard.press("Delete")
                await self.page.keyboard.press("Backspace")
            await self.page.type("input[name='queryItemId']", str(link_id),
                                 {'delay': self.login.input_time_random()})
            await self.page.click(".filter-footer button:first-child")
            await self.page.waitForResponse("https://item.manager.taobao.com/taobao/manager/table.htm")
            await asyncio.sleep(1)
            await self.listening(self.page)
            try:
                await self.page.waitForSelector(FAST_EDIT_BTN, timout=10000)
                await self.page.click(FAST_EDIT_BTN)
                restart = await self.login.slider(self.page)
                if restart:
                    exit("滑块验证码失败，退出")
            except errors.TimeoutError as e:
                logger.info("商品已下架，没有查询到对应的商品ID：" + link_id)
                ms.update(t="prices_tb", set={"SpiderDate": time_now(), "need_to_update": 0, "flag": "XiaJia"},
                          c={"link_id": link_id})
                link_id = ms.get_one(sql=sql)
                if not link_id:
                    return 0
                continue
            else:
                await self.page.focus("input[name='queryItemId']")
                for _ in range(20):
                    await self.page.keyboard.press("Delete")
                    await self.page.keyboard.press("Backspace")
                break
        while 1:
            if self.completed == 4:
                break
            await asyncio.sleep(1)
        await asyncio.sleep(15)

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
                price_tb_item.description = jsonpath(data, '$..textTitle')[0].replace("（", "(").replace("）", ")")
                price_tb_item.skuId = str(jsonpath(table, '$..skuId')[0])
                price_tb_item.stockid = ""
                if jsonpath(table, '$..skuOuterId'):
                    price_tb_item.stockid = jsonpath(table, '$..skuOuterId')[0]
                self.price_tb_items.append(price_tb_item)
        self.completed = 1
        await asyncio.sleep(10)
        await self.goto_tb_item_page()

    async def goto_tb_item_page(self):
        await self.item_page.bringToFront()
        link_id = self.price_tb_items[0].link_id
        logger.info(link_id)
        base = r"https://item.taobao.com/item.htm"
        # self.item_page = await self.login.new_page()
        while 1:
            try:
                await self.listening(self.item_page)
                await self.item_page.goto(base + "?id=" + link_id, timeout=0)
            except Exception as e:
                logger.error(str(e) + "item_page_error")
                restart = await self.login.slider(self.item_page)
                if restart:
                    self.completed = 'exit'
            else:
                # await self.item_page.reload()
                break
        while 1:
            if self.completed == 4:
                break
            await asyncio.sleep(1)

    async def parse_item_page(self, content=None, detail=None, rate=None):

        if content:
            sku_map = re.search('skuMap.*?(\{.*)', content)
            shop_id = store_trans(self.fromStore, 'code_2_id')
            doc = PyQuery(content)
            items = doc("li[data-value]").items()
            logger.debug(items)
            attr_map = {}
            if items:
                for item in items:
                    attr_map[item.attr('data-value')] = item.find('span').text().replace("（", "(").replace("）", ")")
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
            self.completed = 2
        if detail:
            while 1:
                if self.completed == 2:
                    break
                await asyncio.sleep(1)
            logger.debug(detail)
            detail = re.sub(r'span class=\"wl-yen\"', r'span class=\\"wl-yen\\"', detail)
            data = re.search('uccess\((.*?)\);', detail)
            if data:
                x = json.loads(data.group(1))
            else:
                await self.login.slider(self.item_page)
                return
            promo_data = jsonpath(x, '$..promoData')
            for price_tb_item in self.price_tb_items:
                price_tb_item.sales = jsonpath(x, '$..soldTotalCount')[0]
                price_tb_item.typeabbrev = self.fromStore
                if promo_data and promo_data[0]:
                    if price_tb_item.attribute_map:
                        for k, v in promo_data[0].items():
                            if k == price_tb_item.attribute_map:
                                price_tb_item.promotionprice = jsonpath(v, '$..price')[0]
                    else:
                        price_tb_item.promotionprice = jsonpath(x, '$..promoData..price')[0]
            self.completed = 3
        if rate:
            while 1:
                if self.completed == 3:
                    break
                await asyncio.sleep(1)
            logger.debug(rate)
            ms = MySql()
            for price_tb_item in self.price_tb_items:
                count = re.search('count.*?(\d+)', rate)
                if count:
                    price_tb_item.rates = count.group(1)
                price_tb_item.need_to_update = 0
                price_tb_item.save(ms)
                # print(price_tb_item)
            self.price_tb_items[0].delete(ms)
            del ms
            self.completed = 4

    @classmethod
    async def run(cls, login, browser, page, from_store):
        i_m_p_s = ItemManagePageSpider(login, browser, page, from_store)
        await i_m_p_s.do_it()


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))

    manager_page = loop.run_until_complete(l.new_page())
    odps = ItemManagePageSpider(l, b, p, manager_page, f)
    while 1:
        loop.run_until_complete(odps.do_it())
