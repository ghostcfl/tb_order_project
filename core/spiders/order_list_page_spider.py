import asyncio
import datetime
import re
import requests
from jsonpath import jsonpath

from core.spiders.base_spider import BaseSpider
from tools.logger import logger
from tools.tools_method import time_zone, store_trans, time_format, format_tb_name, format_attribute
from tools.tools_method import yesterday, write, read, delete, my_async_sleep
from settings import EARLIEST_ORDER_CREATE_TIME
from model import TBOrderItem, TBOrderDetailItem
from db.my_sql import MySql


class OrderListPageSpider(BaseSpider):
    base_url = "https://trade.taobao.com"
    url = 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8'
    data = {
        'auctionType': '0',
        'close': '0',
        'pageNum': '4',
        'pageSize': '15',
        'queryMore': 'true',
        'rxAuditFlag': '0',
        'rxElectronicAllFlag': '0',
        'rxElectronicAuditFlag': '0',
        'rxHasSendFlag': '0',
        'rxOldFlag': '0',
        'rxSendFlag': '0',
        'rxSuccessflag': '0',
        'rxWaitSendflag': '0',
        'tradeTag': '0',
        'useCheckcode': 'false',
        'useOrderInfo': 'false',
        'errorCheckcode': 'false',
        'action': 'itemlist/SoldQueryAction',
        'prePageNo': '3',
        'buyerNick': '',
        'dateBegin': '0',
        'dateEnd': '0',
        'logisticsService': '',
        'orderStatus': '',
        'queryOrder': 'desc',
        'rateStatus': '',
        'refund': '',
        'sellerNick': '',
        'tabCode': 'latest3Months'
    }

    async def intercept_request(self, req):
        logout = re.search("login.taobao.com", req.url)
        if logout:
            write(flag=self.fromStore + "headers", value="exit")
        await req.continue_()

    async def intercept_response(self, res):
        req = res.request
        if res.url == self.url:
            a = await res.json()
            if a.get("mainOrders"):
                logger.info("重置cookies成功")
                write(flag=self.fromStore + "headers", value=req.headers)
            else:
                pass
            # try:
            #     await self.parse(a['mainOrders'], a['page']['currentPage'])
            #     write(flag="headers", value=req.headers)
            # except KeyError:
            #     logger.error("KeyError")

    async def set_post_headers(self):
        await self.page.bringToFront()
        delete(self.fromStore + "headers")
        while 1:
            frames = self.page.frames
            frame = await self.login.get_nc_frame(frames)
            if not frame:
                headers = read(flag=self.fromStore + "headers")
                if not headers:
                    await self.listening(self.page)
                    try:
                        await self.page.waitForSelector(".pagination-item-1.pagination-item-active", timeout=3000)
                    except Exception as e:
                        await self.page.click(".pagination-item-1")
                    else:
                        await self.page.click(".pagination-item-2")
                elif headers == 'exit':
                    return 'exit'
                else:
                    break
            else:
                await self.login.slider(self.page)
            await asyncio.sleep(5)
        # print(headers)

    async def get_page(self, page_num):
        self.data['pageNum'] = page_num
        while 1:
            headers = read(self.fromStore + "headers")
            if headers == 'exit':
                return headers
            elif headers:
                logger.info("开始订单列表第 " + str(page_num) + " 页爬取")
                logger.info(store_trans(self.fromStore))
                r = requests.post(self.url, data=self.data, headers=headers)
                a = r.json()
                if a.get("mainOrders"):
                    await self.parse(a['mainOrders'], a['page']['currentPage'])
                    logger.info("完成订单列表第 " + str(page_num) + " 页订单爬取")
                    return self.completed
                else:
                    logger.info("headers失效，重置cookies")
                    await self.set_post_headers()
            else:
                logger.info("headers失效，重置cookies")
                await self.set_post_headers()
            await asyncio.sleep(10)

    async def parse(self, main_orders, page_num):
        # print(main_orders)
        ms = MySql()
        t = time_zone(["08:00", "23:00", "23:59"])
        a = datetime.datetime.now()
        if a < t[0]:
            eoc = EARLIEST_ORDER_CREATE_TIME
        elif t[0] < a < t[1]:
            eoc = 2
        else:
            eoc = 60

        for i in range(len(main_orders)):
            continue_code = 0  # 有些订单的商品,在未付款时就已经退掉了,所以直接直接将数据进行删除
            # 解析并保存订单到数据库
            sub_orders, tb_order_item = await self.parse_order_item(i, main_orders, ms)
            # 解析并保存订单详细商品到数据库
            await self.parse_order_detail_item(continue_code, i, main_orders, sub_orders, tb_order_item, ms)

            date = datetime.date.today()
            date_limit = (date - datetime.timedelta(eoc)).strftime("%Y-%m-%d %H:%M:%S")
            if tb_order_item.createTime < date_limit:
                logger.info("完成本轮爬取，共翻 " + str(page_num) + " 页。")
                self.completed = 2
                del ms
                return
        self.completed = 1
        del ms

    async def parse_order_item(self, i, main_orders, ms):
        tb_order_item = TBOrderItem()
        tb_order_item.orderNo = main_orders[i]["id"]
        tb_order_item.createTime = main_orders[i]['orderInfo']['createTime']
        tb_order_item.buyerName = main_orders[i]['buyer']['nick']
        flag = main_orders[i]['extra']['sellerFlag']
        tb_order_item.actualFee = main_orders[i]['payInfo']['actualFee']
        tb_order_item.deliverFee = re.search(r"\(含快递:￥(\d+\.\d+)\)", main_orders[i]['payInfo']['postType']).group(1)
        tb_order_item.detailURL = "https:" + main_orders[i]['statusInfo']['operations'][0]['url']
        tb_order_item.orderStatus = main_orders[i]['statusInfo']['text']
        tb_order_item.fromStore = self.fromStore
        url = jsonpath(main_orders, '$[{}].operations..dataUrl'.format(i))
        if flag == 1 and url:
            data_url = self.base_url + url[0]
            tb_order_item.sellerFlag = await self.get_flag_text(data_url)
        try:
            tb_order_item.isPhoneOrder = main_orders[i]['payInfo']['icons'][0]['linkTitle']
        except KeyError:
            pass
        sub_orders = main_orders[i]['subOrders']
        tb_order_item.save(ms)
        return sub_orders, tb_order_item

    @staticmethod
    async def parse_order_detail_item(continue_code, i, main_orders, sub_orders, tb_order_item, ms):
        for j in range(len(sub_orders)):
            tb_order_detail_item = TBOrderDetailItem()
            tb_order_detail_item.orderNo = main_orders[i]["id"]
            tb_order_detail_item.itemNo = j
            try:
                tb_order_detail_item.goodsCode = sub_orders[j]['itemInfo']['extra'][0]['value']
            except KeyError:
                tb_order_detail_item.goodsCode = 'error'
            tb_order_detail_item.tbName = format_tb_name(sub_orders[j]['itemInfo']['title'])
            tb_order_detail_item.unitPrice = sub_orders[j]['priceInfo']['realTotal']
            tb_order_detail_item.sellNum = sub_orders[j]['quantity']
            tb_order_detail_item.orderStatus = tb_order_item.orderStatus
            tb_order_detail_item.url = "https:" + sub_orders[j]['itemInfo']['itemUrl']
            try:
                attribute_list = sub_orders[j]['itemInfo']['skuText']
            except KeyError:
                pass
            else:
                tb_order_detail_item.goodsAttribute = format_attribute(attribute_list)

            try:
                operations = sub_orders[j]['operations']
            except KeyError:
                pass
            else:
                for x in range(len(operations)):
                    t = operations[x]['style']
                    if t in ['t12', 't16'] and operations[x]['text'] != "退运保险":
                        tb_order_detail_item.refundStatus = operations[x]['text']
                        tb_order_detail_item.isRefund = "1"
                    elif t == 't0' and operations[x]['text'] == '已取消':
                        continue_code = 1
                        delete_item = {'orderNo': tb_order_detail_item.orderNo,
                                       'itemNo': tb_order_detail_item.itemNo,
                                       'goodsCode': tb_order_detail_item.goodsCode}
                        ms = MySql()
                        is_exist = ms.get(t="tb_order_detail_spider", l=1, c=delete_item)
                        if is_exist:
                            ms.delete(t="tb_order_detail_spider", c=delete_item)
                        sql = "UPDATE tb_order_detail_spider SET itemNo=itemNo-1 " \
                              "WHERE orderNo='{}' " \
                              "AND itemNo>'{}'".format(tb_order_detail_item.orderNo,
                                                       tb_order_detail_item.itemNo)
                        ms.update(sql=sql)
                        pass
            if continue_code:
                continue
            tb_order_detail_item.save(ms)

    async def get_flag_text(self, data_url):
        cookies = await self.login.get_cookie(self.page)
        user_agent = await self.browser.userAgent()
        headers = {
            'User-Agent': user_agent,
            'Cookie': cookies
        }
        r = requests.get(url=data_url, headers=headers)
        x = r.json()
        return x.get("tip")

    @classmethod
    async def run(cls, login, browser, page, from_store):
        page_num = 1
        list_spider = OrderListPageSpider(login, browser, page, from_store)
        while 1:
            completed = await list_spider.get_page(page_num)
            if completed == 1:
                page_num += 1
            elif completed == 2:
                MySql.cls_update(t="tb_order_spider", set={"isDetaildown": 0},
                                 c={"isDetaildown": 2, "fromStore": from_store})
                MySql.cls_update(t="tb_order_spider", set={"isVerify": 0},
                                 c={"isVerify": 2, "fromStore": from_store})
                page_num = 1
            await my_async_sleep(15, random_sleep=True)


