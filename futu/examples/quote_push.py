# -*- coding: utf-8 -*-
"""
Examples for use the python functions: get push data
"""
from futu import *
from logger import Logger
import pandas as pd
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)

# 全局参数配置
TRADE_ENV = TrdEnv.SIMULATE              # REAL是真实交易，SIMULATE是仿真
UNLOCK_PASSWORD = '822130'                  # 解锁交易密码
STOCK_CODE = 'HK.800000'                    # 牛熊证参考的股票代码


# 将10位时间戳转换为时间字符串，默认为2017-10-01 13:37:04格式
def timestamp_to_datestr(time_stamp, format_string="%Y-%m-%d %H:%M:%S"):
    time_array = time.localtime(time_stamp)
    str_date = time.strftime(format_string, time_array)
    return str_date


# 将时间字符串转换为10位时间戳，时间字符串默认为2017-10-01 13:37:04格式
def datestr_to_timestamp(date_str, format_string="%Y-%m-%d %H:%M:%S"):
    time_array = time.strptime(date_str, format_string)
    time_stamp = int(time.mktime(time_array))
    return time_stamp


class StockQuoteTest(StockQuoteHandlerBase):
    """
    获得报价推送数据
    """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(StockQuoteTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            log.info("StockQuoteTest: error, msg: %s" % content)
            return RET_ERROR, content
        log.info(content)
        return RET_OK, content


class TickerTest(TickerHandlerBase):
    """ 获取逐笔推送数据 """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(TickerTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            log.info("* TickerTest: error, msg: %s" % content)
            return RET_ERROR, content
        log.info(content)
        return RET_OK, content


class OrderBookTest(OrderBookHandlerBase):
    """ 获得摆盘推送数据 """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(OrderBookTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            log.info("* OrderBookTest: error, msg: %s" % content)
            return RET_ERROR, content
        log.info(content)
        return RET_OK, content


class CurKlineTest(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret_code, data = super(CurKlineTest, self).on_recv_rsp(rsp_str)
        if ret_code != RET_OK:
            print("CurKlineTest: error, msg: %s" % data)
            return RET_ERROR, data
        log.info(data)
        return RET_OK, data


class RTDataTest(RTDataHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret_code, data = super(RTDataTest, self).on_recv_rsp(rsp_str)
        if ret_code != RET_OK:
            print("RTDataTest: error, msg: %s" % data)
            return RET_ERROR, data
        log.info(data)
        return RET_OK, data


if __name__ =="__main__":
    set_futu_debug_model(False)
    log = Logger(timestamp_to_datestr(time.time(), '%Y-%m-%d') + '_test.txt').get_logger()
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    trade_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
    if TRADE_ENV == TrdEnv.REAL:
        ret, data = trade_ctx.unlock_trade(UNLOCK_PASSWORD)
        if ret != RET_OK:
            raise Exception('解锁交易失败')
    # 订阅推送数据
    quote_ctx.subscribe([STOCK_CODE], [SubType.QUOTE, SubType.ORDER_BOOK, SubType.TICKER, SubType.K_1M, SubType.RT_DATA])

    # quote_ctx.set_handler(StockQuoteTest())
    # quote_ctx.set_handler(TickerTest())
    # quote_ctx.set_handler(OrderBookTest())
    # quote_ctx.set_handler(CurKlineTest())
    quote_ctx.set_handler(RTDataTest())
    quote_ctx.start()

