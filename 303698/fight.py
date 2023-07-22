# -*- coding: utf-8 -*-
# import os
import time
import datetime
import math
import futu as ft
from logger import Logger
import pandas as pd
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)


# 运行前需检查并改变下面的值
TRADE_ENV = ft.TrdEnv.REAL                          # 实盘交易：REAL，模拟交易：SIMULATE
PASSWORD_MD5 = 'd7866f93b87fc9c1b0a06a6a6669bada'   # 优先使用 PASSWORD_MD5 解锁
PASSWORD = ''                                       # 如果PASSWORD_MD5为空，则使用 PASSWORD 解锁
HOST = '127.0.0.1'
PORT = 11111

AUTO_BUY = True                                     # 是否自动买入，若是则下面的配置有效
BUY_LIST = [[60, 15, 100*1000]]                     # 固定多少秒，波动多少点，下单多少股
MAX_VOLUME = 300*1000                               # 最大持仓股数，若超过则不会再买入
FOLLOW_TREND = False                                # 买入策略是否为顺势买入，逆势则为False
BULL_CODE = ''                                      # 自动买入牛证的股票代码，格式HK.00700，填auto则会自动选股
BEAR_CODE = 'auto'                                  # 自动买入熊证的股票代码，格式HK.00700，填auto则会自动选股
CHECK_GOLDEN_LINE = False                           # 是否检查黄金分割线
ALLOW_ADD = True                                    # 是否允许补仓，若是则下面的ADD_PRICE_DIFF有效
ADD_PRICE_DIFF = 0.003                              # 持仓股票的现价与最近一次成交价的价差大于等于多少元，才允许补仓
BID_ASK_DIFF = 0.002                                # 买一价和卖一价的价差小于等于多少元，才允许买入

# AUTO_SELL_WHEN_DROP_PRICE = False                   # 是否设置按价格跟踪止损，若是则下面的DROP_PRICE有效
# DROP_PRICE = 100                                    # 下单后损失多少点自动卖出

AUTO_PLACE_ORDER = True                             # 买入后是否自动挂单分批卖出，若是则下面的ORDER_LIST有效
ORDER_LIST = [[400*1000, 200*1000, 2, 3],
              [300*1000, 150*1000, 2, 3],
              [200*1000, 100*1000, 2, 3],
              [100*1000, 50*1000, 2, 3]]            # 下单多少股以上（大的写前面），每单挂多少股，一单挂高几格，下一单挂高几格

AUTO_ADJUST_BUY = True                              # 是否自动调整挂的买单的价格，若是则下面的ADJUST_BUY_DICT有效
ADJUST_BUY_DICT = {
    'rise': [2, 3, 0],                              # 最近多少秒内，往持仓股票方向波动多少点，调整买单为第几档
    'fall': [2, 3, 2]                               # 最近多少秒内，往持仓股票反向波动多少点，调整买单为第几档
}

AUTO_ADJUST_SELL = True                             # 是否自动调整挂的卖单的价格，若是则下面的ADJUST_SELL_DICT有效
ADJUST_SELL_DICT = {
    'rise': [2, 3, 2],                              # 最近多少秒内，往持仓股票方向波动多少点，调整卖单为第几档
    'fall': [2, 3, 1]                               # 最近多少秒内，往持仓股票反向波动多少点，调整卖单为第几档
}

if TRADE_ENV == ft.TrdEnv.SIMULATE:
    AUTO_BUY = True                                 # 模拟盘强制开启自动买入
    AUTO_ADJUST_BUY = False                         # 模拟盘强制关闭自动调价买单
    # AUTO_SELL_WHEN_DROP_PRICE = True                # 模拟盘强制开启按价格跟踪止损

HSI_CODE = 'HK.800000'                              # 恒指代码
MHI_CODE = 'HK.MHImain'                             # 小恒指代码
MAX_ADJUST_DELTA_SECONDS = max(ADJUST_BUY_DICT['rise'][0], ADJUST_BUY_DICT['fall'][0], ADJUST_SELL_DICT['rise'][0], ADJUST_SELL_DICT['fall'][0])
# MAX_ADJUST_DELTA_PRICE = max(ADJUST_BUY_DICT['rise'][1], ADJUST_BUY_DICT['fall'][1], ADJUST_SELL_DICT['rise'][1], ADJUST_SELL_DICT['fall'][1])
MAX_DELTA_SECONDS = BUY_LIST[-1][0]
# DELTA_PRICE_LIST = []
# for x in range(0, len(BUY_LIST)):
#     DELTA_PRICE_LIST.append(BUY_LIST[x][1])
# MAX_DELTA_PRICE = max(DELTA_PRICE_LIST)


# 全局变量
log = None
quote_ctx = None
trade_ctx = None
glb = {
    'golden_line': [0, 0],
    'today_pl_val': 0,
    'trade_date': None,
    'restarted': False,
    'soon_over': False,
    'almost_over': False,
    'to_over': False,
    'over': False,
    'ticker_list': [],
    'price_list': [],
    'cur_price': 0,
    'last_price': 0,
    'last_filled_all_order': {},
    'adjust_ticker_list': [],
    'adjust_price_list': [],
    'submitted_buy_bull': None,
    'submitted_buy_bear': None,
    'submitted_sell_bull': None,
    'submitted_sell_bear': None,
    'submitted_sell_bull_list': [],
    'submitted_sell_bear_list': [],
    'order_book': {},
    'has_bull_list': [],
    'has_bear_list': [],
    'auto_place_order_flag': False,
    'submitted_buy_bull_flag': False,
    'submitted_buy_bear_flag': False,
    'pre_buy_bull_flag': True,
    'pre_buy_bear_flag': True,
    'bull_stop_price': 0,
    'bear_stop_price': 0,
    'force_replacing': False,
    'cache_get_stock_code': {
        '牛': {
            'data': None,
            'duration': 5,
            'last_time': 0
        },
        '熊': {
            'data': None,
            'duration': 5,
            'last_time': 0
        }
    }
}


# 节流函数
def throttle(fn, wait):
    last_call_time = None

    def throttled(*args, **kwargs):
        nonlocal last_call_time
        current_time = time.time()

        if last_call_time is not None:
            countdown = wait - (current_time - last_call_time)
        else:
            countdown = 0

        if countdown <= 0:
            last_call_time = current_time
            return fn(*args, **kwargs)
        else:
            log.info(f'{fn.__name__}调用限频节流中，{countdown}秒后再调用')

    return throttled


