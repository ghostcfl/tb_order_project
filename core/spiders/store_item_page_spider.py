import requests
import re
import json
import time
import asyncio
import shutil
from pyppeteer.launcher import CHROME_PROFILE_PATH
from pyppeteer import launch
from pyquery import PyQuery

from tools.tools_method import write, read, delete, time_now
from tools.request_headers import get_request_headers
from tools.logger import logger
from settings import NOT_FREE_PROXY_API, FREE_PROXY_API, TEST_SERVER_DB_TEST as test_db
from db.my_sql import MySql


class StoreItemPageSpider(object):
    base_url = "https://item.taobao.com/item.htm?id="

    def __init__(self):
        pass

    @staticmethod
    def _set_proxy():
        r = requests.get(FREE_PROXY_API)
        proxy = re.sub("\s+", "", r.text)  # 获得代理IP
        write("item_proxy", proxy)

    async def get_item(self):
        # b = await launch(args=['--proxy-server={}'.format("58.218.92.170:9089")])
        b = await launch()
        p = await b.newPage()
        column_name = [
            "shop_id",
            "link_id",
            "description",
            "price_tb",
            "promotionprice",
            "sales",
            "rates",
        ]
        results = MySql.cls_get_dict(db_setting=test_db, t="tb_master", c={"isUsed": 0}, cn=column_name)

        if results:
            for result in results:
                result['price_tb'] = float(result['price_tb'])
                result['promotionprice'] = float(result['promotionprice'])
                url = self.base_url + result['link_id']
                await p.goto(url, timeout=10000)
                content = await p.content()
                yield content, result
                # while 1:
                #     proxy = read("item_proxy")
                #     logger.info(proxy)
                #     if not proxy:
                #         self._set_proxy()
                #         proxy = read("item_proxy")
                #     proxies = {"https": "https://{}".format(proxy)}
                #     headers = get_request_headers()
                #     try:
                #         r = requests.get(url, headers=headers, proxies=proxies)
                #     except Exception as e:
                #         self._set_proxy()
                #         continue
                #     else:
                #         break
                # yield r.text, result
                time.sleep(60)

    async def parse(self):
        ms = MySql()
        async for html, result in self.get_item():
            result['SpiderDate'] = time_now()
            sku_map = re.search('skuMap.*?(\{.*)', html)
            if not sku_map:
                print(result)
                # MySql.cls_update(db_setting=test_db, t="tb_master", set={"isUsed": 1}, c={"link_id": result['link_id']})
                # res = ms.get_dict(t="prices_tb", c={"link_id": result['link_id']})
                # if res:
                #     ms.update(t="prices_tb", set=result, c={"link_id": result['link_id']})
                # else:
                #     result['stockid'] = "no_match"
                #     ms.insert(t="prices_tb", d=result)
            else:
                doc = PyQuery(html)
                items = doc("li[data-value]").items()
                logger.debug(items)
                attr_map = {}
                if items:
                    for item in items:
                        attr_map[item.attr('data-value')] = item.find('span').text().replace("（", "(").replace("）", ")")
                sku_dict = json.loads(sku_map.group(1))
                for k, v in sku_dict.items():
                    sku_result = result.copy()
                    if result['promotionprice'] > 0:
                        discount = round(float(result['price_tb']) - float(result['promotionprice']), 4)
                        sku_result['promotionprice'] = round(float(v.get('price')) - float(discount), 4)
                    else:
                        sku_result['promotionprice'] = 0
                    sku_result['skuId'] = v.get('skuId')
                    sku_result['price_tb'] = v.get('price')
                    sku_result['attribute'] = "-".join([attr_map.get(r) for r in re.sub('^;|;$', "", k).split(";")])
                    print(sku_result)


if __name__ == '__main__':
    s = StoreItemPageSpider()
    asyncio.get_event_loop().run_until_complete(s.parse())
