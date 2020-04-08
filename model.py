class BaseItem(object):
    def _pop_null_value(self):
        data = self.__dict__.copy()
        for key in list(data.keys()):
            if data.get(key) is None:
                data.pop(key)
        return data


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

    def __str__(self):
        return str(self.__dict__)

    def _condition(self):
        condition = {"orderNo": self.orderNo}
        return condition

    @staticmethod
    def _table_name():
        return "tb_order_spider"

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

    def __str__(self):
        return str(self.__dict__)

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


if __name__ == '__main__':
    i = TBOrderDetailItem(itemNo=2, unitPrice=0, orderNo="")
    i.pop_null_value()
