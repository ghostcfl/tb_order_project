import datetime
import asyncio

from tools.tools_method import yesterday, my_async_sleep
from tools.logger import logger
from db.my_sql import MySql
from core.spiders.order_list_page_spider import OrderListPageSpider


class DelayOrderUpdate(OrderListPageSpider):
    async def get_page(self, page_num=None):
        await self.page.bringToFront()

        if self.page.url != "https://trade.taobao.com/trade/itemlist/list_sold_items.htm":
            await self.page.goto("https://trade.taobao.com/trade/itemlist/list_sold_items.htm")
        while 1:
            self.completed = 0
            days, order_no = self._get_order_info()
            if days > 90:
                pass
            else:
                await self.page.focus("#bizOrderId")
                for _ in range(20):
                    await self.page.keyboard.press("Delete")
                    await self.page.keyboard.press("Backspace")
                if order_no:
                    logger.info("滞留订单爬虫 " + str(order_no) + " 开始")
                    await self.page.type('#bizOrderId', order_no, {'delay': self.login.input_time_random()})
                    await self.listening(self.page)
                    await self.page.click(".button-mod__primary___17-Uv")
                    await self.page.waitForResponse(self.url)
                    while self.captcha:
                        t = await self.login.slider(self.page)
                        if t:
                            return t
                        # await self.page.waitForResponse(self.url)
                    while not self.completed:
                        await asyncio.sleep(2)
                    logger.info("滞留订单爬虫 " + str(order_no) + " 完成")
                    await my_async_sleep(15, True)
                else:
                    logger.info("没有滞留订单可以更新")
                    break
        return 0
        # while 1:
        #     headers = read(self.fromStore + "headers")
        #     if headers:
        #         days, order_no = self._get_order_info()
        #         if days > 90:
        #             data = self.data_before_3_month.copy()
        #         else:
        #             data = self.data.copy()
        #         if order_no:
        #             logger.info("滞留订单 " + order_no + " 开始爬取")
        #             data['orderId'] = order_no
        #             r = requests.post(self.url, data=data, headers=headers)
        #             a = r.json()
        #             if a.get('mainOrders'):
        #                 await self.parse(a['mainOrders'], a['page']['currentPage'])
        #                 logger.info("滞留订单 " + order_no + " 爬取完成")
        #                 return self.completed
        #             else:
        #                 logger.info("headers失效,需要重重置cookies")
        #                 await self.set_post_headers()
        #         else:
        #             break
        #     else:
        #         await self.set_post_headers()
        #     await asyncio.sleep(15)

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

    # @classmethod
    # async def run(cls, login, browser, page, from_store):
    #     while 1:
    #         delay_order_spider = DelayOrderUpdate(login, browser, page, from_store)
    #         await delay_order_spider.get_page()
    #         await my_async_sleep(15, random_sleep=True)


if __name__ == '__main__':
    from settings import STORE_INFO
    from core.browser.login_tb import LoginTB

    loop = asyncio.get_event_loop()
    login, browser, page, from_store = loop.run_until_complete(LoginTB.run(**STORE_INFO["YJ"]))

    delay_order_page = loop.run_until_complete(login.new_page())
    delay_order_spider = DelayOrderUpdate(login, browser, delay_order_page, from_store)

    loop.run_until_complete(delay_order_spider.get_page())