class DelayOrderUpdate(OrderListPageSpider):
    data = {
        'auctionType': '0',
        'close': '0',
        'pageNum': '1',
        'pageSize': '15',
        'queryMore': 'false',
        'rxAuditFlag': '0',
        'rxElectronicAllFlag': '0',
        'rxElectronicAuditFlag': '0',
        'rxHasSendFlag': '0',
        'rxOldFlag': '0',
        'rxSendFlag': '0',
        'rxSuccessflag': '0',
        'rxWaitSendflag': '0',
        'tradeTag': '0',
        'useCheckcode': 'false',
        'useOrderInfo': 'false',
        'errorCheckcode': 'false',
        'action': 'itemlist/SoldQueryAction',
        'prePageNo': '2',
        'buyerNick': '',
        'dateBegin': '0',
        'dateEnd': '0',
        'logisticsService': '',
        'orderStatus': '',
        'queryOrder': 'desc',
        'rateStatus': '',
        'refund': '',
        'sellerNick': '',
        'tabCode': 'latest3Months',
        'orderId': ''
    }
    data_before_3_month = {
        'action': 'itemlist/SoldHisQueryAction',
        'auctionType': '0',
        'buyerNick': '',
        'close': '0',
        'dateBegin': '0',
        'dateEnd': '0',
        # 'lastStartRow': '2343631319_9223370458391616807_580496388009557599_580496388009557599',
        'pageNum': '1',
        'pageSize': '15',
        'queryMore': 'false',
        'queryOrder': 'desc',
        'rxAuditFlag': '0',
        'rxElectronicAllFlag': '0',
        'rxElectronicAuditFlag': '0',
        'rxHasSendFlag': '0',
        'rxOldFlag': '0',
        'rxSendFlag': '0',
        'rxSuccessflag': '0',
        'rxWaitSendflag': '0',
        'tabCode': 'before3Months',
        'tradeTag': '0',
        'useCheckcode': 'false',
        'useOrderInfo': 'false',
        'errorCheckcode': 'false',
        'orderId': '804126784615181089',
        'prePageNo': '1'
    }

    async def get_page(self, page_num=None):
        while 1:
            headers = read(self.fromStore + "headers")
            if headers:
                days, order_no = self._get_order_info()
                if days > 90:
                    data = self.data_before_3_month.copy()
                else:
                    data = self.data.copy()
                if order_no:
                    logger.info("滞留订单 " + order_no + " 开始爬取")
                    data['orderId'] = order_no
                    r = requests.post(self.url, data=data, headers=headers)
                    a = r.json()
                    if a.get('mainOrders'):
                        await self.parse(a['mainOrders'], a['page']['currentPage'])
                        logger.info("滞留订单 " + order_no + " 爬取完成")
                        return self.completed
                    else:
                        logger.info("headers失效,需要重重置cookies")
                        await self.set_post_headers()
                else:
                    break
            else:
                await self.set_post_headers()
            await asyncio.sleep(15)

    def _get_order_info(self):
        today = datetime.datetime.now()
        one_day = datetime.timedelta(minutes=60)
        earlier_15_minutes = today - one_day
        updateTime = earlier_15_minutes.strftime("%Y-%m-%d %H:%M:%S")
        payTime = yesterday("18:00:00")
        sql = """      
                               SELECT 
                               tos.orderNo,createTime
                               FROM tb_order_spider tos
                               WHERE  tos.updateTime<'{}'
                               AND tos.`orderStatus` = '买家已付款' 
                               AND tos.`fromStore` = '{}' 
                               AND tos.payTime<'{}'
                               ORDER BY updateTime;
                               """.format(updateTime, self.fromStore, payTime)
        res = MySql.cls_get_dict(sql=sql)
        order_no = None
        days = 0
        if res:
            order_no = res[0]['orderNo']
            days = (today - res[0]['createTime']).days
        return days, order_no

    @classmethod
    async def run(cls, login, browser, page, from_store):
        while 1:
            delay_order_spider = DelayOrderUpdate(login, browser, page, from_store)
            await delay_order_spider.get_page()
            await my_async_sleep(15, random_sleep=True)


if __name__ == '__main__':
    from core.browser.login_tb import LoginTB
    from settings import STORE_INFO

    delete("KYheaders")
    loop = asyncio.get_event_loop()
    l, b, p, f = loop.run_until_complete(LoginTB.run(**STORE_INFO['KY']))
    dou = DelayOrderUpdate(l, b, p, f)
    tasks = [
        OrderListPageSpider.run(l, b, p, f),
        # DelayOrderUpdate.run(l, b, p, f)
    ]
    loop.run_until_complete(asyncio.wait(tasks))