# 延时函数
def delay_execution(func, delay):
    def delayed_func(*args, **kwargs):
        result = func(*args, **kwargs)
        time.sleep(delay)
        return result

    return delayed_func


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


def get_golden_line(a, b):
    d = dict()
    d['0'] = a
    d['100'] = b
    d['200'] = a + (b - a) * 2
    d['2618'] = a + (b - a) * 2.618
    return d


def draw_golden_line():
    ret, data = quote_ctx.get_rt_data(HSI_CODE)
    # log.info('获取分时数据，data:\n%s' % data)
    if ret != ft.RET_OK:
        log.info('获取分时数据失败')
        return False
    if data.iloc[-1].time[0:10] != glb['trade_date'].get('time'):
        log.info('获取分时数据日期不是今天的，请重启客户端')
        return False
    glb['golden_line'] = [0, 0]
    data_min = data[data.cur_price == min(data.cur_price)]
    data_max = data[data.cur_price == max(data.cur_price)]
    min_index = data_min.index.tolist()[0]
    max_index = data_max.index.tolist()[0]
    data_min = data_min.iloc[0]
    data_max = data_max.iloc[0]
    if data_max.opened_mins > data_min.opened_mins:
        glb['golden_line'][0] = data_min.cur_price
        for i in range(min_index, max_index):
            if i >= 2:
                if (data.iloc[i - 2].cur_price < data.iloc[i - 1].cur_price > data.iloc[i].cur_price
                        and data.iloc[i - 1].cur_price - glb['golden_line'][0] > 80
                        and get_golden_line(glb['golden_line'][0], data.iloc[i - 1].cur_price)['2618'] >= data_max.cur_price):
                    glb['golden_line'][1] = data.iloc[i - 1].cur_price
                    break
    else:
        glb['golden_line'][0] = data_max.cur_price
        for i in range(max_index, min_index):
            if i >= 2:
                if (data.iloc[i - 2].cur_price > data.iloc[i - 1].cur_price < data.iloc[i].cur_price
                        and glb['golden_line'][0] - data.iloc[i - 1].cur_price > 80
                        and get_golden_line(glb['golden_line'][0], data.iloc[i - 1].cur_price)['2618'] <= data_min.cur_price):
                    glb['golden_line'][1] = data.iloc[i - 1].cur_price
                    break
    if glb['golden_line'][1] > 0:
        log.info('黄金分割0%%、100%%的数值分别为：%s' % glb['golden_line'])
        return data
    else:
        log.info('黄金分割还未确定')
        return False


def check_golden_line():
    data = draw_golden_line()
    if data is False:
        return False
    data = data.iloc[-1]
    golden_line = get_golden_line(glb['golden_line'][0], glb['golden_line'][1])
    if glb['golden_line'][1] < glb['golden_line'][0]:
        if data.cur_price > glb['golden_line'][1]:
            log.info('当前价格位于黄金分割0%和100%之间，适合买熊')
            value = '熊'
        elif data.cur_price > golden_line['200']:
            if data.cur_price > data.avg_price:
                log.info('当前价格位于黄金分割100%和200%之间，均线之上，适合买牛')
                value = '牛'
            else:
                log.info('当前价格位于黄金分割100%和200%之间，均线之下，适合买熊')
                value = '熊'
        else:
            log.info('当前价格位于黄金分割200%之上，别追了')
            value = '不允许'
    else:
        if data.cur_price < glb['golden_line'][1]:
            log.info('当前价格位于黄金分割0%和100%之间，适合买牛')
            value = '牛'
        elif data.cur_price < golden_line['200']:
            if data.cur_price > data.avg_price:
                log.info('当前价格位于黄金分割100%和200%之间，均线之上，适合买牛')
                value = '牛'
            else:
                log.info('当前价格位于黄金分割100%和200%之间，均线之下，适合买熊')
                value = '熊'
        else:
            log.info('当前价格位于黄金分割200%之上，别追了')
            value = '不允许'
    return value


# def auto_sell(cur_price):
#     if len(glb['has_bull_list']) > 0:
#         if glb['bull_stop_price'] == 0 or cur_price > glb['bull_stop_price'] + DROP_PRICE:
#             glb['bull_stop_price'] = cur_price - DROP_PRICE
#         elif cur_price <= glb['bull_stop_price']:
#             log.info('触发卖牛，当前价格%s，牛证止损价%s' % (cur_price, glb['bull_stop_price']))
#             sell_all('牛')
#     if len(glb['has_bear_list']) > 0:
#         if glb['bear_stop_price'] == 0 or cur_price < glb['bear_stop_price'] - DROP_PRICE:
#             glb['bear_stop_price'] = cur_price + DROP_PRICE
#         elif cur_price >= glb['bear_stop_price']:
#             log.info('触发卖熊，当前价格%s，熊证止损价%s' % (cur_price, glb['bear_stop_price']))
#             sell_all('熊')


def get_order_book(code):
    ret, data = quote_ctx.get_order_book(code, num=3)
    log.info('获取摆盘数据，ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('获取摆盘数据失败')
        return False
    return data


def _smart_buy(code, volume, price=None, type='Bid'):
    if price is None:
        data = get_order_book(code)
        if not data:
            return False
        if TRADE_ENV == ft.TrdEnv.SIMULATE:
            type = 'Ask'
        price = data[type][0][0]
    if not price > 0:
        log.info('价格不大于0，下买单失败')
        return False
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.BUY, trd_env=TRADE_ENV)
    log.info('下买单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('股票%s下买单失败，价格%s，数量%s' % (code, price, volume))
        return False
    else:
        log.info('股票%s下买单成功，价格%s，数量%s' % (code, price, volume))
        return data


def _smart_sell(code, volume, price=None, type='Ask'):
    if price is None:
        data = get_order_book(code)
        if not data:
            return False
        price = data[type][0][0]
    if not price > 0:
        log.info('价格不大于0，下卖单失败')
        return False
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.SELL, trd_env=TRADE_ENV)
    log.info('下卖单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('股票%s下卖单失败，价格%s，数量%s' % (code, price, volume))
        return False
    else:
        log.info('股票%s下卖单成功，价格%s，数量%s' % (code, price, volume))
        return data


def _cancel_order(order_id):
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.CANCEL, order_id=order_id, price=0, qty=0, trd_env=TRADE_ENV)
    log.info('撤单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('撤单失败')
        return False
    else:
        log.info('撤单成功')
        return data


def _modify_order(order_id, price, qty):
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.NORMAL, order_id=order_id, price=price, qty=qty, trd_env=TRADE_ENV)
    log.info('修改订单，ret: %s, data:\n%s, order_id: %s, price: %s, qty: %s' % (ret, data, order_id, price, qty))
    if ret != ft.RET_OK:
        log.info('修改订单失败')
        return False
    else:
        log.info('修改订单成功')
        return data


