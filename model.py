import abc

from tools.tools_method import time_format


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

    def save(self, ms):
        data = self._pop_null_value()
        condition = self._condition()
        res = ms.get(t=self._table_name(), c=condition)
        if res:
            ms.update(t=self._table_name(), set=data, c=condition)
            # ms.print_update_sql(t=self._table_name(), set=data, c=condition)
        else:
            ms.insert(t=self._table_name(), d=data)
            # ms.print_insert_sql(t=self._table_name(), d=data)


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
        self.updateTime = kwargs.get('updateTime')
        self.isDetaildown = kwargs.get('isDetaildown')
        self.isVerify = kwargs.get('isVerify')

    def _condition(self):
        condition = {"orderNo": self.orderNo}
        return condition

    @staticmethod
    def _table_name():
        return "tb_order_spider"


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
        self.isRefund = kwargs.get('isRefund')
        self.refundStatus = kwargs.get('refundStatus')

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
        self.SpiderDate = kwargs.get('SpiderDate', time_format())
        self.attribute_map = kwargs.get('attribute_map')

    @staticmethod
    def _table_name():
        return "prices_tb"

    def _condition(self):
        condition = {"stockid": self.stockid, "link_id": self.link_id, "shop_id": self.shop_id}
        return condition

    def save(self, ms):
        data = self._pop_null_value()
        if data.get('attribute_map'):
            data.pop('attribute_map')
        condition = self._condition()
        res = ms.get(t=self._table_name(), c=condition)
        if res:
            data['flag'] = 'update'
            data.pop('operator')
            ms.update(t=self._table_name(), set=data, c=condition)
            # ms.print_update_sql(t=self._table_name(), set=data, c=condition)
            return 0
        else:
            data['flag'] = 'add'
            data['last_time'] = time_format()
            data['package_number'] = 1
            ms.insert(t=self._table_name(), d=data)
            # ms.print_insert_sql(t=self._table_name(), d=data)
            return 1


if __name__ == '__main__':
    pass
    # i = TBOrderDetailItem(itemNo=2, unitPrice=0, orderNo="")
    # i.pop_null_value()
