from db.my_sql import MySql
from settings import TEST_SERVER_DB_TEST
from tools.mail import mail
from settings import MAIL_RECEIVERS
from settings import STORE_INFO


class Reports(object):
    translate_dictionary = {
        "insert": "新增",
        "price": "更新销售价格",
        "promotion": "更新优惠价格",
        "sale": "更新销量",
        "XiaJia": "下架商品",
        "ShangJia": "重新上架商品",
    }

    @staticmethod
    def init_receivers():
        receivers = MAIL_RECEIVERS.copy()
        receivers.append("szjavali@qq.com")
        receivers.append("104684637@qq.com")
        receivers.append("myzhiheng@163.com")
        mail_receivers_ky = receivers.copy()
        mail_receivers_yk = receivers.copy()
        mail_receivers_yj = receivers.copy()
        mail_receivers_tb = receivers.copy()
        mail_receivers_ky.append(STORE_INFO['KY']['manager_mail'])
        mail_receivers_yk.append(STORE_INFO['YK']['manager_mail'])
        mail_receivers_yj.append(STORE_INFO['YJ']['manager_mail'])
        mail_receivers_tb.append(STORE_INFO['TB']['manager_mail'])
        mail_container = {
            "KY": {
                "receivers": mail_receivers_ky,
                "mail_content": "",
                "title": "开源 | 育松 | 店铺搜索页面爬虫报告"
            },
            "YJ": {
                "receivers": mail_receivers_yj,
                "mail_content": "",
                "title": "玉佳 | 信泰微 | 店铺搜索页面爬虫报告"
            },
            "YK": {
                "receivers": mail_receivers_yk,
                "mail_content": "",
                "title": "玉佳企业店 | 店铺搜索页面爬虫报告"
            },
            "TB": {
                "receivers": mail_receivers_tb,
                "mail_content": "",
                "title": "赛宝 | 优信 | 店铺搜索页面爬虫报告"
            },
        }
        return mail_container

    def get(self, shop_ids):
        mail_container = self.init_receivers()
        ms = MySql(db_setting=TEST_SERVER_DB_TEST)

        for shop_id in shop_ids:
            shop_name = MySql.cls_get_one(sql="SELECT shopname FROM shop_info WHERE shop_id={}".format(shop_id))
            flag_report_groups = []
            # sql = "SELECT COUNT(id) AS nums FROM tb_master where shop_id='{}' and update_date<'{}'".format(shop_id,
            #                                                                                                datetime.date.today())
            # nums = mysql.get_data(db=test_server, sql=sql, return_one=True)
            # if int(nums) > 0:
            #     flag_report_groups.append("下架商品{}条".format(nums))
            # del sql
            # del nums
            for flag in self.translate_dictionary.keys():
                sql = "SELECT COUNT(id) AS nums FROM tb_master WHERE flag LIKE '%%{}%%' AND shop_id='{}'".format(flag,
                                                                                                                 shop_id)
                nums = ms.get_one(db=TEST_SERVER_DB_TEST, sql=sql)
                if int(nums) > 0:
                    flag_report_groups.append("{}{}条".format(self.translate_dictionary[flag], nums))

            if flag_report_groups:
                result = ms.get_dict(t="tb_search_page_info", c={"shop_id": shop_id})
                flag_report_groups.append("总计爬取{}页".format(result[0]['total_page']))
                flag_report_groups.append(
                    "总计花费{}分{}秒".format(int(result[0]['spent_time'] / 60), int(result[0]['spent_time'] % 60)))
                flag_report_groups.reverse()
                flag_report_groups.append(shop_name)
                flag_report_groups.reverse()

                if shop_id in ["115443253", "33817767"]:
                    mail_container["KY"]['mail_content'] += "|".join(flag_report_groups) + "\n"
                    mail_container["KY"]['mail_content'] += self.insert_link(shop_id, ms)
                elif shop_id in ["34933991", "131282813"]:
                    mail_container["TB"]['mail_content'] += "|".join(flag_report_groups) + "\n"
                    mail_container["TB"]['mail_content'] += self.insert_link(shop_id, ms)
                elif shop_id in ["68559944", "60299985"]:
                    mail_container["YJ"]['mail_content'] += "|".join(flag_report_groups) + "\n"
                    mail_container["YJ"]['mail_content'] += self.insert_link(shop_id, ms)
                else:
                    mail_container["YK"]['mail_content'] += "|".join(flag_report_groups) + "\n"
                    mail_container["YK"]['mail_content'] += self.insert_link(shop_id, ms)
        return mail_container

    def insert_link(self, shop_id, ms):
        sql = "SELECT link_id FROM tb_master WHERE flag ='{}' AND shop_id='{}'".format('insert', shop_id)
        results = ms.get_dict(sql=sql)
        if results:
            result = "新增链接：\n"
            for r in results:
                result += f"https://item.taobao.com/item.htm?id={r['link_id']}\n"
                # print(r['link_id'])
            return result
        else:
            return ""

    def report(self, shop_ids):
        r = self.get(shop_ids=shop_ids)
        for k, v in r.items():
            mail(v.get("title"), v.get("mail_content"), v.get("receivers"))
            # print(v.get("mail_content"))
    # mail("店铺搜索页爬虫报告", r, MAIL_RECEIVERS)
    # [Format._write(shop_id=shop_id, flag="mail", value=1) for shop_id in shop_ids]


if __name__ == '__main__':
    report = Reports()
    ids = ["115443253", "33817767", "34933991", "131282813", "68559944", "60299985", "197444037"]
    report.report(ids)
    #
    # ms = MySql(db_setting=TEST_SERVER_DB_TEST)
    # report.insert_link("115443253", ms)
