from db.my_sql import MySql
from tools.mail import mail
from tools.tools_method import store_trans, time_zone
from tools.logger import logger


def verify():
    l_orderNo = []
    column_name = ['orderNo', 'deliverFee', 'actualFee', 'couponPrice', 'fromStore', 'orderStatus']
    condition = {'isVerify': '0', 'isDetaildown': '1'}
    # kwargs = {'isVerify': '2', 'isDetaildown': '1'}
    ms = MySql()
    result = ms.get(t="tb_order_spider", cn=column_name, c=condition)
    if result:
        for i in result:
            total = 0
            orderNo = i[0]
            deliverFee = i[1]
            actualFee = i[2]
            couponPrice = i[3]
            fromStore = i[4]
            column_name = ['unitPrice', 'sellNum', 'unitBenefits']
            condition = {'orderNo': orderNo}
            result2 = ms.get(t="tb_order_detail_spider", cn=column_name, c=condition)
            for j in result2:
                unitPrice = j[0]
                sellNum = j[1]
                unitBenefits = j[2]
                total = total + unitPrice * sellNum - unitBenefits
            a = round(total, 3) + deliverFee - actualFee - couponPrice
            if abs(a) > 0.0001 and i[5] != '交易关闭':
                list_tmp = []
                list_tmp.append(str(round(total, 2)))
                list_tmp.append(str(deliverFee))
                list_tmp.append(str(actualFee))
                list_tmp.append(str(couponPrice))
                list_tmp.append(str(a))
                list_tmp.append(store_trans(fromStore))
                list_tmp.append(orderNo)
                l_orderNo.append("|".join(list_tmp))
                ms.update(t="tb_order_spider", set={'isVerify': 2, 'isDetaildown': 0}, c={'orderNo': orderNo})
            else:
                ms.update(t="tb_order_spider", set={'isVerify': 1}, c={'orderNo': orderNo})
                # print('没有异常数据，验证完成！')
                pass
    if l_orderNo:
        s = "\n".join(l_orderNo)
        # print(s)
        mail("数据异常报告", s, ["946930866@qq.com"])
    # taobao_check()


def taobao_check():
    from settings import TEST_SERVER2 as ts
    ms = MySql()
    test_server = ts.copy()
    test_server['db'] = 'test'
    ms_test = MySql(**test_server)
    today = time_zone(["00:00"])[0]
    # 查询表erp导入脚本标记为8并且已被爬虫爬取到的数据
    sql = """
    SELECT t.OrderNo as orderNo,t.StocksCatTotal,t.RealPay,t.StoreName,t.CreatDate
    FROM taobaoorders AS t JOIN tb_order_spider AS s
    ON t.OrderNo = s.orderNo
    WHERE t.Flag=8 AND s.isVerify=1;
    """
    res = ms.get(sql=sql, dict_result=True)

    if res:
        pass
    else:
        logger.info("没有数据")
        return

    for r in res:
        # 获取今日报告的数据，如果没有就初始一个0的数据

        sql = """
        select * from spider_reports
        where reports_date='%s'
        and reports_type = '优惠差额报告' and store_name='%s'
        """ % (today, r['StoreName'])

        report = ms_test.get(db=test_server, dict_result=True, sql=sql)

        if report:
            fix_total = report[0]['price']
            count = report[0]['count']
            flag = 'update'
        else:
            fix_total = 0
            count = 0
            flag = 'create'

        out_list = []
        itemNum = ms.get(t="tb_order_detail_spider", cn=["count(itemNo)"], c={"orderNo": r["orderNo"]},
                         dict_result=True)
        if itemNum:
            actualFee = ms.get(t="tb_order_spider", cn=["actualFee"], c={"orderNo": r["orderNo"]},
                               dict_result=True)
            if r['StocksCatTotal'] != itemNum[0]['count(itemNo)']:
                out_list.append("宝贝种类数量不一致！导入了%d个宝贝种类，爬取了%d个宝贝种类"
                                % (r['StocksCatTotal'], itemNum[0]['count(itemNo)']))
            elif actualFee:
                if r['RealPay'] - actualFee[0]['actualFee'] != 0:
                    out_list.append("订单总价不一致，爬虫修正（%.2f ==> %.2f)" % (r['RealPay'], actualFee[0]['actualFee']))
                    ms.update(t="taobaoorders",
                              set={'RealPay': actualFee[0]['actualFee']},
                              c={'OrderNo': r['orderNo']})
                else:
                    out_list.append("1")
            ms.update(t="taobaoorders",
                      set={'RealPay': actualFee[0]['actualFee'], 'Flag': 0,
                           'spiderFlag': "and".join(out_list)},
                      c={'OrderNo': r['orderNo']})
        res_detail = ms.get(t="taobaoordersdetail", c={"OrderNo": r["orderNo"]}, dict_result=True)
        if res_detail:
            pass
        else:
            continue
        for rd in res_detail:
            spider_detail = ms.get(t="tb_order_detail_spider",
                                   c={"orderNo": r["orderNo"], "goodsCode": rd["ShopCode"],
                                      "itemNo": rd["LineNo"]},
                                   dict_result=True)
            if len(spider_detail) == 1:

                for sd in spider_detail:
                    price = (sd['unitPrice'] * sd['sellNum'] - sd['unitBenefits']) / sd['sellNum']
                    fix_total += rd['Price'] - price
                    count += 1
                    if price - rd['Price'] != 0:
                        out_str = "%.2f ==> %.4f" % (rd['Price'], price)
                    else:
                        out_str = '1'
                    ms.update(t="taobaoordersdetail",
                              set={'Price': round(price, 4), 'spiderFlag': out_str,
                                   'YouHui': sd['unitBenefits']},
                              c={'Id': rd['Id']})
            else:
                logger.error("订单报错：" + r["orderNo"])
        if flag == 'create':
            ms_test.insert(t="spider_reports",
                           d={'reports_type': '优惠差额报告',
                              'reports_date': today,
                              'count': count,
                              'price': round(fix_total, 2),
                              'store_name': r['StoreName'], },
                           )
        elif flag == 'update':
            ms_test.update(t="spider_reports",
                           set={'count': count, 'price': round(fix_total, 2), },
                           c={'reports_type': '优惠差额报告', 'reports_date': today, 'store_name': r['StoreName'], },
                           )


if __name__ == '__main__':
    verify()
