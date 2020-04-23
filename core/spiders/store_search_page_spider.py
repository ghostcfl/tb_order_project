import requests
import time
import re
import random
import datetime
import redis
from pyquery import PyQuery
from datetime import date

from tools.logger import logger
from tools.tools_method import write, read
from db.my_sql import MySql

from settings import FREE_PROXY_API, TEST_SERVER_DB_TEST


class StoreSearchPageSpider(object):
    def __init__(self):
        self.redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
        self.redis_cli = redis.Redis(connection_pool=self.redis_pool)

    @staticmethod
    def _set_proxy():
        r = requests.get(FREE_PROXY_API)
        proxy = re.sub("\s+", "", r.text)  # 获得代理IP
        write('proxy', proxy)

    @staticmethod
    def _get_curls(shop_id):
        curls = []
        results = MySql.cls_get_dict(db_setting=TEST_SERVER_DB_TEST, t="tb_search_curl", c={'shop_id': shop_id})
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
        shop_infos = MySql.get_dict(sql=sql)
        for shop_info in shop_infos:
            yield shop_info['shop_id']

    @staticmethod
    def _get_page_num(shop_id):
        #  从数据库得到数据
        ms = MySql(db_setting=TEST_SERVER_DB_TEST)
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
            ms.update(t="tb_search_page_info", set={"used_page_nums": "0"}, c={"shop_id": shop_id})
            result = ms.get_dict(t="tb_search_page_info", c={"shop_id": shop_id})
        del ms
        #  获取已采集的数据的页码列表
        used_page_nums = [int(x) for x in result[0]['used_page_nums'].split(",")]
        total_page = result[0]['total_page']
        set_a = set([i for i in range(total_page + 1)])  # 全部页码的set集合
        set_b = set(used_page_nums)  # 已采集的数据的页码集合
        list_result = list(set_a - set_b)  # 未采集数据的页码列表
        if list_result:
            # 返回一个随机的未采集数据的页码，已采集的页码集合，和总的页码数
            return random.choice(list_result), used_page_nums, total_page
        else:
            # 如果没有未采集的页码，则表示当前店铺的所有页码全部采集完成
            return 0, 0, 0

    def _get_html(self):
        for shop_id in self._get_shop_id():
            start_time = time.time()
            curls = self._get_curls(shop_id)
            if not curls:
                continue
            curl = random.choice(curls)
            page_num, used_page_nums, total_page = self._get_page_num(shop_id)
            session = requests.Session()
            while page_num:
                url, params, cookies, headers = self.format_request_params(curl['curl'], page_num)
                while 1:
                    try:
                        proxy = read("proxy")
                        logger.info(proxy)
                        if not proxy:
                            self._set_proxy()
                        proxies = {"https": "https://{}".format(proxy)}
                        r = session.get(url=url, params=params, cookies=cookies, headers=headers, proxies=proxies,
                                        stream=True)
                    except Exception as e:
                        logger.error(str(e.args))
                        self._set_proxy()
                        continue
                    else:
                        break
                html = r.text.replace("\\", "")
                html = re.sub("jsonp\d+\(\"|\"\)", "", html)

                yield html, shop_id, curl, total_page, page_num  # 传递给parse处理
                page_num, used_page_nums, total_page = self._get_page_num(shop_id)
                # spent_time = int(time.time() - start_time)
                # used_page_nums.append(page_num)
                # used_page_nums.sort()
                # tb_search_page_info = {  # tb_search_page_info
                #     "used_page_nums": ",".join([str(x) for x in used_page_nums]),
                #     "spent_time": spent_time,
                #     "last_date": datetime.date.today()
                # }
                # MySql.cls_update(db_setting=TEST_SERVER_DB_TEST, t="tb_search_page_info", set=tb_search_page_info, c={"shop_id": shop_id})

        #     sql = "UPDATE tb_master SET flag='XiaJia',update_date='{}' WHERE shop_id='{}' AND update_date<'{}'".format(
        #         datetime.date.today(), shop_id, datetime.date.today())
        #     print(sql)
        #     mysql.update_data(db=test_server, sql=sql)
        # reports = Reports()
        # reports.report([ids for ids in self._get_shop_id()])

    def _parse(self):
        for html, shop_id, curl, total_page, page_num in self._get_html():
            doc = PyQuery(html)
            #  存在未知错误的时候，写错误的HTML写到文件中
            try:
                match = re.search("item\dline1", html).group()
            except Exception as e:
                logger.error(e)
                logger.error(shop_id + "错误页码：" + str(page_num))
                with open("error.html", 'w') as f:
                    f.write(html)
                logger.error("未知错误查看error.html文件1")
                mysql.delete_data(db=test_server, t='tb_search_curl', c={"id": curl['id']})
                return 1
            if not match:
                with open("error.html", 'w') as f:
                    f.write(html)
                logger.error(shop_id + "错误页码：" + str(page_num))
                logger.error("未知错误查看error.html文件2")
                return 1

            num = doc(".pagination span.page-info").text()
            try:
                total_page_num = re.search("\d+\/(\d+)", num).group(1)
            except Exception as e:
                pass
            else:
                if int(total_page_num) != int(total_page):
                    tspi = {  # tb_search_page_info
                        "total_page": total_page_num,
                    }
                    mysql.update_data(db=test_server, t="tb_search_page_info", set=tspi, c={"shop_id": shop_id})

            items = doc("." + match + " dl.item").items()
            for i in items:
                item = {}
                item['shop_id'] = shop_id
                item['link_id'] = i.attr('data-id')
                item['description'] = i.find("dd.detail a").text()
                item['update_date'] = date.today()
                item['flag'] = "insert"
                cprice = float(i.find("div.cprice-area span.c-price").text())
                if i.find("div.sprice-area span.s-price").text():
                    sprice = float(i.find("div.sprice-area span.s-price").text())
                else:
                    sprice = 0
                if i.find("div.sale-area span.sale-num").text():
                    item['sale_num'] = int(i.find("div.sale-area span.sale-num").text())
                else:
                    item['sale_num'] = 0
                if sprice:
                    item['price'] = sprice
                    item['promotionPrice'] = cprice
                else:
                    item['price'] = cprice
                    item['promotionPrice'] = sprice
                yield item
    #
    # def save(self):
    #     for i in self._parse():
    #         logger.info(i)
    #         res = mysql.get_data(db=test_server, t="tb_master",
    #                              c={'link_id': i['link_id']}, dict_result=True)
    #         flag = ["update"]
    #         narrative = []
    #         if res:
    #             if res[0]['price'] != i['price']:
    #                 flag.append("price")
    #                 narrative.append("更新销售价格:[{}]=>[{}]".format(res[0]['price'], i['price']))
    #             if res[0]['promotionPrice'] != i['promotionPrice']:
    #                 flag.append("promotion")
    #                 narrative.append("更新优惠售价格:[{}]=>[{}]".format(res[0]['promotionPrice'], i['promotionPrice']))
    #             if res[0]['sale_num'] != i['sale_num']:
    #                 flag.append("sale")
    #                 narrative.append("更新销量:[{}]=>[{}]".format(res[0]['sale_num'], i['sale_num']))
    #             if res[0]['flag'] == 'XiaJia':
    #                 flag.append("ShangJia")
    #                 narrative.append("下架商品重新上架")
    #             i['flag'] = "_".join(flag)
    #             i['narrative'] = ";".join(narrative)
    #             mysql.update_data(db=test_server, t='tb_master', set=i, c={"link_id": i['link_id']})
    #         else:
    #             i['flag'] = 'insert'
    #             mysql.insert_data(db=test_server, t="tb_master", d=i)
