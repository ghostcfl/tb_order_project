import asyncio
import re
import json
from pyppeteer import errors
from jsonpath import jsonpath

from core.spiders.base_spider import BaseSpider
from model import TBOrderItem, TBOrderDetailItem
from db.my_sql import MySql
from tools.logger import logger
from tools.tools_method import store_trans, status_format, my_async_sleep
from tools.verify import verify


class OrderDetailPageSpider(BaseSpider):
    detail_page = None

    async def get_page(self):
        await self.page.bringToFront()

        results = MySql.cls_get_dict(t="tb_order_spider",
                                     cn=["detailURL", "orderNo"],
                                     c={
                                         "isDetaildown": 0,
                                         "fromStore": self.fromStore,
                                     },
                                     o=["createTime"], om="d")
        for result in results:
            ms = MySql()
            tb_order_item = TBOrderItem(**result)
            logger.info(store_trans(self.fromStore))
            logger.info("开始订单 " + result["orderNo"] + " 详情爬取")
            while 1:
                try:
                    await self.page.goto(tb_order_item.detailURL)
                except errors.PageError:
                    return 1
                except errors.TimeoutError:
                    return 1
                else:
                    break
            try:
                await self.page.waitForSelector('#detail-panel', timeout=30000)
            except errors.TimeoutError:
                await self.login.slider(self.page)
                is_logout = re.search(r"login.taobao.com", self.page.url)
                if is_logout:
                    logger.info("登陆状态超时")
                    return 1
                continue
            content = await self.page.content()
            a = re.search(r"var data = JSON.parse\('(.*)'\);", content).group(1)
            # a = a.encode("").decode("unicode_escape")
            b = a.replace('\\\\\\"', '')
            data = b.replace('\\"', '"')
            m = json.loads(data)
            tb_order_item.actualFee = jsonpath(m, '$..actualFee.value')[0]
            tb_order_item.deliverFee = re.findall('\(快递:(\d+\.\d+)', str(m))[0]
            tb_order_item.orderStatus = status_format(jsonpath(m, '$..statusInfo.text')[0])
            if tb_order_item.orderStatus == '等待买家付款':
                tb_order_item.isDetaildown = 2
            else:
                tb_order_item.isDetaildown = 1
            tb_order_item.couponPrice = await self.get_coupon(m)

            if jsonpath(m, '$..buyMessage'):
                tb_order_item.buyerComments = jsonpath(m, '$..buyMessage')[0]
            orderNo = m['mainOrder']['id']
            order_info = m['mainOrder']['orderInfo']['lines'][1]['content']
            for i in range(len(order_info)):
                if order_info[i]['value']['name'] == '支付宝交易号:':
                    try:
                        tb_order_item.tradeNo = order_info[i]['value']['value']
                    except KeyError:
                        tb_order_item.tradeNo = None
                elif order_info[i]['value']['name'] == '创建时间:':
                    tb_order_item.createTime = order_info[i]['value']['value']
                # elif order_info[i]['value']['name'] == '发货时间:':
                #     tb_order_item = order_info[i]['value']['value']
                elif order_info[i]['value']['name'] == '付款时间:':
                    tb_order_item.payTime = order_info[i]['value']['value']
            if jsonpath(m, '$..logisticsName'):
                tb_order_item.shippingCompany = jsonpath(m, '$..logisticsName')[0]
                tb_order_item.shippingMethod = jsonpath(m, '$..shipType')[0]
                tb_order_item.shippingNo = jsonpath(m, '$..logisticsNum')[0]
            rec_info = jsonpath(m, '$..tabs..address')[0]
            tb_order_item.receiverName = re.sub(u'[\uD800-\uDBFF][\uDC00-\uDFFF]|\s', "", rec_info.split("，")[0])
            tb_order_item.receiverPhone = rec_info.split("，")[1]
            tb_order_item.receiverAddress = "".join(rec_info.split("，")[2:])
            tb_order_item.save(ms)
            sub_orders = m['mainOrder']['subOrders']
            for i in range(len(sub_orders)):
                tb_order_detail_item = TBOrderDetailItem(orderNo=orderNo, itemNo=i)
                tb_order_detail_item.unitBenefits = 0
                if sub_orders[i]['promotionInfo']:
                    for j in sub_orders[i]['promotionInfo']:
                        for x in j['content']:
                            for k, v in x.items():
                                if k == 'value':
                                    f_prom = re.match("Exercise", v)
                                    p_list = re.findall("-?\d+\.\d+", v)
                                    if p_list and not f_prom:
                                        tb_order_detail_item.unitBenefits += float(p_list.pop())
                tb_order_detail_item.save(ms)
            del ms
            await my_async_sleep(seconds=15, random_sleep=True)
        verify()

    @staticmethod
    async def get_coupon(m):
        coupon = 0
        for k, v in m['mainOrder']['payInfo'].items():
            if k == 'promotions':
                promotions = m['mainOrder']['payInfo']['promotions']
                for i in range(len(promotions)):
                    if 'prefix' and 'suffix' in promotions[i]:
                        coupon_temp = re.search(r"(\d+\.\d+)", promotions[i]['value'])
                        if coupon_temp:
                            coupon += float(coupon_temp.group(1))
        return round(coupon, 4)


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    odps = OrderDetailPageSpider(l, b, p, f)
    loop.run_until_complete(odps.get_page())
