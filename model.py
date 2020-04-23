import abc
from datetime import date

from tools.tools_method import time_now, time_ago


class BaseItem(abc.ABC):
    def __str__(self):
        return str(self.__dict__)

    def _pop_null_value(self):
        data = self.__dict__.copy()
        for key in list(data.keys()):
            if data.get(key) is None:
                data.pop(key)
        return data

    @abc.abstractmethod
    def _condition(self):
        pass

    @staticmethod
    def _table_name():
        pass


class TBOrderItem(BaseItem):
    def __init__(self, **kwargs):
        self.orderNo = kwargs.get('orderNo')
        self.createTime = kwargs.get('createTime')
        self.tradeNo = kwargs.get('tradeNo')
        self.buyerName = kwargs.get('buyerName')
        self.sellerFlag = kwargs.get('sellerFlag')
        self.isPhoneOrder = kwargs.get('isPhoneOrder')
        self.actualFee = kwargs.get('actualFee')
        self.deliverFee = kwargs.get('deliverFee')
        self.detailURL = kwargs.get('detailURL')
        self.orderStatus = kwargs.get('orderStatus')
        self.couponPrice = kwargs.get('couponPrice')
        self.payTime = kwargs.get('payTime')
        self.receiverName = kwargs.get('receiverName')
        self.receiverPhone = kwargs.get('receiverPhone')
        self.receiverAddress = kwargs.get('receiverAddress')
        self.shippingMethod = kwargs.get('shippingMethod')
        self.shippingCompany = kwargs.get('shippingCompany')
        self.shippingNo = kwargs.get('shippingNo')
        self.buyerComments = kwargs.get('buyerComments')
        self.fromStore = kwargs.get('fromStore')
        self.updateTime = kwargs.get('updateTime', time_now())
        self.isDetaildown = kwargs.get('isDetaildown')
        self.isVerify = kwargs.get('isVerify')

    def _condition(self):
        condition = {"orderNo": self.orderNo}
        return condition

    @staticmethod
    def _table_name():
        return "tb_order_spider"

    def save(self, ms):
        status = ["卖家已发货", "交易成功"]
        data = self._pop_null_value()
        condition = self._condition()
        res = ms.get_dict(t=self._table_name(), c=condition)
        if res:
            if data['orderStatus'] in status and res[0]['orderStatus'] == "买家已付款":
                data['isDetaildown'] = 0
            ms.update(t=self._table_name(), set=data, c=condition)
            # ms.print_update_sql(t=self._table_name(), set=data, c=condition)
        else:
            ms.insert(t=self._table_name(), d=data)
            # ms.print_insert_sql(t=self._table_name(), d=data)


class TBOrderDetailItem(BaseItem):
    def __init__(self, **kwargs):
        self.orderNo = kwargs.get('orderNo')
        self.itemNo = kwargs.get('itemNo')
        self.goodsCode = kwargs.get('goodsCode')
        self.goodsAttribute = kwargs.get('goodsAttribute')
        self.tbName = kwargs.get('tbName')
        self.url = kwargs.get('url')
        self.unitPrice = kwargs.get('unitPrice')
        self.orderStatus = kwargs.get('orderStatus')
        self.sellNum = kwargs.get('sellNum')
        self.unitBenefits = kwargs.get('unitBenefits')
        self.isRefund = kwargs.get('isRefund', 0)
        self.refundStatus = kwargs.get('refundStatus', "")

    def _condition(self):
        condition = {"orderNo": self.orderNo, "itemNo": self.itemNo}
        return condition

    @staticmethod
    def _table_name():
        return "tb_order_detail_spider"

    def save(self, ms):
        data = self._pop_null_value()
        condition = self._condition()
        res = ms.get(t=self._table_name(), c=condition)
        if res:
            if data.get("goodsCode"):
                data.pop("goodsCode")
            ms.update(t=self._table_name(), set=data, c=condition)
            # ms.print_update_sql(t=self._table_name(), set=data, c=condition)
        else:
            ms.insert(t=self._table_name(), d=data)
            # ms.print_insert_sql(t=self._table_name(), d=data)