def _order_list_query(code='', status=''):
    status_filter_list = [ft.OrderStatus.SUBMITTED, ft.OrderStatus.FILLED_PART]
    if status != '':
        status_filter_list.append(status)
    ret, data = trade_ctx.order_list_query(status_filter_list=status_filter_list, code=code, trd_env=TRADE_ENV, refresh_cache=True)
    # log.info('查询订单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('查询订单失败')
        return False
    log.info('查询订单成功')
    if ft.OrderStatus.FILLED_ALL in status_filter_list:
        filled_all_data = data[data.order_status == ft.OrderStatus.FILLED_ALL]
        if not filled_all_data.empty:
            for index, row in filled_all_data.iterrows():
                code, create_time, price = row.code, row.create_time, row.price
                if code not in glb['last_filled_all_order']:
                    glb['last_filled_all_order'][code] = {'create_time': create_time, 'price': price}
                else:
                    if create_time > glb['last_filled_all_order'][code].create_time:
                        glb['last_filled_all_order'][code] = {'create_time': create_time, 'price': price}
            log.info('所有股票最近一次成交的订单价格为\n%s' % glb['last_filled_all_order'])
        else:
            log.info('还没有已全部成交的订单')
    data = data[(data.order_status == ft.OrderStatus.SUBMITTED) | (data.order_status == ft.OrderStatus.FILLED_PART)]
    for i in range(0, len(data)):
        data2 = data.iloc[i]
        if data2.trd_side == ft.TrdSide.BUY:
            set_submitted_buy(data2.code, data2.stock_name, data2)
        elif data2.trd_side == ft.TrdSide.SELL:
            set_submitted_sell(data2.code, data2.stock_name, data2)
    return data


