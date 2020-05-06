import re
import requests
import datetime
import random
import time
from pyquery import PyQuery

from settings import NOT_FREE_PROXY_API, TEST_SERVER_DB_TEST as test_db, IP_PROXY_WHITE_LIST
from tools.tools_method import write, read, delete
from tools.reports import Reports
from tools.mail import mail
from db.my_sql import MySql
from tools.logger import logger
from model import TBMasterItem
from settings import MAIL_RECEIVERS


class StoreSearchPageSpider(object):
    proxies = None

    def __init__(self):
        pass

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
            write("proxy", proxy)
            return proxy
        else:
            write("proxy", proxy)
            return proxy

    @staticmethod
    def _get_curls(shop_id):
        curls = []
        results = MySql.cls_get_dict(db_setting=test_db, t="tb_search_curl", c={'shop_id': shop_id})
        for res in results:
            curls.append(res)
        return curls

    @staticmethod
    def format_request_params(curl, page_num=2):
        curl = re.sub("\"|\^", "", curl)
        a = curl.split(" -H ")
        params = {}
        cookies = {}
        headers = {}
        url = ""
        for b in a:
            if re.match("curl", b):
                c = b.split(" ")[-1]
                url = c.split("?", 1)[0]
                d = c.split("?", 1)[1].split("&")
                for e in d:
                    f = e.split("=", 1)
                    params[f[0]] = f[1]
            elif re.match("Cookie", b, re.I):
                g = b.split(": ")[-1]
                h = g.split("; ")
                for i in h:
                    j = i.split("=", 1)
                    cookies[j[0]] = j[1]
            else:
                k = b.split(": ", 1)
                headers[k[0]] = k[1]
        params['orderType'] = "hotsell_desc"
        if page_num > 1:
            headers['Referer'] = re.sub("i\/asynS", "s", url) + "?" + "&".join(
                [k + "=" + str(v) for k, v in params.items()]) + "&pageNo=" + str(page_num)
            params['pageNo'] = str(page_num)
        return url, params, cookies, headers

    @staticmethod
    def _get_shop_id():
        sql = "select shop_id from shop_info where shop_id!='88888888'"  # 获取所有的店铺ID
        shop_infos = MySql.cls_get_dict(sql=sql)
        for shop_info in shop_infos:
            yield shop_info['shop_id']

    @staticmethod
    def _get_page_num(shop_id):
        #  从数据库得到数据
        ms = MySql(db_setting=test_db)
        result = ms.get_dict(t="tb_search_page_info", c={"shop_id": shop_id})
        if not result:
            #  没有数据就新增一个默认数据
            d = {
                "shop_id": shop_id,
                "total_page": 20,
                "used_page_nums": "0"
            }
            #  插入数据后再重新获取
            ms.insert(t="tb_search_page_info", d=d)
            result = ms.get_dict(t="tb_search_page_info", c={"shop_id": shop_id})

        if result[0]['last_date'] < datetime.date.today():
            ms.update(t="tb_search_page_info", set={"used_page_nums": "0", "spent_time": 0}, c={"shop_id": shop_id})
            result = ms.get_dict(t="tb_search_page_info", c={"shop_id": shop_id})
        #  获取已采集的数据的页码列表
        used_page_nums = [int(x) for x in result[0]['used_page_nums'].split(",")]
        total_page = result[0]['total_page']
        set_a = set([i for i in range(total_page + 1)])  # 全部页码的set集合
        set_b = set(used_page_nums)  # 已采集的数据的页码集合
        list_result = list(set_a - set_b)  # 未采集数据的页码列表
        if list_result:
            # 返回一个随机的未采集数据的页码，已采集的页码集合，和总的页码数
            return random.choice(list_result), used_page_nums, total_page, result[0]['spent_time']
        else:
            # 如果没有未采集的页码，则表示当前店铺的所有页码全部采集完成
            return 0, 0, 0, 0

    def _get_html(self):
        for shop_id in self._get_shop_id():
            start_time = time.time()
            curls = self._get_curls(shop_id)
            if not curls:
                continue
            curl = random.choice(curls)
            page_num, used_page_nums, total_page, sp_time = self._get_page_num(shop_id)
            session = requests.Session()
            while page_num:
                delete(flag='tspi')
                url, params, cookies, headers = self.format_request_params(curl['curl'], page_num)
                while 1:
                    try:
                        proxy = read("proxy")
                        logger.info(proxy)
                        if not proxy:
                            self._set_proxy()
                        proxies = {"https": "https://{}".format(proxy)}
                        r = session.get(url=url, params=params, cookies=cookies, headers=headers, proxies=proxies,
                                        stream=True, timeout=30)
                    except Exception as e:
                        logger.error(str(e))
                        self._set_proxy()
                        session = requests.Session()
                        continue
                    else:
                        break
                html = r.text.replace("\\", "")
                html = re.sub("jsonp\d+\(\"|\"\)", "", html)
                yield html, shop_id, used_page_nums, total_page, page_num
                spent_time = int(time.time() - start_time) + sp_time
                tspi = read(flag="tspi")
                if tspi:
                    tspi['spent_time'] = spent_time
                    MySql.cls_update(db_setting=test_db, t="tb_search_page_info", set=tspi, c={"shop_id": shop_id})
                page_num, used_page_nums, total_page, sp_time = self._get_page_num(shop_id)
            sql = "UPDATE tb_master SET flag='XiaJia',update_date='{}' WHERE shop_id='{}' AND update_date<'{}'".format(
                datetime.date.today(), shop_id, datetime.date.today())
            MySql.cls_update(db_setting=test_db, sql=sql)
        reports = Reports()
        reports.report([ids for ids in self._get_shop_id()])

    def parse(self):
        for html, shop_id, used_page_nums, total_page, page_num in self._get_html():
            doc = PyQuery(html)
            match = re.search("item\dline1", html)
            if not match:
                MySql.cls_delete(db_setting=test_db, t='tb_search_curl', c={"shop_id": shop_id})
                mail("店铺搜索页爬虫出错", shop_id + "错误页码：" + str(page_num) + "\n" + html, MAIL_RECEIVERS)
                exit("店铺搜索页爬虫出错")

            used_page_nums.append(page_num)
            used_page_nums.sort()
            tspi = {  # tb_search_page_info
                "used_page_nums": ",".join([str(x) for x in used_page_nums]),
                "last_date": datetime.date.today()
            }
            write(flag="tspi", value=tspi)

            num = doc(".pagination span.page-info").text()
            try:
                total_page_num = re.search("\d+\/(\d+)", num).group(1)
            except Exception as e:
                logger.error(str(e))
            else:
                if int(total_page_num) != int(total_page):
                    tspi['total_page'] = total_page_num
                    write(flag="tspi", value=tspi)

            items = doc("." + match.group() + " dl.item").items()
            ms = MySql(db_setting=test_db)
            for i in items:
                tb_master_item = TBMasterItem()
                tb_master_item.shop_id = shop_id
                tb_master_item.link_id = i.attr('data-id')
                tb_master_item.description = i.find("dd.detail a").text()
                cprice = float(i.find("div.cprice-area span.c-price").text())
                if i.find("div.sprice-area span.s-price").text():
                    sprice = float(i.find("div.sprice-area span.s-price").text())
                else:
                    sprice = 0
                if i.find("div.sale-area span.sale-num").text():
                    tb_master_item.sales = int(i.find("div.sale-area span.sale-num").text())
                if i.find("dd.rates a span").text():
                    tb_master_item.rates = int(i.find("dd.rates a span").text())
                if sprice:
                    tb_master_item.price_tb = sprice
                    tb_master_item.promotionprice = cprice
                else:
                    tb_master_item.price_tb = cprice
                    tb_master_item.promotionprice = sprice

                print(tb_master_item)
                tb_master_item.save(ms)
            del ms

    @classmethod
    def run(cls):
        s = StoreSearchPageSpider()
        s.parse()


if __name__ == '__main__':
    StoreSearchPageSpider.run()
