import re
import json
import asyncio
from pyquery import PyQuery
from jsonpath import jsonpath

from settings import FAST_EDIT_BTN
from core.spiders.base_spider import BaseSpider
from tools.logger import logger
from model import PriceTBItem
from db.my_sql import MySql


class ItemManagePageSpider(BaseSpider):
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

    async def do_it(self, link_id):
        base = "https://item.manager.taobao.com/taobao/manager/render.htm"
        pages = await self.browser.pages()
        for page in pages:
            if re.search(r"render.htm", page.url):
                self.manager_page = page
                break
        if not self.manager_page:
            self.manager_page = await self.login.new_page()

        await self.manager_page.bringToFront()

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
            await self.listening(self.manager_page)
            try:
                await self.manager_page.waitForSelector(FAST_EDIT_BTN)
                await self.manager_page.click(FAST_EDIT_BTN)
                restart = await self.login.slider(self.manager_page)
                if restart:
                    exit("滑块验证码失败，退出")
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
        while 1:
            try:
                await self.listening(self.item_page)
                await self.item_page.goto(base + "?id=" + link_id)
                restart = await self.login.slider(self.manager_page)
                if restart:
                    exit("滑块验证码失败，退出")
            except Exception as e:
                logger.error(str(e) + "item_page_error")
                restart = await self.login.slider(self.manager_page)
                if restart:
                    exit("滑块验证码失败，退出")
            else:
                break
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
            for price_tb_item in self.price_tb_items:
                price_tb_item.sales = jsonpath(x, '$..soldTotalCount')[0]
                price_tb_item.typeabbrev = self.fromStore
                if promo_data and promo_data[0]:
                    for k, v in promo_data[0].items():
                        if k == price_tb_item.attribute_map:
                            price_tb_item.promotionprice = jsonpath(v, '$..price')[0]
            self.completed = 2
        if rate:
            while 1:
                if self.completed == 2:
                    break
                await asyncio.sleep(1)
            logger.debug(rate)
            ms = MySql()
            for price_tb_item in self.price_tb_items:
                count = re.search('count.*?(\d+)', rate)
                if count:
                    price_tb_item.rates = count.group(1)
                price_tb_item.save(ms)
            self.completed = 3

    @classmethod
    async def run(cls, login, browser, page, from_store, link_id):
        i_m_p_s = ItemManagePageSpider(login, browser, page, from_store)
        await i_m_p_s.do_it(link_id)


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    odps = ItemManagePageSpider(l, b, p, f)
    loop.run_until_complete(odps.do_it('603692235487'))