def _cancel_all(code='', stock_type='', trd_side=''):
    if code == '' and stock_type == '' and trd_side == '':
        ret, data = trade_ctx.cancel_all_order(trd_env=TRADE_ENV)
        log.info('撤销全部订单，ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('撤销全部订单失败')
    data = order_list_query(code)
    if data is False:
        log.info('_cancel_all => order_list_query 撤销全部订单失败')
        return False
    if data is None:
        log.info('_cancel_all => order_list_query 限频节流中')
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            if stock_type == '' and trd_side == '':
                cancel_order(data2.order_id)
            elif data2.stock_name.find(stock_type) > -1 and trd_side == '':
                cancel_order(data2.order_id)
            elif data2.stock_name.find(stock_type) > -1 and trd_side == data2.trd_side:
                cancel_order(data2.order_id)
            elif stock_type == '' and trd_side == data2.trd_side:
                cancel_order(data2.order_id)


# 清仓指定股票
def force_sell(code='', qty=''):
    data = smart_sell(code, qty, type='Bid')
    if data is False:
        log.info('force_sell => smart_sell 清仓失败')
        return False
    if data is None:
        log.info('force_sell => smart_sell 限频节流中')
        return False
    if len(data) > 0:
        data0 = data.iloc[0]
        if data0.order_status == ft.OrderStatus.FILLED_PART:
            log.info('订单部分成交，改单降低一格')
            modify_order(data0.order_id, data0.price - 0.001, data0.qty)
        else:
            log.info('清仓成功')

# 清仓今日买的指定股票
def sell_all(code='', qty='', stock_type=''):
    if code != '':
        cancel_all(code=code)
        force_sell(code, qty)
        return True
    cancel_all() # 尽量调用撤销全部订单接口比较快
    data = position_list_query(stock_type=stock_type)
    if data is False or data is None:
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            log.info('准备清仓')
            if data2.qty > data2.can_sell_qty:
                cancel_all(code=data2.code)
            force_sell(data2.code, data2.qty)


def subscribe(code_list, subtype_list):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.subscribe(code_list, subtype_list)
    log.info('订阅%s数据，ret: %s, data:%s' % (subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('订阅%s数据失败' % subtype_list)
        return False
    else:
        return True


def unsubscribe(code_list, subtype_list):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.unsubscribe(code_list, subtype_list)
    log.info('取消订阅%s数据，ret: %s, data:%s' % (subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('取消订阅%s数据失败' % subtype_list)
        return False
    else:
        return True


def set_has(code, stock_name):
    if stock_name.find('牛') > -1:
        # log.info('持仓牛证：%s' % code)
        glb['has_bull_list'].append(code)
    elif stock_name.find('熊') > -1:
        # log.info('持仓熊证：%s' % code)
        glb['has_bear_list'].append(code)
    subscribe(code, ft.SubType.ORDER_BOOK)


def reset_has(stock_name='', real=False):
    if stock_name == '' or stock_name.find('牛') > -1:
        if real:
            glb['bull_stop_price'] = 0
            unsubscribe(glb['has_bull_list'], ft.SubType.ORDER_BOOK)
        glb['has_bull_list'] = []
    if stock_name == '' or stock_name.find('熊') > -1:
        if real:
            glb['bear_stop_price'] = 0
            unsubscribe(glb['has_bear_list'], ft.SubType.ORDER_BOOK)
        glb['has_bear_list'] = []


def set_submitted_buy(code, stock_name, data=None):
    if stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = True
        if data is not None:
            glb['submitted_buy_bull'] = data
        log.info('已设置买单数据，牛证%s' % code)
    elif stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = True
        if data is not None:
            glb['submitted_buy_bear'] = data
        log.info('已设置买单数据，熊证%s' % code)
    subscribe(code, ft.SubType.ORDER_BOOK)


def reset_submitted_buy(code, stock_name=''):
    if stock_name == '' or stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = False
        glb['submitted_buy_bull'] = None
        log.info('已重置买单数据，牛证%s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = False
        glb['submitted_buy_bear'] = None
        log.info('已重置买单数据，熊证%s' % code)
    # if not AUTO_ADJUST_SELL:
    #     unsubscribe(code, ft.SubType.ORDER_BOOK)


def append_data(dict_list, key, data):
    is_added = False
    for i in range(0, len(dict_list)):
        if dict_list[i][key] == data[key]:
            is_added = True
            dict_list[i] = data
            break
    if not is_added:
        dict_list.append(data)


def del_data(dict_list, key, data):
    for i in range(0, len(dict_list)):
        if dict_list[i][key] == data[key]:
            del dict_list[i]
            break


def set_submitted_sell(code, stock_name, data):
    if stock_name.find('牛') > -1:
        append_data(glb['submitted_sell_bull_list'], 'order_id', data)
        glb['submitted_sell_bull'] = glb['submitted_sell_bull_list'][-1]
        log.info('已设置卖单数据，牛证code: %s, price: %s' % (code, glb['submitted_sell_bull'].price))
    elif stock_name.find('熊') > -1:
        append_data(glb['submitted_sell_bear_list'], 'order_id', data)
        glb['submitted_sell_bear'] = glb['submitted_sell_bear_list'][-1]
        log.info('已设置卖单数据，熊证code: %s, price: %s' % (code, glb['submitted_sell_bear'].price))


def reset_submitted_sell(code, stock_name='', data=None):
    if stock_name == '' or stock_name.find('牛') > -1:
        del_data(glb['submitted_sell_bull_list'], 'order_id', data)
        if len(glb['submitted_sell_bull_list']) > 0:
            glb['submitted_sell_bull'] = glb['submitted_sell_bull_list'][-1]
        else:
            glb['submitted_sell_bull'] = None
        log.info('已重置卖单数据，牛证code: %s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        del_data(glb['submitted_sell_bear_list'], 'order_id', data)
        if len(glb['submitted_sell_bear_list']) > 0:
            glb['submitted_sell_bear'] = glb['submitted_sell_bear_list'][-1]
        else:
            glb['submitted_sell_bear'] = None
        log.info('已重置卖单数据，熊证code: %s' % code)


def _position_list_query(stock_type='', logging=True):
    ret, data = trade_ctx.position_list_query(trd_env=TRADE_ENV, refresh_cache=True)
    if logging:
        log.info('查询持仓列表，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('查询持仓列表失败，ret: %s, data:\n%s' % (ret, data))
        return False
    reset_has()
    data = data[(data.today_buy_qty > 0) & data.stock_name.str.contains('恒指')]

    # 统计今日盈亏
    glb['today_pl_val'] = 0
    for i in range(0, len(data)):
        data2 = data.iloc[i]
        glb['today_pl_val'] += data2.today_pl_val
        if data2.qty > 0 and data2.qty != data2.today_buy_qty - data2.today_sell_qty and data2.today_buy_qty > data2.today_sell_qty:
            log.info('持仓股数有问题，ret: %s, data:\n%s' % (ret, data))
    log.info('当前股价：%s，今日短炒盈亏：%s元' % (glb['cur_price'], glb['today_pl_val']))

    data = data[data.qty > 0]
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            set_has(data2.code, data2.stock_name)
            if data2.qty == data2.can_sell_qty:
                reset_submitted_buy(data2.code, data2.stock_name)
                if AUTO_PLACE_ORDER and data2.nominal_price > 0.02 and data2.stock_name.find('熊') > -1 and not glb['to_over']:
                    log.info('存在买入的股票%s没自动挂卖单，现在重新自动挂卖单，现价%s，成本价%s' % (data2.code, data2.nominal_price, data2.cost_price))
                    auto_place_order(data2.code, data2.qty, max(data2.nominal_price, data2.cost_price))
            if data2.nominal_price <= 0.02:
                log.info('存在买入的股票%s快被回收，现在开始自动换股，现价%s，成本价%s' % (data2.code, data2.nominal_price, data2.cost_price))
                glb.force_replacing = True
                sell_all(code=data2.code, qty=data2.qty)
                if data2.stock_name.find('熊') > -1:
                    to_buy('熊', data2.qty, force=True)
                # else:
                    # to_buy('牛', data2.qty)
        bull_data = data[data.stock_name.str.contains('牛')]
        bear_data = data[data.stock_name.str.contains('熊')]
        if len(bull_data) == 0:
            reset_has('牛', True)
        if len(bear_data) == 0:
            reset_has('熊', True)
        if stock_type == '牛':
            data = bull_data
        elif stock_type == '熊':
            data = bear_data
        if logging:
            log.info('今天买入的恒指牛熊持仓列表:\n%s' % data)
        return data
    else:
        log.info('没有持仓今天买入的恒指牛熊')
        reset_has(real=True) # TODO 没有取消订阅，因为has_bear_list已经在上面被清空了
        if glb['almost_over']:
            glb['over'] = True
            log.info('--------------------end--------------------')
        return []


class SysNotifyTest(ft.SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------OpenD通知推送--------------------')
        ret, data = super(SysNotifyTest, self).on_recv_rsp(rsp_pb)
        log.info('OpenD通知推送，ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('OpenD通知推送失败')
            return ret, data
        return ret, data


class OrderBookTest(ft.OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret, data = super(OrderBookTest, self).on_recv_rsp(rsp_str)
        # log.info('实时摆盘推送，ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('实时摆盘推送失败，ret: %s, data:%s' % (ret, data))
            return ret, data
        glb['order_book'][data['code']] = data
        return ret, data


def auto_place_order(code, volume, price):
    if glb['auto_place_order_flag']:
        log.info('已经开始自动挂单，不要重复了')
        return False
    if glb['almost_over']:
        glb['auto_place_order_flag'] = True
        data = smart_sell(code, volume)
        if data is False:
            log.info('auto_place_order => smart_sell 自动挂卖单失败')
        glb['auto_place_order_flag'] = False
        return
    if volume < 100*1000:
        return False
    # if glb['submitted_sell_bull'] is not None and glb['submitted_sell_bull'].code == code:
    #     return False
    # if glb['submitted_sell_bear'] is not None and glb['submitted_sell_bear'].code == code:
    #     return False
    glb['auto_place_order_flag'] = True
    item = []
    # ORDER_LIST = [[400*1000, 200*1000, 2, 3],
    #     [200*1000, 100*1000, 2, 3],
    #     [100*1000, 50*1000, 2, 3]]            # 下单多少股以上（大的写前面），每单挂多少股，一单挂高几格，下一单挂高几格
    for i in range(0, len(ORDER_LIST)):
        if volume >= ORDER_LIST[i][0]:
            item = ORDER_LIST[i]
            break
    if glb.force_replacing:
        price += 0.02
    for i in range(0, len(item) - 2):
        data = smart_sell(code, item[1], price + 0.001 * item[2 + i])
        if data is False:
            log.info('auto_place_order => smart_sell 自动挂卖单失败')
        elif glb.force_replacing:
            glb.force_replacing = False
    glb['auto_place_order_flag'] = False


class TradeOrderTest(ft.TradeOrderHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------订单状态推送--------------------')
        ret, data = super(TradeOrderTest, self).on_recv_rsp(rsp_pb)
        log.info('订单状态推送，ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('订单状态推送失败')
            return ret, data
        data = data.iloc[0]
        if data.trd_env != TRADE_ENV:
            log.info('该订单状态推送不是当前环境，无需处理')
            return ret, data
        if data.order_status == ft.OrderStatus.FILLED_ALL:
            glb['last_filled_all_order'][data.code] = {'create_time': data.create_time, 'price': data.price}
            if data.trd_side == ft.TrdSide.BUY:
                log.info('订单状态推送：订单买入全部成交')
                reset_submitted_buy(data.code, data.stock_name)
                set_has(data.code, data.stock_name)
                if AUTO_PLACE_ORDER and data.stock_name.find('熊') > -1 and not glb['to_over']:
                    auto_place_order(data.code, data.dealt_qty, data.price)
            elif data.trd_side == ft.TrdSide.SELL:
                log.info('订单状态推送：订单卖出全部成交')
                reset_submitted_sell(data.code, data.stock_name, data)
                position_list_query()
        elif data.order_status == ft.OrderStatus.FILLED_PART:
            if data.trd_side == ft.TrdSide.BUY:
                log.info('订单状态推送：订单买入部分成交')
                set_has(data.code, data.stock_name)
            elif data.trd_side == ft.TrdSide.SELL:
                log.info('订单状态推送：订单卖出部分成交')
        elif data.order_status == ft.OrderStatus.SUBMIT_FAILED or data.order_status == ft.OrderStatus.FAILED:
            log.info('订单状态推送：订单提交失败')
            position_list_query()
        elif data.order_status == ft.OrderStatus.CANCELLED_ALL or data.order_status == ft.OrderStatus.CANCELLED_PART:
            log.info('订单状态推送：订单已撤销')
            if data.trd_side == ft.TrdSide.BUY:
                reset_submitted_buy(data.code, data.stock_name)
            elif data.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(data.code, data.stock_name, data)
        elif data.order_status == ft.OrderStatus.SUBMITTED:
            log.info('订单状态推送：%s订单已提交，等待成交' % data.trd_side)
            if data.trd_side == ft.TrdSide.BUY:
                set_submitted_buy(data.code, data.stock_name, data)
            elif data.trd_side == ft.TrdSide.SELL:
                set_submitted_sell(data.code, data.stock_name, data)
        else:
            log.info('订单状态推送：订单状态为%s' % data.order_status)

        return ret, data


# class RTDataTest(ft.RTDataHandlerBase):
#     def on_recv_rsp(self, rsp_str):
#         # log.info('--------------------分时推送--------------------')
#         ret, data = super(RTDataTest, self).on_recv_rsp(rsp_str)
#         if ret != ft.RET_OK:
#             log.info('分时推送失败')
#             return ret, data
#         #    code                 time      is_blank    opened_mins  cur_price  last_close     avg_price  turnover  volume
#         # 0  HK.800000  2019-08-14 13:01:00     False          781   25416.63     25281.3  25482.145921  660739.0       0
#         glb['rt_data'] = data.iloc[0]

#         return ret, data


def auto_adjust(delta_price, i, adjust_dict, submitted_type):
    if glb[submitted_type] is None or glb[submitted_type].code not in glb['order_book']:
        return False
    data = glb[submitted_type]
    order_book = glb['order_book'].get(data.code)
    bid_price = order_book['Bid'][0][0]
    ask_price = order_book['Ask'][0][0]
    if bid_price >= 0.25:
        return False
    rise_price = 0
    fall_price = 0
    if submitted_type.find('buy') > -1:
        rise_price = bid_price - (adjust_dict['rise'][2] - 1) * 0.001
        fall_price = bid_price - (adjust_dict['fall'][2] - 1) * 0.001
    elif submitted_type.find('sell') > -1:
        rise_price = ask_price + (adjust_dict['rise'][2] - 1) * 0.001
        fall_price = ask_price + (adjust_dict['fall'][2] - 1) * 0.001
    rise_condition = False
    fall_condition = False
    if submitted_type.find('bull') > -1:
        rise_condition = delta_price >= adjust_dict['rise'][1] and glb['adjust_ticker_list'][-1][2] >= max(glb['adjust_price_list'])
        fall_condition = delta_price <= -adjust_dict['fall'][1] and glb['adjust_ticker_list'][-1][2] <= min(glb['adjust_price_list'])
    elif submitted_type.find('bear') > -1:
        rise_condition = delta_price <= -adjust_dict['rise'][1] and glb['adjust_ticker_list'][-1][2] <= min(glb['adjust_price_list'])
        fall_condition = delta_price >= adjust_dict['fall'][1] and glb['adjust_ticker_list'][-1][2] >= max(glb['adjust_price_list'])
    # 要买入的时候才考虑升档，要卖出的时候只考虑降档
    if rise_condition and submitted_type.find('buy') > -1:
        delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1][1]) - datestr_to_timestamp(glb['adjust_ticker_list'][i][1])
        if delta_seconds <= adjust_dict['rise'][0] and data.price < rise_price:
            log.info('订单价为%s，调整价为%s，准备升档' % (data.price, rise_price))
            data.price = rise_price
            modify_order(data.order_id, rise_price, data.qty)
    elif fall_condition:
        delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1][1]) - datestr_to_timestamp(glb['adjust_ticker_list'][i][1])
        if delta_seconds <= adjust_dict['fall'][0] and data.price > fall_price:
            log.info('订单价为%s，调整价为%s，准备降档' % (data.price, fall_price))
            data.price = fall_price
            modify_order(data.order_id, fall_price, data.qty)


def pre_adjust():
    # ADJUST_BUY_DICT = {
    #     'rise': [2, 3, 1],                              # 最近多少秒内，往持仓股票方向波动多少点，调整买单为第几档
    #     'fall': [2, 3, 2]                               # 最近多少秒内，往持仓股票反向波动多少点，调整买单为第几档
    # }
    while datestr_to_timestamp(glb['adjust_ticker_list'][-1][1]) - datestr_to_timestamp(glb['adjust_ticker_list'][0][1]) > MAX_ADJUST_DELTA_SECONDS:
        glb['adjust_ticker_list'].pop(0)
        glb['adjust_price_list'].pop(0)
    # i 从逐笔列表的倒数第二项开始，依次递减1，直到0为止，要遍历的前提是预设的多少秒内是不统一的
    # for i in range(len(glb['adjust_ticker_list']) - 2, -1, -1):
    i = 0
    delta_price = glb['adjust_ticker_list'][-1][2] - glb['adjust_ticker_list'][i][2]
    # if delta_price > MAX_ADJUST_DELTA_PRICE:
    #     break
    if AUTO_ADJUST_BUY:
        auto_adjust(delta_price, i, ADJUST_BUY_DICT, 'submitted_buy_bear')
        auto_adjust(delta_price, i, ADJUST_BUY_DICT, 'submitted_buy_bull')
    # 快收盘清仓的时候才自动调价卖出
    if AUTO_ADJUST_SELL and glb['almost_over']:
        auto_adjust(delta_price, i, ADJUST_SELL_DICT, 'submitted_sell_bear')
        auto_adjust(delta_price, i, ADJUST_SELL_DICT, 'submitted_sell_bull')


def _get_stock_code(stock_type='all', cache_first=False):
    cache = glb['cache_get_stock_code'].get(stock_type)
    if cache_first and cache['data'] is not None and time.time() - cache['last_time'] < cache['duration']:
        log.info('读取缓存数据：%s' % cache)
        return cache['data']
    cache['data'] = False

    req = ft.WarrantRequest()
    req.stock_owner = HSI_CODE  # 所属正股
    if stock_type == '牛':
        req.type_list = [ft.WrtType.BULL]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    elif stock_type == '熊':
        req.type_list = [ft.WrtType.BEAR]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    # req.issuer_list = [ft.Issuer.JP]  # Qot_Common.Issuer, 发行人过滤列表
    req.status = ft.WarrantStatus.NORMAL  # Qot_Common.WarrantStatus, 窝轮状态
    req.cur_price_min = 0.04  # 最新价过滤起点
    req.cur_price_max = 0.12  # 最新价过滤终点
    req.conversion_min = 10000  # 换股比率过滤起点
    req.conversion_max = 10000  # 换股比率过滤终点
    req.vol_min = 1000  # 成交量的过滤下限，单位K
    req.sort_field = ft.SortField.VOLUME  # 根据哪个字段排序
    req.ascend = False  # 升序ture, 降序false
    req.begin = 0  # 数据起始点
    req.num = 3  # 返回数据个数，最大200

    ret, data = quote_ctx.get_warrant(req=req)
    log.info('获取恒指牛熊，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('获取恒指牛熊失败')
    else:
        data = data[0]
        data = data[data.stock_owner == HSI_CODE] # 坑，返回的结果还要再过滤一次
        # data = data[data.cur_price == min(data.cur_price)]
        if len(data) > 0:
            data = data.iloc[0]
            bid_ask_diff = data.ask_price - data.bid_price
            if data.ask_price != 0 and (bid_ask_diff < BID_ASK_DIFF or math.isclose(bid_ask_diff, BID_ASK_DIFF)):
                log.info('买一价%s和卖一价%s的价差%s小于等于%s元，允许买入' % (data.bid_price, data.ask_price, bid_ask_diff, BID_ASK_DIFF))
                cache['data'] = data
            else:
                log.info('买一价%s和卖一价%s的价差%s大于%s元，不允许买入' % (data.bid_price, data.ask_price, bid_ask_diff, BID_ASK_DIFF))
        else:
            log.info('挑选失败，没有符合条件的')
    cache['last_time'] = time.time()
    return cache['data']


def to_buy(stock_type, volume, force=False):
    global BULL_CODE, BEAR_CODE
    if volume <= 0:
        return False
    code = ''
    if stock_type == '牛':
        code = BULL_CODE
    elif stock_type == '熊':
        code = BEAR_CODE
    if code == '':
        return False

    if force is False:
        data = position_list_query(stock_type=stock_type)
        if data is False or data is None:
            return False
        if len(data) > 0:
            data0 = data.iloc[0]
            total_qty = sum(data.qty)
            if total_qty + volume > MAX_VOLUME:
                if MAX_VOLUME - total_qty >= 100*1000:
                    volume = MAX_VOLUME - total_qty
                    log.info('当前持仓股数%s，买入后将会超过最大持仓股数%s，最多只能买%s' % (total_qty, MAX_VOLUME, volume))
                else:
                    log.info('当前持仓股数%s，买入后将会超过最大持仓股数%s，不允许补仓' % (total_qty, MAX_VOLUME))
                    return False
            if total_qty > 0:
                if not ALLOW_ADD:
                    log.info('配置不允许补仓')
                    return False
                reference_price = glb['last_filled_all_order'].get(data0.code, {}).get('price')
                if not reference_price:
                    log.info('股票%s的最近一次成交价不存在，\n%s' % (data0.code, glb['last_filled_all_order']))
                    reference_price = data0.cost_price
                add_price_diff = reference_price - data0.nominal_price
                if add_price_diff < ADD_PRICE_DIFF and not math.isclose(add_price_diff, ADD_PRICE_DIFF):
                    log.info('持仓股票%s的现价%s与最近一次成交价%s的价差%s小于%s元，不允许补仓' % (data0.code, data0.nominal_price, reference_price, add_price_diff, ADD_PRICE_DIFF))
                    if stock_type == '牛':
                        glb['pre_buy_bull_flag'] = False
                    elif stock_type == '熊':
                        glb['pre_buy_bear_flag'] = False
                    return False
                log.info('持仓股票%s的现价%s与最近一次成交价%s的价差%s大于等于%s元，允许补仓' % (data0.code, data0.nominal_price, reference_price, add_price_diff, ADD_PRICE_DIFF))

    if code == 'auto':
        data = get_stock_code(stock_type=stock_type)
        if data is False or data is None:
            return False
        code = data.stock

    set_submitted_buy(code, stock_type)
    data = smart_buy(code, volume)
    if data is False or data is None:
        reset_submitted_buy(code, stock_type)
    else:
        # 刚买入，先设置别追买，要等待时机才买
        if stock_type == '牛':
            glb['pre_buy_bull_flag'] = False
        elif stock_type == '熊':
            glb['pre_buy_bear_flag'] = False
    return data


def auto_buy(buy_type, volume):
    # log.info('auto_buy，submitted_buy_bear_flag：%s' % glb['submitted_buy_bear_flag'])
    if buy_type == '牛' and not glb['submitted_buy_bull_flag'] and (ALLOW_ADD or len(glb['has_bull_list']) == 0):
        glb['pre_buy_bear_flag'] = True
        if BULL_CODE == '':
            return False
        if not glb['pre_buy_bull_flag']:
            log.info('刚买入不久，还未掉头，不宜追牛')
            return False
        if not CHECK_GOLDEN_LINE or check_golden_line() == '牛':
            log.info('触发买牛')
            to_buy('牛', volume)
    elif buy_type == '熊' and not glb['submitted_buy_bear_flag'] and (ALLOW_ADD or len(glb['has_bear_list']) == 0):
        glb['pre_buy_bull_flag'] = True
        if BEAR_CODE == '':
            return False
        if not glb['pre_buy_bear_flag']:
            log.info('刚买入不久，还未掉头，不宜追熊')
            return False
        if not CHECK_GOLDEN_LINE or check_golden_line() == '熊':
            log.info('触发买熊')
            to_buy('熊', volume)


def pre_buy():
    #       code              time                 price        volume  turnover    ticker_direction       sequence   type      push_data_type
    # 0     HK_FUTURE.999010  2019-03-01 00:59:55  28655.0       1   28655.0              BUY  6663097136416030721  AUTO_MATCH          CACHE
    # BUY_LIST = [[60, 15, 200*1000]]
    while datestr_to_timestamp(glb['ticker_list'][-1][1]) - datestr_to_timestamp(glb['ticker_list'][0][1]) > MAX_DELTA_SECONDS:
        glb['ticker_list'].pop(0)
        glb['price_list'].pop(0)
    # if glb['ticker_list'][-1][1][-2:] != '00':
    #     return False
    pre_buy_flag = False
    for j in range(0, len(BUY_LIST)):
        i = 0
        delta_price = glb['ticker_list'][-1][2] - glb['ticker_list'][i][2]
        # 60秒内上涨点数比预设点数还要大，且最后的价格是最高的价格
        if delta_price >= BUY_LIST[j][1] and glb['ticker_list'][-1][2] >= max(glb['price_list']):
            delta_seconds = datestr_to_timestamp(glb['ticker_list'][-1][1]) - datestr_to_timestamp(glb['ticker_list'][i][1])
            if delta_seconds <= BUY_LIST[j][0] and len(BUY_LIST[j]) == 3:
                pre_buy_flag = True
                if FOLLOW_TREND:
                    BUY_LIST[j].extend(['牛', i, delta_seconds, delta_price])
                else:
                    BUY_LIST[j].extend(['熊', i, delta_seconds, delta_price])
        # 60秒内下跌点数比预设点数还要小，且最后的价格是最低的价格
        elif delta_price <= -BUY_LIST[j][1] and glb['ticker_list'][-1][2] <= min(glb['price_list']):
            delta_seconds = datestr_to_timestamp(glb['ticker_list'][-1][1]) - datestr_to_timestamp(glb['ticker_list'][i][1])
            if delta_seconds <= BUY_LIST[j][0] and len(BUY_LIST[j]) == 3:
                pre_buy_flag = True
                if FOLLOW_TREND:
                    BUY_LIST[j].extend(['熊', i, delta_seconds, delta_price])
                else:
                    BUY_LIST[j].extend(['牛', i, delta_seconds, delta_price])
    if pre_buy_flag:
        # [[60, 15, 200000, '熊', 0, 60, 16.0]]
        # log.info(BUY_LIST)
        for j in range(0, len(BUY_LIST)):
            if len(BUY_LIST[j]) > 3:
                # log.info(glb['ticker_list'][BUY_LIST[j][4]])
                # log.info(glb['ticker_list'][-1])
                # log.info('最近%s秒内波动了%s点' % (BUY_LIST[j][5], BUY_LIST[j][6]))
                auto_buy(BUY_LIST[j][3], BUY_LIST[j][2])
                BUY_LIST[j] = BUY_LIST[j][0:3]


class TickerTest(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_str):
        # log.info('--------------------逐笔明细--------------------')
        ret, data = super(TickerTest, self).on_recv_rsp(rsp_str)
        if ret != ft.RET_OK:
            log.info('逐笔明细推送失败')
            return ret, data
        #       code              time                 price        volume  turnover    ticker_direction       sequence   type      push_data_type
        # 0     HK_FUTURE.999010  2019-03-01 00:59:55  28655.0       1   28655.0              BUY  6663097136416030721  AUTO_MATCH          CACHE
        data0 = data.iloc[0]
        # log.info('逐笔明细推送, data:\n%s' % data0)
        t = data0.time
        h = int(t[11:13])
        m = int(t[14:16])
        s = int(t[17:19])
        if h < 9 or h == 9 and m < 30 or h >= 16:
            # print(data)
            if h == 9 and m == 15 and not glb['restarted']:
                log.info('准备开盘，需要重置数据')
                glb['restarted'] = True
                resetData()
            elif h == 16 and m == 0 and s == 0:
                log.info('--------------------收盘--------------------')
            return ret, data

        if h == 9 and m == 30 and glb['restarted']:
            log.info('--------------------开盘--------------------')
            glb['restarted'] = False
        elif (glb['trade_date'].get('trade_date_type') == 'MORNING' and h == 11 or h == 15) and m >= 30:
            glb['soon_over'] = True
            if m >= 55:
                if not glb['almost_over']:
                    glb['almost_over'] = True
                    cancel_all()
                    position_list_query()
                if m >= 59:
                    glb['to_over'] = True
                    if not glb['over']:
                        sell_all(stock_type='熊')
                        log.info('--------------------end--------------------')
                return ret, data

        if glb['to_over']:
            return ret, data

        # 有持仓的时候，每波动10点查询持仓列表
        glb['cur_price'] = data0.price
        if (len(glb['has_bull_list']) > 0 or len(glb['has_bear_list']) > 0) and abs(glb['cur_price'] - glb['last_price']) >= 10:
            glb['last_price'] = glb['cur_price']
            position_list_query(logging=False)

        # 自动买入和自动调价
        if AUTO_BUY or AUTO_ADJUST_BUY or AUTO_ADJUST_SELL:
            data_list = data.values.tolist()
            for i in range(0, len(data_list)):
                if AUTO_BUY and not glb['soon_over']:
                    glb['ticker_list'].append(data_list[i])
                    glb['price_list'].append(data_list[i][2])
                if AUTO_ADJUST_BUY or AUTO_ADJUST_SELL:
                    glb['adjust_ticker_list'].append(data_list[i])
                    glb['adjust_price_list'].append(data_list[i][2])
            # 尾盘就不买了
            if AUTO_BUY and not glb['soon_over']:
                pre_buy()
            # 自动调价
            if AUTO_ADJUST_BUY or AUTO_ADJUST_SELL:
                pre_adjust()

        return ret, data


# 获取交易日
def request_trading_days():
    today = datetime.date.today()
    if today.month < 12:
        last_day = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(today.year + 1, 1, 1) - datetime.timedelta(days=1)
    ret, data = quote_ctx.request_trading_days(ft.Market.HK, start=today.strftime('%Y-%m-%d'), end=last_day.strftime('%Y-%m-%d'))
    log.info('获取交易日，ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        glb['restarted'] = False
        log.info('获取交易日失败')
        return False
    if len(data) == 0 or data[0]['time'] != today.strftime('%Y-%m-%d'):
        log.info('今天不是交易日')
        return False
    glb['trade_date'] = data[0]
    return glb['trade_date']


# 重置数据
def resetData():
    global log
    log = Logger('logs/' + timestamp_to_datestr(time.time(), '%Y-%m-%d.log')).get_logger()
    log.info('--------------------start--------------------')
    glb['soon_over'] = False
    glb['almost_over'] = False
    glb['to_over'] = False
    glb['over'] = False
    glb['pre_buy_bull_flag'] = True
    glb['pre_buy_bear_flag'] = True
    request_trading_days()


# 每 30 秒内最多请求 10 次查询持仓接口
position_list_query = throttle(_position_list_query, 3)
# 每 30 秒内最多请求 15 次下单接口，且连续两次请求的间隔不可小于 0.02 秒
smart_buy = throttle(_smart_buy, 2)
smart_sell = delay_execution(_smart_sell, 0.02) # 自动挂卖单是遍历的，所以不能节流，只能延时
# 每 30 秒内最多请求 60 次筛选窝轮接口
get_stock_code = throttle(_get_stock_code, 0.5)
# 每 30 秒内最多请求 10 次查询今日订单接口
order_list_query = throttle(_order_list_query, 3)
# 每 30 秒内最多请求 20 次改单撤单接口，且连续两次请求的间隔不可小于 0.04 秒
modify_order = delay_execution(_modify_order, 0.04) # 自动调价要连续执行，所以不能节流，只能延时
cancel_order = delay_execution(_cancel_order, 0.04) # 撤销订单是遍历的，所以不能节流，只能延时
cancel_all = delay_execution(_cancel_all, 0.04) # 撤销全部订单也是遍历的，所以不能节流，只能延时


def start():
    global quote_ctx, trade_ctx
    temp_quote_ctx = None
    temp_trade_ctx = None
    if quote_ctx is not None:
        temp_quote_ctx = quote_ctx
        temp_trade_ctx = trade_ctx
        log.info('开始重启新的程序')
    quote_ctx = ft.OpenQuoteContext(host=HOST, port=PORT)
    trade_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.HK, host=HOST, port=PORT)
    resetData()
    if TRADE_ENV == ft.TrdEnv.REAL:
        ret, data = trade_ctx.unlock_trade(password_md5=PASSWORD_MD5, password=PASSWORD)
        log.info('解锁交易，ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            glb['restarted'] = False
            log.info('解锁交易失败')
            return False
    data = subscribe(MHI_CODE, ft.SubType.TICKER)
    if data is False:
        glb['restarted'] = False
        return False
    # data = subscribe(HSI_CODE, ft.SubType.RT_DATA)
    # if data is False:
    #     glb['restarted'] = False
    #     return False
    quote_ctx.set_handler(SysNotifyTest())
    quote_ctx.set_handler(TickerTest())
    trade_ctx.set_handler(TradeOrderTest())
    if AUTO_ADJUST_BUY or AUTO_ADJUST_SELL:
        quote_ctx.set_handler(OrderBookTest())
    position_list_query()
    order_list_query(status=ft.OrderStatus.FILLED_ALL)
    # get_stock_code('熊')
    if CHECK_GOLDEN_LINE:
        check_golden_line()

    ret, data = quote_ctx.query_subscription()
    log.info('查询订阅数据，ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('查询订阅数据失败')
    quote_ctx.start()
    if temp_quote_ctx is not None:
        temp_quote_ctx.close()
        temp_trade_ctx.close()
        log.info('程序重启成功')


if __name__ == "__main__":
    ft.set_futu_debug_model(False)
    # log = Logger('logs/' + os.path.basename(__file__)[:-3], True).get_logger()
    start()