class PriceTBItem(BaseItem):
    def __init__(self, **kwargs):
        self.stockid = kwargs.get('stockid')
        self.link_id = kwargs.get('link_id')
        self.attribute = kwargs.get('attribute')
        self.skuId = kwargs.get('skuId')
        self.shop_id = kwargs.get('shop_id')
        self.typeabbrev = kwargs.get('typeabbrev')
        self.price_tb = kwargs.get('price_tb')
        self.price_erp = kwargs.get('price_erp', 0)
        self.currabrev = kwargs.get('currabrev', "CNY")
        self.operator = kwargs.get('operator', '爬虫维护')
        self.last_time = kwargs.get('last_time')
        self.flag = kwargs.get('flag')
        self.freight = kwargs.get('freight')
        self.ratio = kwargs.get('ratio')
        self.promotionprice = kwargs.get('promotionprice')
        self.sales = kwargs.get('sales')
        self.rates = kwargs.get('rates')
        self.package_number = kwargs.get('package_number')
        self.description = kwargs.get('description')
        self.SpiderDate = kwargs.get('SpiderDate', time_now())
        self.need_to_update = kwargs.get('need_to_update')
        self.attribute_map = kwargs.get('attribute_map')

    @staticmethod
    def _table_name():
        return "prices_tb"

    def _condition(self):
        condition = {"stockid": self.stockid, "link_id": self.link_id, "shop_id": self.shop_id}
        return condition

    def save(self, ms):
        data = self._pop_null_value()
        if data['stockid'] == '':
            return 1
        if data.get('attribute_map'):
            data.pop('attribute_map')
        condition = self._condition()
        res = ms.get(t=self._table_name(), c=condition)
        if res:
            data['flag'] = 'update'
            data.pop('operator')
            ms.update(t=self._table_name(), set=data, c=condition)
            # ms.print_update_sql(t=self._table_name(), set=data, c=condition)
        else:
            data['flag'] = 'add'
            data['last_time'] = time_now()
            data['package_number'] = 1
            if data.get("need_to_update") is None:
                data['need_to_update'] = 1
            ms.insert(t=self._table_name(), d=data)
            # ms.print_insert_sql(t=self._table_name(), d=data)

    def delete(self, ms):
        sql = "delete from prices_tb where " \
              "link_id='{}' " \
              "and shop_id='{}' " \
              "and SpiderDate<'{}'".format(self.link_id, self.shop_id, time_ago(minutes=5))
        ms.delete(sql=sql)


class TBMasterItem(BaseItem):

    def __init__(self, **kwargs):
        self.link_id = kwargs.get("link_id")
        self.shop_id = kwargs.get("shop_id")
        self.description = kwargs.get("description")
        self.price_tb = kwargs.get("price_tb")
        self.promotionprice = kwargs.get("promotionprice")
        self.sales = kwargs.get("sales", 0)
        self.rates = kwargs.get("rates", 0)
        self.update_date = kwargs.get("update_date", date.today())
        self.flag = kwargs.get("flag")
        self.narrative = kwargs.get("narrative")

    @staticmethod
    def _table_name():
        return 'tb_master'

    def _condition(self):
        condition = {"link_id": self.link_id}
        return condition

    def save(self, ms):
        data = self._pop_null_value()
        res = ms.get_dict(t=self._table_name(), c=self._condition())
        flag = ["update"]
        narrative = []
        if res:
            if abs(float(res[0]['price_tb']) - data['price_tb']) > 0.01:
                flag.append("price")
                narrative.append("更新销售价格:[{}]=>[{}]".format(res[0]['price_tb'], data['price_tb']))
            if abs(float(res[0]['promotionprice']) - data['promotionprice']) > 0.01:
                flag.append("promotion")
                narrative.append("更新优惠售价格:[{}]=>[{}]".format(res[0]['promotionprice'], data['promotionprice']))
            if res[0]['sales'] != data['sales']:
                flag.append("sale")
                narrative.append("更新销量:[{}]=>[{}]".format(res[0]['sales'], data['sales']))
            if res[0]['flag'] == 'XiaJia':
                flag.append("ShangJia")
                narrative.append("下架商品重新上架")
            data['flag'] = "_".join(flag)
            data['narrative'] = ";".join(narrative)
            ms.update(t=self._table_name(), set=data, c=self._condition())
        else:
            data['flag'] = 'insert'
            ms.insert(t=self._table_name(), d=data)

    def save_to_record(self, ms):
        start = 0
        limit = 1000
        while 1:
            column_name = self.__dict__.keys()
            res = ms.get(t=self._table_name(), cn=list(column_name), l=[str(start * limit), str(limit)])
            if not res:
                break
            d = []
            for r in res:
                a = tuple(str(x) for x in r)
                d.append(str(a))
            sql = "insert into tb_master_record " + str(tuple(column_name)).replace("'", "") + " values " + ",".join(d)
            ms.insert(sql=sql)
            start += 1


if __name__ == '__main__':
    # from db.my_sql import MySql
    # from settings import TEST_SERVER_DB_TEST
    # ms = MySql(db_setting=TEST_SERVER_DB_TEST)
    # t = TBMasterItem()
    # t.save_to_record(ms)
    pass
