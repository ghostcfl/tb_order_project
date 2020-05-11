import requests
import re
import json
import asyncio
import subprocess
from pyppeteer import errors
from pyppeteer import launch
from pyquery import PyQuery

from tools.tools_method import write, read, time_now, store_trans, time_ago
from tools.kill_pyppeteer_temp_file import kill_temp_file
from tools.request_headers import get_user_agent
from tools.logger import logger
from settings import TEST_SERVER_DB_TEST, NOT_FREE_PROXY_API, CHROME_PATH,IP_PROXY_WHITE_LIST
from db.my_sql import MySql


class StoreItemPageSpider(object):
    base_url = "https://item.taobao.com/item.htm?id="
    _browser = None
    _page = None
    _item = []

    def __init__(self):
        self.exit_signal = 1

    @staticmethod
    async def intercept_request(req):
        if re.search(r'https://item.taobao.com/item.htm', req.url):
            await req.continue_()
        elif re.search('item.taobao.com.*?noitem.htm.*?', req.url):
            link_id = re.findall("itemid=(\d+)", req.url)[0]
            MySql.cls_update(db_setting=TEST_SERVER_DB_TEST, t="tb_master",
                             set={"flag": "XiaJia", "isUsed": 1}, c={"link_id": link_id})
            await req.abort()
        else:
            await req.abort()

    async def intercept_response(self, res):
        if re.search(r'https://item.taobao.com/item.htm', res.url):
            try:
                content = await res.text()
            except errors.NetworkError:
                logger.error("网络出错了，没有解析内容，重新请求")
                await self._goto_the_next()
            else:
                await self.parse(content)

    @staticmethod
    def _set_proxy():
        r = requests.get(NOT_FREE_PROXY_API)
        proxy = re.sub("\s+", "", r.text)  # 获得代理IP
        match = re.match("^\d+\.\d+\.\d+\.\d+:\d+$", proxy)  # 检测返回的数据是否正确

        if not match:
            # proxy = json.loads(proxy)
            ip_match = re.search("请添加白名单(\d+\.\d+\.\d+\.\d+)", proxy)
            if ip_match:
                ip = ip_match.group(1)
                requests.get(IP_PROXY_WHITE_LIST + ip)
            write("item_proxy", proxy)
            return proxy
        else:
            write("item_proxy", proxy)
            return proxy

    async def listening(self, page):
        await page.setRequestInterception(True)
        page.on('request', self.intercept_request)
        page.on('response', self.intercept_response)

    @staticmethod
    def _get_item():
        column_name = [
            "shop_id",
            "link_id",
            "description",
            "price_tb",
            "promotionprice",
            "sales",
            "rates",
        ]
        results = MySql.cls_get_dict(db_setting=TEST_SERVER_DB_TEST,
                                     t="tb_master",
                                     c={"isUsed": 0, "isMut": 1, "flag!": "XiaJia"},
                                     cn=column_name, l=["0", "1"])
        if results:
            results[0]['price_tb'] = float(results[0]['price_tb'])
            results[0]['promotionprice'] = float(results[0]['promotionprice'])
            results[0]['typeabbrev'] = store_trans(results[0]['shop_id'], 'id_2_code')
            return results[0]
        else:
            exit("已经完成所有的爬取")

    async def init_page_to_listening(self):
        # 获取存储在tools/data里的ip代理
        proxy = read('item_proxy')
        if not proxy:
            proxy = self._set_proxy()
        logger.info("当前代理IP：" + proxy)
        # 获取一个使用代理的浏览器
        self._browser = await launch(headless=True, executablePath=CHROME_PATH, args=[f'--proxy-server={proxy}'])
        # self._browser = await launch(autoClose=False, headless=False, args=[f'--proxy-server={proxy}'])
        # 获取一个浏览器的page对象
        self._page = await self._browser.newPage()
        # 设置page的请求头的user_agent
        await self._page.setUserAgent(get_user_agent())
        # 监听page的request,response事件，触发回调至intercept_response，intercept_request
        await self.listening(self._page)
        # 在数据库中获取要完成爬虫的任务
        self._item = self._get_item()
        try:
            await self._page.goto(self.base_url + self._item['link_id'])
        except errors.TimeoutError:
            pass
        except errors.PageError:
            self._set_proxy()
            return
        while self.exit_signal:
            await asyncio.sleep(50)

    async def parse(self, html):
        ms = MySql()
        self._item['SpiderDate'] = time_now()
        sku_map = re.search('skuMap.*?(\{.*)', html)
        match_xia_jia = re.search("此宝贝已下架", html)
        if match_xia_jia:
            self._item['flag'] = "XiaJia"
        if not sku_map:
            MySql.cls_update(db_setting=TEST_SERVER_DB_TEST, t="tb_master",
                             set={"isUsed": 1, "isMut": 0},
                             c={"link_id": self._item['link_id']})
            res = ms.get_dict(t="prices_tb", c={"link_id": self._item['link_id']})
            if res:
                ms.update(t="prices_tb", set=self._item, c={"link_id": self._item['link_id']})
            else:
                self._item['stockid'] = "no_match"
                self._item['SpiderDate'] = time_ago(minutes=60)
                self._item['need_to_update'] = 1
                ms.insert(t="prices_tb", d=self._item)
            logger.info(self._item)
        else:
            MySql.cls_update(db_setting=TEST_SERVER_DB_TEST, t="tb_master",
                             set={"isUsed": 1, "isMut": 1},
                             c={"link_id": self._item['link_id']})
            doc = PyQuery(html)
            items = doc("li[data-value]").items()
            logger.debug(items)
            attr_map = {}
            if items:
                for item in items:
                    attr_map[item.attr('data-value')] = item.find('span').text().replace("（", "(").replace("）", ")")
            sku_dict = json.loads(sku_map.group(1))
            count = 1
            for k, v in sku_dict.items():
                sku_result = self._item.copy()
                if self._item['promotionprice'] > 0:
                    discount = round(float(self._item['price_tb']) - float(self._item['promotionprice']), 4)
                    sku_result['promotionprice'] = round(float(v.get('price')) - float(discount), 4)
                else:
                    sku_result['promotionprice'] = 0
                sku_result['skuId'] = v.get('skuId')
                sku_result['price_tb'] = v.get('price')
                sku_result['attribute'] = "-".join([attr_map.get(r) for r in re.sub('^;|;$', "", k).split(";")])
                res = ms.get_dict(t="prices_tb", c={"skuId": sku_result['skuId']})
                if res:
                    ms.update(t="prices_tb", set=sku_result, c={"skuId": sku_result['skuId']})
                else:
                    sku_result['stockid'] = "no_match" + str(count)
                    sku_result['SpiderDate'] = time_ago(minutes=60)
                    sku_result['need_to_update'] = 1
                    ms.insert(t="prices_tb", d=sku_result)
                    count += 1
                logger.info(sku_result)
        del ms
        await self._goto_the_next()

    async def _goto_the_next(self):
        while 1:
            self._item = self._get_item()
            await self._page.setUserAgent(get_user_agent())
            try:
                await self._page.goto(self.base_url + self._item['link_id'])
            except errors.TimeoutError:
                logger.info("网页响应超时")
                self.exit_signal = 0
                return
            except errors.PageError:
                self._set_proxy()
                self.exit_signal = 0
                return
            else:
                break

    @classmethod
    def run(cls):
        kill_temp_file()
        subprocess.run("taskkill /F /IM chrome.exe", stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        s = StoreItemPageSpider()
        asyncio.get_event_loop().run_until_complete(s.init_page_to_listening())


if __name__ == '__main__':
    import time
    import schedule

    StoreItemPageSpider.run()

    schedule.every(1).seconds.do(StoreItemPageSpider.run)
    while 1:
        schedule.run_pending()
        time.sleep(1)
