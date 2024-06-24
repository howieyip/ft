# -*- coding: utf-8 -*-
import time
import datetime
import math
import futu as ft
from utils.logger import Logger
import pandas as pd
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)


# 配置
conf = {
    'log_file': 'logs/fight',
    'TRADE_ENV': ft.TrdEnv.REAL,                          # 实盘交易：REAL，模拟交易：SIMULATE
    'PASSWORD_MD5': 'd7866f93b87fc9c1b0a06a6a6669bada',   # 优先使用 PASSWORD_MD5 解锁
    'PASSWORD': '',                                       # 如果PASSWORD_MD5为空，则使用 PASSWORD 解锁
    'HOST': '127.0.0.1',
    'PORT': 11111,

    'AUTO_BUY': False,                              # 是否自动买入，若是则下面的配置有效
    'TRY_RECOVERY': False,                          # 是否尝试买快回收的股票
    'BIG-ONE-WAY': False,                           # 是否采用大单边策略
    'FOLLOW_TREND': False,                          # 买入策略是否为顺势买入，逆势则为False
    'BULL_CODE': '',                                # 自动买入牛证的股票代码，格式HK.00700，填auto则会自动选股
    'BEAR_CODE': '',                                # 自动买入熊证的股票代码，格式HK.00700，填auto则会自动选股
    'GOLDEN_LINE_DIFF': 80,                         # 黄金分割线0-100之间要间隔多少点
    'CUR_PRICE_MIN': 0.03,
    'CUR_PRICE_MAX': 0.10,                          # 这个值非常重要，当天买入的新股票如果低于这个价，会被当成是日内短炒止损

    'DELTA_SECONDS': 60,                            # 多少秒内
    'DELTA_PRICE_MIN': 8,                           # 最小波动多少点
    'DELTA_PRICE_MAX': 18,                          # 最大波动多少点
    'FOLLOW_TREND_PRICE': 20,                       # 波动多少点，强制改为顺势买入
    'BUY_VOLUME': 100e3,                            # 下单多少股
    'MAX_VOLUME': 300e3,                            # 最大持仓股数，若超过则不会再买入
    'LOSS_PRICE_DIFF': 0.01,                        # 止损价差，买入后单价亏多少元要强制止损

    'AUTO_ADJUST': False,                           # 是否自动调整订单价格，若是则下面的AUTO_ADJUST_BUY和AUTO_ADJUST_SELL有效
    'AUTO_ADJUST_BUY': True,                        # 是否自动调整挂的买单的价格，若是则下面的ADJUST_BUY_DICT有效
    'ADJUST_BUY_DICT': {
        'rise': [60, 1, 1],                         # 最近多少秒内，往持仓股票方向波动多少点，调整买单为第几档
        'fall': [60, 1, 2]                          # 最近多少秒内，往持仓股票反向波动多少点，调整买单为第几档
    },

    'ALLOW_ADD': True,                              # 是否允许补仓，若是则下面的ADD_PRICE_DIFF有效
    'ADD_PRICE_DIFF': 0.005,                        # 持仓股票的现价与最近一次成交价的价差大于等于多少元，才允许补仓

    'AUTO_PLACE_ORDER': False,                      # 买入后是否自动挂单分批卖出，若是则下面的ORDER_LIST有效
    'ORDER_LIST': [                                 # 下单多少股以上（大的写前面），每单挂多少股，例如下单800k，分3档200k 200k 400k挂单
        [800e3, 200e3, 200e3, 200e3, 200e3],
        [700e3, 150e3, 150e3, 200e3, 200e3],
        [600e3, 150e3, 150e3, 150e3, 150e3],
        [500e3, 100e3, 100e3, 150e3, 150e3],
        [400e3, 100e3, 100e3, 100e3, 100e3],
        [300e3, 50e3, 50e3, 100e3, 100e3],
        [200e3, 50e3, 50e3, 50e3, 50e3],
        [150e3, 50e3, 0, 50e3, 50e3],
        [100e3, 50e3, 0, 50e3, 0]
    ],
    'FIRST_ORDER_DIFF': 0.002,                      # 第一个卖单为第几档
    'LAST_ORDER_DIFF': 0.005,                       # 最后一个卖单为第几档

    'AUTO_ADJUST_SELL': True,                       # 是否自动调整挂的卖单的价格，若是则下面的ADJUST_SELL_DICT有效
    'ADJUST_SELL_DICT': {
        'rise': [60, 1, 2],                         # 最近多少秒内，往持仓股票方向波动多少点，调整卖单为第几档
        'fall': [60, 1, 1]                          # 最近多少秒内，往持仓股票反向波动多少点，调整卖单为第几档
    },
    'AUTO_MOVE_POSITION': False,                    # 是否自动强制移仓，是则下面的MOVE_POSITION_DICT生效
    'MOVE_POSITION_DICT': {
        'from_code': 'HK.',                         # 指定code移仓目前是一次性应急用
        'to_code': 'auto',
        'volume': 400e3,
        'cur_price_min': 0.15,
        'cur_price_max': 0.19
    }
}


# 常量
CONST = {
    'HSI_CODE': 'HK.800000',
    'MHI_CODE': 'HK.MHImain',
    'bull': '牛',
    'bear': '熊'
}


# 全局变量
log = None
quote_ctx = None
trade_ctx = None
glb = {
    'rt_data': None,
    'golden_line': {'0': 0, '100': 0, 'diff': 0, 'reverse': '', 'check_result': ''},
    'loss': {},
    'today_pl_val_bull': 0,
    'today_pl_val_bear': 0,
    'trade_date': {},
    'afternoon': False,
    'soon_over': False,
    'almost_over': False,
    'to_over': False,
    'over': False,
    'ticker_list': [],
    'cur_price': 0,
    'last_price': 0,
    'kline_data': None,
    'MA10': 0,
    'MA20': 0,
    'max_nominal_price': {},
    'filled_all_last_order': {},
    'filled_all_buy_order': {},
    'adjust_ticker_list': [],
    'submitted_buy_bull_flag': False,
    'submitted_buy_bear_flag': False,
    'submitted_buy_bull_data': None,
    'submitted_buy_bear_data': None,
    'submitted_sell_bull_data': None,
    'submitted_sell_bear_data': None,
    'submitted_sell_bull_list': [],
    'submitted_sell_bear_list': [],
    'order_book': {},
    'auto_buy_list': [],
    'has_bull_list': [],
    'has_bear_list': [],
    'auto_place_order_flag': False,
    'move_position': False,
    'cache_get_stock_code': {
        'bull': {
            'data': None,
            'duration': 5,
            'last_time': 0
        },
        'bear': {
            'data': None,
            'duration': 5,
            'last_time': 0
        },
        'all': {
            'data': None,
            'duration': 5,
            'last_time': 0
        }
    }
}


# 添加数组元素，不重复
def add_unique_element(arr, element):
    if element not in arr:
        arr.append(element)
    return arr


# 节流函数
def throttle(fn, wait, need_log=True):
    last_call_time = None
    logged = False

    def throttled(*args, **kwargs):
        nonlocal last_call_time, logged, need_log
        current_time = time.time()

        if last_call_time is not None:
            countdown = round(wait - (current_time - last_call_time), 3)
        else:
            countdown = 0

        if countdown <= 0:
            last_call_time = current_time
            logged = False
            # if need_log:
            #     log.info(f'{fn.__name__} call success')
            return fn(*args, **kwargs)
        if need_log and not logged:
            log.info(f'{fn.__name__} call throttling, {countdown}s remaining')
            logged = True
        return None

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
def datestr_to_timestamp(time_str, format_str="%Y-%m-%d %H:%M:%S", pattern=r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'):
    # 去掉小数部分
    time_str = time_str.split('.')[0]
    # if re.fullmatch(pattern, time_str):
    return datetime.datetime.strptime(time_str, format_str).timestamp()
    # else:
    #     return time.time()


def get_golden_line(line=None):
    if line is None:
        line = glb['golden_line']
    line['diff'] = round(line['100'] - line['0'], 2)
    line['reverse'] = glb['golden_line']['reverse']
    if line['diff'] > 0 and glb['golden_line']['diff'] < 0:
        line['reverse'] = 'bull'
    elif line['diff'] < 0 and glb['golden_line']['diff'] > 0:
        line['reverse'] = 'bear'
    # line['123.6'] = line['0'] + line['diff'] * 1.236
    line['261.8'] = line['0'] + line['diff'] * 2.618
    line['300'] = line['0'] + line['diff'] * 3
    glb['golden_line'] = line
    return line


def get_rt_data():
    ret, rt_data = quote_ctx.get_rt_data(CONST['HSI_CODE'])
    # log.info('get_rt_data, ret: %s, rt_data:%s' % (ret, rt_data))
    if ret != ft.RET_OK:
        log.info('get_rt_data error, ret: %s, rt_data:\n%s' % (ret, rt_data))
        return False
    #       code                 time  is_blank  opened_mins  cur_price  last_close     avg_price  volume      turnover
    # 0    HK.800000  2023-10-31 09:30:00     False          570   17337.70    17406.36  17337.700000       0  1.682861e+09
    # 1    HK.800000  2023-10-31 09:31:00     False          571   17214.94    17406.36  17276.320000       0  1.822654e+09
    # 2    HK.800000  2023-10-31 09:32:00     False          572   17223.84    17406.36  17258.826667       0  8.516341e+08
    # 3    HK.800000  2023-10-31 09:33:00     False          573   17224.69    17406.36  17250.292500       0  7.468972e+08
    # ret, data = (0, {'opened_mins': [570, 571, 572, 573],
    # 'cur_price': [17337.70, 17214.94, 17223.84, 17212.21]})
    # data = pd.DataFrame(data)
    glb['rt_data'] = rt_data
    return rt_data


def get_cur_kline(num=20):
    ret, kline_data = quote_ctx.get_cur_kline(CONST['MHI_CODE'], num, ft.KLType.K_1M)
    # log.info('get_cur_kline, ret: %s, kline_data:%s' % (ret, kline_data))
    if ret != ft.RET_OK:
        log.info('get_cur_kline error, ret: %s, kline_data:\n%s' % (ret, kline_data))
        return False
    #            code         name             time_key     open    close     high      low  volume  turnover  pe_ratio  turnover_rate  last_close
    # 0   HK.MHImain  小恒指主连(2406)  2024-06-15 02:42:00  17773.0  17772.0  17773.0  17769.0      18  319883.0       0.0            0.0     17772.0
    # 1   HK.MHImain  小恒指主连(2406)  2024-06-15 02:43:00  17775.0  17776.0  17776.0  17775.0       8  142205.0       0.0            0.0     17772.0
    # 18  HK.MHImain  小恒指主连(2406)  2024-06-15 03:00:00  17796.0  17796.0  17796.0  17793.0      30  533842.0       0.0            0.0     17795.0
    # 19  HK.MHImain  小恒指主连(2406)  2024-06-17 09:16:00  17796.0  17796.0  17796.0  17796.0       0       0.0       0.0            0.0     17796.0
    glb['kline_data'] = kline_data
    return kline_data


def draw_ma_line(need_log=True):
    kline_data = get_cur_kline()
    if kline_data is False or len(kline_data) < 20:
        return False
    MA20_SUM = 0
    MA10_SUM = 0
    for i in range(-1, -21, -1):
        MA20_SUM += kline_data.iloc[i].close
        if i > -11:
            MA10_SUM += kline_data.iloc[i].close
    glb['MA10'] = round(MA10_SUM / 10, 3)
    glb['MA20'] = round(MA20_SUM / 20, 3)
    if need_log:
        log.info('draw_ma_line, MA10: %s, MA20: %s' % (glb['MA10'], glb['MA20']))


def draw_golden_line():
    rt_data = get_rt_data()
    if rt_data is False or len(rt_data) < 5:
        return False
    if rt_data.iloc[-1].time[0:10] != glb['trade_date'].get('time'):
        log.info('get_rt_data not today')
        # return False
    data = rt_data.iloc[:-1] # 排除最后一个数据，因为在当前分钟未结束时画分割线是不准确的
    # cur_index = data.shape[0] - 1
    nlargest_data = data.nlargest(2, 'cur_price')
    nsmallest_data = data.nsmallest(2, 'cur_price')
    min1_data = nsmallest_data.iloc[0]
    min2_data = nsmallest_data.iloc[1]
    max1_data = nlargest_data.iloc[0]
    max2_data = nlargest_data.iloc[1]
    min_data = min1_data
    max_data = max1_data
    # min2 max2 max1 min1 排列形态，反画向下
    if min2_data.opened_mins < max2_data.opened_mins < min1_data.opened_mins and min2_data.opened_mins < max1_data.opened_mins < min1_data.opened_mins and abs(min1_data.cur_price - min2_data.cur_price) < 10:
        min_data = min2_data
    # max2 min2 min1 max1 排列形态，反画向上
    elif max2_data.opened_mins < min2_data.opened_mins < max1_data.opened_mins and max2_data.opened_mins < min1_data.opened_mins < max1_data.opened_mins and abs(max1_data.cur_price - max2_data.cur_price) < 10:
        max_data = max2_data
    min_index = min_data.name
    max_index = max_data.name
    golden_line = {'0': 0, '100': 0}
    if max_data.opened_mins > min_data.opened_mins:
        golden_line['0'] = min_data.cur_price
        for i in range(min_index, max_index): # 寻找100%的位置，需是最小值和最大值之间的拐点
            if i >= 4:
                cur_price = data.iloc[i - 2].cur_price
                if ((data.iloc[i - 3].cur_price < cur_price > data.iloc[i - 1].cur_price) and
                    # (cur_price > data.iloc[i].cur_price or cur_price - data.iloc[i - 1].cur_price >= 5) and
                    (cur_price - golden_line['0'] > conf['GOLDEN_LINE_DIFF'])):
                        golden_line['100'] = cur_price
                        golden_line = get_golden_line(golden_line)
                        if (max_data.cur_price <= golden_line['300']):
                            break
    else:
        golden_line['0'] = max_data.cur_price
        for i in range(max_index, min_index):
            if i >= 4:
                cur_price = data.iloc[i - 2].cur_price
                if ((data.iloc[i - 3].cur_price > cur_price < data.iloc[i - 1].cur_price) and
                    # (cur_price < data.iloc[i].cur_price or cur_price - data.iloc[i - 1].cur_price <= -5) and
                    (golden_line['0'] - cur_price > conf['GOLDEN_LINE_DIFF'])):
                        golden_line['100'] = cur_price
                        golden_line = get_golden_line(golden_line)
                        if (min_data.cur_price >= golden_line['300']):
                            break
    if golden_line['100'] == 0:
        return False
    return golden_line

def _check_golden_line(need_log=True):
    golden_line = draw_golden_line()
    if golden_line is False:
        log.info('golden_line not ready')
        glb['golden_line']['check_result'] = 'not_ready'
        return 'not_ready'
    draw_ma_line(need_log)
    cur_rt_data = glb['rt_data'].iloc[-1]
    cur_price = cur_rt_data.cur_price
    avg_price = cur_rt_data.avg_price
    check_result = ''
    if golden_line['100'] > golden_line['0']:
        if glb['MA10'] - glb['MA20'] > 10 and (cur_price > avg_price or cur_price < avg_price - 40):
            check_result = 'bull'
        elif glb['MA10'] - glb['MA20'] < 0:
            check_result = 'cancel_bull'
    else:
        if glb['MA10'] - glb['MA20'] < -10 and (cur_price < avg_price or cur_price > avg_price + 40):
            check_result = 'bear'
        elif glb['MA10'] - glb['MA20'] > 0:
            check_result = 'cancel_bear'
    glb['golden_line']['check_result'] = check_result
    if need_log:
        exclude_keys = {'261.8', '300'}
        filtered_obj = {k: v for k, v in glb['golden_line'].items() if k not in exclude_keys}
        log.info('cur_price: %s, avg_price: %s, golden_line: %s' % (cur_price, round(avg_price, 2), filtered_obj))
    return check_result


def get_order_book(code):
    ret, data = quote_ctx.get_order_book(code, num=3)
    log.info('get_order_book, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('get_order_book error')
        return False
    return data


def _smart_buy(code, volume, price=None, type='Bid'):
    if price is None:
        data = get_order_book(code)
        if not data:
            return False
        if conf['TRADE_ENV'] == ft.TrdEnv.SIMULATE:
            type = 'Ask'
        price = max(0.01, data[type][0 if type == 'Ask' else 1][0])
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.BUY, trd_env=conf['TRADE_ENV'])
    log.info('_smart_buy, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('code %s _smart_buy error, price %s, volume %s' % (code, price, volume))
        if '购买力不足' in data:
            conf['AUTO_BUY'] = False
        return False
    else:
        log.info('code %s _smart_buy success, price %s, volume %s' % (code, price, volume))
        return data


def _smart_sell(code, volume, price=None, type='Ask'):
    if price is None:
        data = get_order_book(code)
        if not data:
            return False
        price = max(0.01, data[type][0][0])
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.SELL, trd_env=conf['TRADE_ENV'])
    log.info('_smart_sell, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('code %s _smart_sell error, price %s, volume %s' % (code, price, volume))
        return False
    else:
        log.info('code %s _smart_sell success, price %s, volume %s' % (code, price, volume))
        return data


def _cancel_order(order_id):
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.CANCEL, order_id=order_id, price=0, qty=0, trd_env=conf['TRADE_ENV'])
    log.info('_cancel_order, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('_cancel_order error')
        return False
    else:
        log.info('_cancel_order success')
        return data


def _modify_order(order_id, price, qty):
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.NORMAL, order_id=order_id, price=price, qty=qty, trd_env=conf['TRADE_ENV'])
    log.info('modify_order, ret: %s, data:\n%s, order_id: %s, price: %s, qty: %s' % (ret, data, order_id, price, qty))
    if ret != ft.RET_OK:
        log.info('modify_order error')
        return False
    else:
        log.info('modify_order success')
        return data


def find_buy_price(order):
    buy_order = glb['filled_all_buy_order']
    if buy_order.get(order.order_id):
        return buy_order.get(order.order_id).get('price')
    else:
        data = order_list_query(order.code)
        if data is False or data is None:
            log.info('order_list_query data is False or data is None')
            return order.price
        filled_all_buy_data = data[((data.order_status == ft.OrderStatus.FILLED_ALL) | (data.order_status == ft.OrderStatus.CANCELLED_PART)) & (data.trd_side == ft.TrdSide.BUY)]
        if filled_all_buy_data.empty:
            log.info('error: filled_all_buy_data is empty')
            return order.price
        for index, row in filled_all_buy_data.iterrows():
            if buy_order.get(order.order_id) is None:
                buy_order[order.order_id] = {'create_time': row.create_time, 'price': row.price, 'code': row.code}
            else:
                if row.create_time > buy_order[order.order_id].get('create_time') and row.create_time <= order.get('create_time'):
                    buy_order[order.order_id] = {'create_time': row.create_time, 'price': row.price, 'code': row.code}
        log.info('filled_all_buy_order:\n%s' % buy_order)
        return buy_order.get(order.order_id).get('price')


def _order_list_query(code='', status_filter_list=[ft.OrderStatus.SUBMITTED, ft.OrderStatus.FILLED_PART, ft.OrderStatus.FILLED_ALL, ft.OrderStatus.CANCELLED_PART]):
    ret, data = trade_ctx.order_list_query(status_filter_list=status_filter_list, code=code, trd_env=conf['TRADE_ENV'], refresh_cache=True)
    # log.info('查询订单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('order_list_query error, code: %s' % code)
        return False
    log.info('order_list_query success, code: %s' % code)
    if ft.OrderStatus.FILLED_ALL in status_filter_list:
        last_order = glb['filled_all_last_order']
        filled_all_data = data[(data.order_status == ft.OrderStatus.FILLED_ALL) | (data.order_status == ft.OrderStatus.CANCELLED_PART)]
        if not filled_all_data.empty:
            last_data = filled_all_data[filled_all_data.updated_time == max(filled_all_data.updated_time)].iloc[0]
            last_order['last'] = {'updated_time': last_data.updated_time, 'price': last_data.price, 'trd_side': last_data.trd_side}
            for index, row in filled_all_data.iterrows():
                # code, updated_time, price = row.code, row.updated_time, row.price
                if row.code not in last_order:
                    last_order[row.code] = {'updated_time': row.updated_time, 'price': row.price, 'trd_side': row.trd_side}
                else:
                    if row.updated_time > last_order[row.code].get('updated_time'):
                        last_order[row.code] = {'updated_time': row.updated_time, 'price': row.price, 'trd_side': row.trd_side}
            log.info('filled_all_last_order:\n%s' % last_order)
        else:
            log.info('filled_all_data is empty')
    data = data[(data.order_status == ft.OrderStatus.SUBMITTED) | (data.order_status == ft.OrderStatus.FILLED_PART)]
    for i in range(0, len(data)):
        item = data.iloc[i]
        if item.trd_side == ft.TrdSide.BUY:
            set_submitted_buy(item.code, item.stock_name, item)
        elif item.trd_side == ft.TrdSide.SELL:
            set_submitted_sell(item.code, item.stock_name, item)
    if ft.OrderStatus.FILLED_ALL in status_filter_list:
        return filled_all_data
    return data


def _cancel_all(code='', trd_side='', stock_type=''):
    if code is None:
        return False
    if code == '' and stock_type == '' and trd_side == '':
        ret, data = trade_ctx.cancel_all_order(trd_env=conf['TRADE_ENV'])
        log.info('cancel_all_order, ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('cancel_all_order error')
    data = order_list_query(code, [ft.OrderStatus.SUBMITTED, ft.OrderStatus.FILLED_PART])
    if data is False:
        log.info('_cancel_all => order_list_query error')
        return False
    if data is None:
        log.info('_cancel_all => order_list_query throttling')
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            item = data.iloc[i]
            if stock_type == '':
                if trd_side == '':
                    cancel_order(item.order_id)
                elif trd_side == item.trd_side:
                    cancel_order(item.order_id)
            else:
                if CONST[stock_type] in item.stock_name and trd_side == '':
                    cancel_order(item.order_id)
                elif CONST[stock_type] in item.stock_name and trd_side == item.trd_side:
                    cancel_order(item.order_id)


# 买一价强制卖掉指定股票
def force_sell(code='', qty=''):
    data = smart_sell(code, qty, type='Bid')
    if data is False:
        log.info('force_sell => smart_sell error')
        return False
    if data is None:
        log.info('force_sell => smart_sell throttling')
        return False
    if len(data) > 0:
        data0 = data.iloc[0]
        if data0.order_status == ft.OrderStatus.FILLED_PART:
            log.info('FILLED_PART, modify_order price - 0.001')
            modify_order(data0.order_id, data0.price - 0.001, data0.qty)
        else:
            log.info('force_sell success')

# 卖掉指定的股票
def sell_all(code='', qty='', stock_type=''):
    if code != '':
        cancel_all(code)
        force_sell(code, qty)
        return True
    cancel_all(stock_type=stock_type) # 尽量调用撤销全部订单接口比较快
    data = _position_list_query(stock_type=stock_type)
    if data is False or data is None:
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            item = data.iloc[i]
            log.info('to sell all')
            if item.qty > item.can_sell_qty:
                cancel_all(item.code)
            force_sell(item.code, item.qty)


def subscribe(code_list, subtype_list, subscribe_push=True):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.subscribe(code_list, subtype_list, subscribe_push=subscribe_push)
    log.info('subscribe %s %s, ret: %s, data: %s' % (code_list, subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('subscribe %s %s error' % (code_list, subtype_list))
        return False
    else:
        return True


def unsubscribe(code_list, subtype_list):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.unsubscribe(code_list, subtype_list)
    log.info('unsubscribe %s %s, ret: %s, data: %s' % (code_list, subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('unsubscribe %s %s error' % (code_list, subtype_list))
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
    subscribe([code], [ft.SubType.ORDER_BOOK])


def reset_has(stock_name=''):
    if stock_name == '' or stock_name.find('牛') > -1:
        # if real:
        #     unsubscribe(glb['has_bull_list'], [ft.SubType.ORDER_BOOK])
        glb['has_bull_list'] = []
    if stock_name == '' or stock_name.find('熊') > -1:
        # if real:
        #     unsubscribe(glb['has_bear_list'], [ft.SubType.ORDER_BOOK])
        glb['has_bear_list'] = []


def set_submitted_buy(code, stock_name, data=None):
    if stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = True
        if data is not None:
            glb['submitted_buy_bull_data'] = data
        log.info('set_submitted_buy bull:%s' % code)
    elif stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = True
        if data is not None:
            glb['submitted_buy_bear_data'] = data
        log.info('set_submitted_buy bear: %s' % code)
    subscribe([code], [ft.SubType.ORDER_BOOK])


def reset_submitted_buy(code, stock_name=''):
    if stock_name == '' or stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = False
        glb['submitted_buy_bull_data'] = None
        log.info('reset_submitted_buy bull: %s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = False
        glb['submitted_buy_bear_data'] = None
        log.info('reset_submitted_buy bear: %s' % code)


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
        glb['submitted_sell_bull_data'] = glb['submitted_sell_bull_list'][-1]
        log.info('set_submitted_sell bull: %s, price: %s' % (code, data.price))
    elif stock_name.find('熊') > -1:
        append_data(glb['submitted_sell_bear_list'], 'order_id', data)
        glb['submitted_sell_bear_data'] = glb['submitted_sell_bear_list'][-1]
        log.info('set_submitted_sell bear: %s, price: %s' % (code, data.price))


def reset_submitted_sell(code, stock_name='', data=None):
    if stock_name == '' or stock_name.find('牛') > -1:
        del_data(glb['submitted_sell_bull_list'], 'order_id', data)
        if len(glb['submitted_sell_bull_list']) > 0:
            glb['submitted_sell_bull_data'] = glb['submitted_sell_bull_list'][-1]
        else:
            glb['submitted_sell_bull_data'] = None
        log.info('reset_submitted_sell bull: %s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        del_data(glb['submitted_sell_bear_list'], 'order_id', data)
        if len(glb['submitted_sell_bear_list']) > 0:
            glb['submitted_sell_bear_data'] = glb['submitted_sell_bear_list'][-1]
        else:
            glb['submitted_sell_bear_data'] = None
        log.info('reset_submitted_sell bear: %s' % code)


# 统计今日盈亏并止损
def sum_today_pl_val(today_buy_data):
    glb['today_pl_val_bull'] = 0
    glb['today_pl_val_bear'] = 0
    for i in range(0, len(today_buy_data)):
        item = today_buy_data.iloc[i]
        if item.stock_name.find('牛') > -1:
            glb['today_pl_val_bull'] += item.today_pl_val
        elif item.stock_name.find('熊') > -1:
            glb['today_pl_val_bear'] += item.today_pl_val
    log.info('MHI cur_price: %s, today bull: %s, today bear: %s' % (glb['cur_price'], glb['today_pl_val_bull'], glb['today_pl_val_bear']))
    # 止损
    has_sold = False
    loss_val = -(conf['BUY_VOLUME'] * conf['LOSS_PRICE_DIFF'] + (conf['MAX_VOLUME'] - conf['BUY_VOLUME']) * conf['ADD_PRICE_DIFF'])
    if glb['today_pl_val_bull'] <= loss_val and conf['BULL_CODE'] != '':
        conf['BULL_CODE'] = ''
        log.info('loss_val: %s' % loss_val)
        sell_all(stock_type='bull')
        has_sold = True
    if glb['today_pl_val_bear'] <= loss_val and conf['BEAR_CODE'] != '':
        conf['BEAR_CODE'] = ''
        log.info('loss_val: %s' % loss_val)
        sell_all(stock_type='bear')
        has_sold = True
    return has_sold


# 自动移仓
def auto_move_position(hsi_data):
    if not conf['AUTO_MOVE_POSITION']:
        return False
    hold_data = hsi_data[hsi_data.qty > 0]
    has_sold = False
    for i in range(0, len(hold_data)):
        item = hold_data.iloc[i]
        if round(item.nominal_price, 3) <= 0.021:
            log.info('code: %s, move_position, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
            glb['move_position'] = True
            subscribe([item.code], [ft.SubType.ORDER_BOOK]) # 有可能不是今天买的，所以可能没订阅
            sell_all(code=item.code, qty=item.qty)
            if item.stock_name.find('熊') > -1:
                to_buy('bear', volume=item.qty, force=True)
            elif item.stock_name.find('牛') > -1:
                to_buy('bull', volume=item.qty, force=True)
            has_sold = True
        elif conf['MOVE_POSITION_DICT']['from_code'] == item.code:
            conf['AUTO_MOVE_POSITION'] = False
            log.info('code: %s, move_position, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
            qty = min(item.qty, conf['MOVE_POSITION_DICT']['volume'])
            sell_all(code=item.code, qty=qty)
            if item.stock_name.find('熊') > -1:
                conf['BEAR_CODE'] = conf['MOVE_POSITION_DICT']['to_code']
                to_buy('bear', volume=qty, force=True, cur_price_min=conf['MOVE_POSITION_DICT']['cur_price_min'], cur_price_max=conf['MOVE_POSITION_DICT']['cur_price_max'])
            elif item.stock_name.find('牛') > -1:
                conf['BULL_CODE'] = conf['MOVE_POSITION_DICT']['to_code']
                to_buy('bull', volume=qty, force=True, cur_price_min=conf['MOVE_POSITION_DICT']['cur_price_min'], cur_price_max=conf['MOVE_POSITION_DICT']['cur_price_max'])
            has_sold = True
    return has_sold


def _position_list_query(stock_type='', need_log=True):
    ret, data = trade_ctx.position_list_query(trd_env=conf['TRADE_ENV'], refresh_cache=True)
    if need_log:
        log.info('position_list_query, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('position_list_query error, ret: %s, data:\n%s' % (ret, data))
        return False
    reset_has()
    hsi_data = data[data.stock_name.str.contains('恒指')]

    # 自动移仓
    if auto_move_position(hsi_data):
        return False

    # 统计今日盈亏并确定是否止损停止交易
    today_buy_data = hsi_data[(hsi_data.nominal_price < conf['CUR_PRICE_MAX']) & (hsi_data.today_buy_qty > 0) &
                    (hsi_data.qty == hsi_data.today_buy_qty - hsi_data.today_sell_qty)]
    if sum_today_pl_val(today_buy_data):
        return False

    today_buy_hold_data = today_buy_data[today_buy_data.qty > 0]
    if need_log:
        log.info('today_buy_hold_data:\n%s' % today_buy_hold_data)
    check_result = check_golden_line(need_log) or glb['golden_line']['check_result']
    if len(today_buy_hold_data) > 0:
        # has_sold = False
        for i in range(0, len(today_buy_hold_data)):
            item = today_buy_hold_data.iloc[i]
            set_has(item.code, item.stock_name)
            # 还有能挂单的量则重新挂单
            if item.can_sell_qty > 0 and conf['AUTO_PLACE_ORDER'] and not glb['to_over']:
                log.info('auto_place_order, code: %s, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
                auto_place_order(item.code, item.qty, max(item.nominal_price, item.cost_price), batch=not glb['almost_over'])

            if item.code not in glb['max_nominal_price']:
                glb['max_nominal_price'][item.code] = item.nominal_price
            elif item.nominal_price > glb['max_nominal_price'][item.code]:
                glb['max_nominal_price'][item.code] = item.nominal_price

            if item.code not in glb['loss']:
                glb['loss'][item.code] = False
            if glb['loss'].get(item.code):
                first_order_diff = 0.001
            else:
                first_order_diff = conf['FIRST_ORDER_DIFF']
            if item.stock_name.find('牛') > -1:
                if len(glb['submitted_sell_bull_list']) > 0 and item.nominal_price < round(glb['submitted_sell_bull_list'][0].price - first_order_diff, 3):
                    # 当前价格比买入后的最高价低3格的时候，重新挂单
                    if item.nominal_price < round(glb['max_nominal_price'][item.code] - conf['FIRST_ORDER_DIFF'], 3):
                        log.info('loss_order, code: %s, nominal_price: %s, max_nominal_price: %s' % (item.code, item.nominal_price, glb['max_nominal_price'][item.code]))
                        auto_place_order(item.code, item.qty, item.nominal_price, loss=True)
                elif conf['TRY_RECOVERY'] and (check_result == 'not_ready' or check_result == 'bear'):
                    log.info('sell_bull, code: %s, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
                    # sell_all(code=item.code, qty=item.qty)
                    # has_sold = True
                    # glb['loss'][item.code] = True
            elif item.stock_name.find('熊') > -1:
                if len(glb['submitted_sell_bear_list']) > 0 and item.nominal_price < round(glb['submitted_sell_bear_list'][0].price - first_order_diff, 3):
                    # 当前价格比买入后的最高价低3格的时候，重新挂单
                    if item.nominal_price < round(glb['max_nominal_price'][item.code] - conf['FIRST_ORDER_DIFF'], 3):
                        log.info('loss_order, code: %s, nominal_price: %s, max_nominal_price: %s' % (item.code, item.nominal_price, glb['max_nominal_price'][item.code]))
                        auto_place_order(item.code, item.qty, item.nominal_price, loss=True)
                elif conf['TRY_RECOVERY'] and (check_result == 'not_ready' or check_result == 'bull'):
                    log.info('sell_bear, code: %s, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
                    # sell_all(code=item.code, qty=item.qty)
                    # has_sold = True
                    # glb['loss'][item.code] = True
                # 分割线反画
                # if glb['golden_line']['reverse'] == 'bull':
                #     if '熊' in item.stock_name:
                #         log.info('reverse_loss, code: %s, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
                #         glb['loss'][item.code] = True
                # elif glb['golden_line']['reverse'] == 'bear':
                #     if '牛' in item.stock_name:
                #         log.info('reverse_loss, code: %s, nominal_price: %s, cost_price: %s' % (item.code, item.nominal_price, item.cost_price))
                #         glb['loss'][item.code] = True
        # if has_sold:
        #     return False
        bull_data = today_buy_hold_data[today_buy_hold_data.stock_name.str.contains('牛')]
        bear_data = today_buy_hold_data[today_buy_hold_data.stock_name.str.contains('熊')]
        if len(bull_data) == 0:
            reset_has('牛')
        if len(bear_data) == 0:
            reset_has('熊')
        if stock_type == 'bull':
            return bull_data
        elif stock_type == 'bear':
            return bear_data
        return today_buy_hold_data
    else:
        glb['max_nominal_price'] = {}
        glb['loss'] = {}
        reset_has()
        if glb['almost_over']:
            glb['over'] = True
            log.info('--------------------over--------------------')
        return []


class SysNotify(ft.SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------SysNotify push--------------------')
        ret, data = super(SysNotify, self).on_recv_rsp(rsp_pb)
        log.info('SysNotify push ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('SysNotify push error')
            return ret, data
        return ret, data


class OrderBook(ft.OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret, data = super(OrderBook, self).on_recv_rsp(rsp_str)
        # log.info('实时摆盘推送，ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('OrderBook push error，ret: %s, data:%s' % (ret, data))
            return ret, data
        glb['order_book'][data['code']] = data
        return ret, data


def auto_place_order(code, volume, price, batch=True, cancel=True, loss=False):
    if glb['auto_place_order_flag']:
        log.info('auto_place_order_flag True')
        return False
    if price > conf['CUR_PRICE_MAX']:
        return False
    first_order_price = price + conf['FIRST_ORDER_DIFF']
    if loss:
        glb['loss'][code] = True
        order_book = get_order_book(code)
        if order_book:
            first_order_price = order_book['Bid'][0][0]
        else:
            first_order_price = price - 0.001
    else:
        glb['loss'][code] = False
    if volume < 100e3:
        batch = False
    glb['auto_place_order_flag'] = True
    if cancel:
        cancel_all(code, trd_side=ft.TrdSide.SELL)
    if not batch:
        data = smart_sell(code, volume)
        if data is False:
            log.info('auto_place_order => smart_sell error')
        glb['auto_place_order_flag'] = False
        return
    item = []
    # [[600e3, 150e3, 150e3, 150e3, 150e3]]
    for i in range(0, len(conf['ORDER_LIST'])):
        if volume >= conf['ORDER_LIST'][i][0]:
            item = conf['ORDER_LIST'][i]
            break
    volume_diff = volume - item[0]
    if glb['move_position']:
        first_order_price += 0.02
    for i in range(1, len(item)): # 从1开始
        vol = item[i]
        if volume_diff > 0 and i == len(item) - 1:
            vol += volume_diff
        if vol == 0:
            continue
        data = smart_sell(code, vol, first_order_price + 0.001 * (i - 1))
        if data is False:
            log.info('auto_place_order => smart_sell error')
        elif glb['move_position']:
            glb['move_position'] = False
    glb['auto_place_order_flag'] = False


class TradeOrder(ft.TradeOrderHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------TradeOrder--------------------')
        ret, data = super(TradeOrder, self).on_recv_rsp(rsp_pb)
        log.info('TradeOrder ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('TradeOrder error')
            return ret, data
        data = data.iloc[0]
        if data.trd_env != conf['TRADE_ENV']:
            log.info('TradeOrder not TRADE_ENV')
            return ret, data
        log.info('TradeOrder trd_side: %s, order_status: %s' % (data.trd_side, data.order_status))
        if data.order_status == ft.OrderStatus.FILLED_ALL or data.order_status == ft.OrderStatus.CANCELLED_PART:
            glb['filled_all_last_order'][data.code] = {'updated_time': data.updated_time, 'price': data.price, 'trd_side': data.trd_side}
            glb['filled_all_last_order']['last'] = {'updated_time': data.updated_time, 'price': data.price, 'trd_side': data.trd_side}
            if data.trd_side == ft.TrdSide.BUY:
                glb['max_nominal_price'][data.code] = data.price
                reset_submitted_buy(data.code, data.stock_name)
                set_has(data.code, data.stock_name)
                if conf['AUTO_PLACE_ORDER'] and not glb['to_over']:
                    time.sleep(2)
                    auto_place_order(data.code, data.dealt_qty, data.price, cancel=False)
            elif data.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(data.code, data.stock_name, data)
                position_list_query()
        elif data.order_status == ft.OrderStatus.FILLED_PART:
            if data.trd_side == ft.TrdSide.BUY:
                set_has(data.code, data.stock_name)
        elif data.order_status == ft.OrderStatus.SUBMIT_FAILED or data.order_status == ft.OrderStatus.FAILED:
            position_list_query()
        elif data.order_status == ft.OrderStatus.CANCELLED_ALL:
            if data.trd_side == ft.TrdSide.BUY:
                reset_submitted_buy(data.code, data.stock_name)
            elif data.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(data.code, data.stock_name, data)
        elif data.order_status == ft.OrderStatus.SUBMITTED:
            if data.trd_side == ft.TrdSide.BUY:
                set_submitted_buy(data.code, data.stock_name, data)
            elif data.trd_side == ft.TrdSide.SELL:
                set_submitted_sell(data.code, data.stock_name, data)
        elif data.order_status == ft.OrderStatus.DISABLED:
            # 需要重新获取订单以重置一些全局变量
            order_list_query()

        return ret, data


def auto_adjust(delta_price, i, adjust_dict, submitted_type):
    data = glb[submitted_type]
    if data is None or data.code not in glb['order_book'] or (submitted_type.find('buy') > -1 and data.code not in glb['auto_buy_list']):
        return False
    order_book = glb['order_book'].get(data.code)
    bid_price = max(0.01, order_book['Bid'][0][0])
    ask_price = max(0.01, order_book['Ask'][0][0])
    if bid_price >= conf['CUR_PRICE_MAX']:
        return False
    rise_price = 0
    fall_price = 0
    if submitted_type.find('buy') > -1:
        rise_price = round(bid_price - (adjust_dict['rise'][2] - 1) * 0.001, 3)
        fall_price = max(0.01, round(bid_price - (adjust_dict['fall'][2] - 1) * 0.001, 3))
    elif submitted_type.find('sell') > -1:
        rise_price = round(ask_price + (adjust_dict['rise'][2] - 1) * 0.001, 3)
        # 尾盘才降价到卖一
        if glb['almost_over']:
            fall_price = round(ask_price + (adjust_dict['fall'][2] - 1) * 0.001, 3)
        else:
            fall_price = round(max(find_buy_price(data) + conf['LAST_ORDER_DIFF'], ask_price - 0.001), 3)
    rise_condition = False
    fall_condition = False
    if submitted_type.find('bull') > -1:
        rise_condition = delta_price >= adjust_dict['rise'][1]
        fall_condition = delta_price <= -adjust_dict['fall'][1]
    elif submitted_type.find('bear') > -1:
        rise_condition = delta_price <= -adjust_dict['rise'][1]
        fall_condition = delta_price >= adjust_dict['fall'][1]
    # 买单可升可降，卖单在尾盘只降不升
    if rise_condition:
        if submitted_type.find('buy') > -1 or not glb['almost_over']:
            delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['adjust_ticker_list'][i].get('time'))
            if delta_seconds <= adjust_dict['rise'][0] and data.price < rise_price:
                log.info('%s order price: %s, rise_price: %s' % (submitted_type, data.price, rise_price))
                modify_order(data.order_id, rise_price, data.qty)
    elif fall_condition:
        delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['adjust_ticker_list'][i].get('time'))
        if delta_seconds <= adjust_dict['fall'][0] and data.price > fall_price:
            log.info('%s order price: %s, fall_price: %s' % (submitted_type, data.price, fall_price))
            modify_order(data.order_id, fall_price, data.qty)


def pre_adjust():
    # conf['ADJUST_BUY_DICT'] = {
    #     'rise': [2, 3, 1],                              # 最近多少秒内，往持仓股票方向波动多少点，调整买单为第几档
    #     'fall': [2, 3, 2]                               # 最近多少秒内，往持仓股票反向波动多少点，调整买单为第几档
    # }
    while datestr_to_timestamp(glb['adjust_ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['adjust_ticker_list'][0].get('time')) > conf['MAX_ADJUST_DELTA_SECONDS']:
        glb['adjust_ticker_list'].pop(0)
    # i 从逐笔列表的倒数第二项开始，依次递减1，直到0为止，要遍历的前提是预设的多少秒内是不统一的
    # for i in range(len(glb['adjust_ticker_list']) - 2, -1, -1):
    i = 0
    delta_price = glb['adjust_ticker_list'][-1].get('price') - glb['adjust_ticker_list'][i].get('price')
    # if delta_price > MAX_ADJUST_DELTA_PRICE:
    #     break
    if conf['AUTO_ADJUST_BUY']:
        auto_adjust(delta_price, i, conf['ADJUST_BUY_DICT'], 'submitted_buy_bear_data')
        auto_adjust(delta_price, i, conf['ADJUST_BUY_DICT'], 'submitted_buy_bull_data')
    if conf['AUTO_ADJUST_SELL']:
        auto_adjust(delta_price, i, conf['ADJUST_SELL_DICT'], 'submitted_sell_bear_data')
        auto_adjust(delta_price, i, conf['ADJUST_SELL_DICT'], 'submitted_sell_bull_data')


def _get_stock_code(stock_type='all', cache_first=False, cur_price_min=None, cur_price_max=None):
    cache = glb['cache_get_stock_code'].get(stock_type)
    if cache_first and cache['data'] is not None and time.time() - cache['last_time'] < cache['duration']:
        log.info('读取缓存数据：%s' % cache)
        return cache['data']
    cache['data'] = False

    req = ft.WarrantRequest()
    req.stock_owner = CONST['HSI_CODE']  # 所属正股
    if stock_type == 'bull':
        req.type_list = [ft.WrtType.BULL]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    elif stock_type == 'bear':
        req.type_list = [ft.WrtType.BEAR]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    # req.issuer_list = [ft.Issuer.JP]  # Qot_Common.Issuer, 发行人过滤列表
    req.status = ft.WarrantStatus.NORMAL  # Qot_Common.WarrantStatus, 窝轮状态
    req.cur_price_min = cur_price_min or conf['CUR_PRICE_MIN']  # 最新价过滤起点
    req.cur_price_max = cur_price_max or conf['CUR_PRICE_MAX']  # 最新价过滤终点
    req.conversion_min = 10000  # 换股比率过滤起点
    req.conversion_max = 10000  # 换股比率过滤终点
    req.vol_min = 1000  # 成交量的过滤下限，单位K
    req.sort_field = ft.SortField.VOLUME  # 根据哪个字段排序
    req.ascend = False  # 升序ture, 降序false
    req.begin = 0  # 数据起始点
    req.num = 20 if cur_price_min == 0.01 else 3  # 返回数据个数，最大200

    ret, data = quote_ctx.get_warrant(req=req)
    # log.info('get_warrant, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('get_warrant error')
    else:
        data = data[0]
        # FUTU BUG: 返回的结果还要再过滤一次
        data = data[(data.stock_owner == CONST['HSI_CODE']) & (data.status == ft.WarrantStatus.NORMAL)]
        data = data[data.bid_price >= 0.01]
        if len(data) > 0:
            if conf['TRY_RECOVERY'] and cur_price_min == 0.01:
                rt_data = get_rt_data()
                if rt_data is False:
                    return False
                cur_rt_data = rt_data.iloc[-1]
                intrinsic_price = round(abs(cur_rt_data.cur_price - data['strike_price']) / data.conversion_ratio, 3)
                data.insert(loc=data.columns.get_loc('ask_price') + 1, column='intrinsic_price', value=intrinsic_price)
                data.insert(loc=data.columns.get_loc('intrinsic_price') + 1, column='ibp_diff', value=data.intrinsic_price - data.bid_price)
                data = data.sort_values(by='ibp_diff', ascending=False)
                log.info('ibp_diff, data:\n%s' % data)
                data = data.iloc[0]
                if data.ibp_diff >= 0.009:
                    log.info('ibp_diff allow buy, code: %s, bid_price: %s, ask_price: %s, intrinsic_price: %s' % (data.stock, data.bid_price, data.ask_price, data.intrinsic_price))
                    cache['data'] = data
                else:
                    log.info('ibp_diff not allow buy, code: %s, bid_price: %s, ask_price: %s, intrinsic_price: %s' % (data.stock, data.bid_price, data.ask_price, data.intrinsic_price))
            else:
                cache['data'] = data.iloc[0]
        else:
            log.info('_get_stock_code error, conditions not met')
    cache['last_time'] = time.time()
    return cache['data']


def to_buy(stock_type, code='', volume=None, force=False, cur_price_min=None, cur_price_max=None):
    if glb['soon_over']:
        return False
    log.info('to buy %s' % stock_type)
    if volume is None:
        volume = conf['BUY_VOLUME']
        if glb['afternoon']:
            volume /= 2
    if code == '':
        if stock_type == 'bull':
            code = conf['BULL_CODE']
        elif stock_type == 'bear':
            code = conf['BEAR_CODE']
        else:
            code = 'auto'
    if code == '':
        return False

    if force is False:
        data = position_list_query(stock_type=stock_type, need_log=False)
        if data is False or data is None:
            return False
        if len(data) > 0:
            data0 = data.iloc[0]
            total_qty = sum(data.qty)
            if total_qty + volume > conf['MAX_VOLUME']:
                if conf['MAX_VOLUME'] - total_qty >= 100e3:
                    volume = math.floor((conf['MAX_VOLUME'] - total_qty) / 100e3) * 100e3
                    log.info('current total_qty: %s, MAX_VOLUME: %s, can only buy %s' % (total_qty, conf['MAX_VOLUME'], volume))
                else:
                    log.info('current total_qty: %s, MAX_VOLUME: %s, not allow add' % (total_qty, conf['MAX_VOLUME']))
                    return False
            if total_qty > 0:
                if not conf['ALLOW_ADD']:
                    log.info('not allow add')
                    return False
                reference_price = glb['filled_all_last_order'].get(data0.code, {}).get('price')
                if not reference_price:
                    log.info('code: %s, no filled_all_last_order，\n%s' % (data0.code, glb['filled_all_last_order']))
                    reference_price = data0.cost_price
                add_price_diff = round(reference_price - data0.nominal_price, 3)
                if add_price_diff < conf['ADD_PRICE_DIFF']:
                    log.info('code: %s, nominal_price: %s, reference_price: %s, diff: %s < %s, not allow add' % (data0.code, data0.nominal_price, reference_price, add_price_diff, conf['ADD_PRICE_DIFF']))
                    return False
                log.info('code: %s, nominal_price: %s, reference_price: %s, diff: %s >= %s, allow add' % (data0.code, data0.nominal_price, reference_price, add_price_diff, conf['ADD_PRICE_DIFF']))

    if code == 'auto':
        data = get_stock_code(stock_type=stock_type, cur_price_min=cur_price_min, cur_price_max=cur_price_max)
        if data is False or data is None:
            return False
        code = data.stock
        if '牛' in data['name']: # 必须用中括号，data.name会访问到name属性而不是列
            stock_type = 'bull'
        elif '熊' in data['name']:
            stock_type = 'bear'

    set_submitted_buy(code, CONST[stock_type])
    if force:
        data = smart_buy(code, volume, type='Ask')
    else:
        data = smart_buy(code, volume)
    if data is False or data is None:
        reset_submitted_buy(code, CONST[stock_type])
    else:
        add_unique_element(glb['auto_buy_list'], code)
    return data


def auto_buy(stock_type):
    # log.info('auto_buy stock_type: %s' % stock_type)
    if stock_type == 'bull' and not glb['submitted_buy_bull_flag'] and (conf['ALLOW_ADD'] or len(glb['has_bull_list']) == 0):
        if conf['BULL_CODE'] == '':
            return False
        check_result = check_golden_line(need_log=False) or glb['golden_line']['check_result']
        if check_result == 'bull':
            to_buy('bull')
        elif conf['TRY_RECOVERY'] and check_result == 'not_ready':
            to_buy('bull', cur_price_min=0.01, cur_price_max=0.018)
    elif stock_type == 'bear' and not glb['submitted_buy_bear_flag'] and (conf['ALLOW_ADD'] or len(glb['has_bear_list']) == 0):
        if conf['BEAR_CODE'] == '':
            return False
        check_result = check_golden_line(need_log=False) or glb['golden_line']['check_result']
        if check_result == 'bear':
            to_buy('bear')
        elif conf['TRY_RECOVERY'] and check_result == 'not_ready':
            to_buy('bear', cur_price_min=0.01, cur_price_max=0.018)


def get_submitted_code(submitted_type):
    # 必须判断值是否为None，如果用get方法的第二个参数是不会判断的
    if submitted_type in glb and glb[submitted_type] is not None:
        return glb[submitted_type].get('code')
    else:
        return None


def pre_buy():
    if glb['kline_data'] is None:
        return False
    #       code              time                 price        volume  turnover    ticker_direction       sequence   type      push_data_type
    # 0     HK_FUTURE.999010  2019-03-01 00:59:55  28655.0       1   28655.0              BUY  6663097136416030721  AUTO_MATCH          CACHE
    while datestr_to_timestamp(glb['ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['ticker_list'][0].get('time')) > conf['DELTA_SECONDS']:
        glb['ticker_list'].pop(0)
    cur_seconds = glb['ticker_list'][-1].get('time').split('.')[0][-2:]
    if cur_seconds != '59' and cur_seconds != '00' and cur_seconds != '01':
        return False
    # 上一单成交1分钟后才考虑买
    # filled_all_last_order_time = glb['filled_all_last_order'].get('last', {}).get('updated_time')
    # if filled_all_last_order_time:
    #     delta_seconds = datestr_to_timestamp(glb['ticker_list'][-1].get('time')) - datestr_to_timestamp(filled_all_last_order_time)
    #     if delta_seconds <= conf['DELTA_SECONDS']:
    #         log.info('pre_buy delta_seconds: %s' % delta_seconds)
    #         return False
    delta_price = glb['ticker_list'][-1].get('price') - glb['ticker_list'][0].get('price')
    # log.info('pre_buy delta_price: %s' % delta_price)

    max_price = glb['kline_data'].iloc[-30:]['close'].max()
    min_price = glb['kline_data'].iloc[-30:]['close'].min()
    if abs(delta_price) >= conf['FOLLOW_TREND_PRICE']:
        conf['FOLLOW_TREND'] = True
        if delta_price >= conf['FOLLOW_TREND_PRICE'] and max_price - glb['cur_price'] > 20:
            auto_buy('bull')
            cancel_all(get_submitted_code('submitted_buy_bear_data'))
        elif delta_price <= -conf['FOLLOW_TREND_PRICE'] and glb['cur_price'] - min_price > 20:
            auto_buy('bear')
            cancel_all(get_submitted_code('submitted_buy_bull_data'))
    else:
        conf['FOLLOW_TREND'] = False
        if conf['DELTA_PRICE_MIN'] <= delta_price <= conf['DELTA_PRICE_MAX'] and (conf['BIG-ONE-WAY'] or glb['cur_price'] - min_price > 15):
            auto_buy('bear')
        elif -conf['DELTA_PRICE_MIN'] >= delta_price >= -conf['DELTA_PRICE_MAX'] and (conf['BIG-ONE-WAY'] or max_price - glb['cur_price'] > 15):
            auto_buy('bull')
        elif delta_price > conf['DELTA_PRICE_MAX'] and get_submitted_code('submitted_buy_bear_data'):
            cancel_all(get_submitted_code('submitted_buy_bear_data'))
            log.info('cancel_all bear, delta_price: %s' % delta_price)
        elif delta_price < -conf['DELTA_PRICE_MAX'] and get_submitted_code('submitted_buy_bull_data'):
            cancel_all(get_submitted_code('submitted_buy_bull_data'))
            log.info('cancel_all bull, delta_price: %s' % delta_price)


# class RTData(ft.RTDataHandlerBase):
#     def on_recv_rsp(self, rsp_str):
#         # log.info('--------------------分时推送--------------------')
#         ret, data = super(RTData, self).on_recv_rsp(rsp_str)
#         if ret != ft.RET_OK:
#             log.info('RTData push error，ret: %s, data:%s' % (ret, data))
#             return ret, data
#         #       code                 time  is_blank  opened_mins  cur_price  last_close     avg_price  volume      turnover
#         # 0    HK.800000  2023-10-31 09:30:00     False          570   17337.70    17406.36  17337.700000       0  1.682861e+09

#         cur_data = data.iloc[-1]

#         return ret, data


class Ticker(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_str):
        # log.info('--------------------逐笔明细--------------------')
        ret, data = super(Ticker, self).on_recv_rsp(rsp_str)
        if ret != ft.RET_OK:
            log.info('Ticker push error，ret: %s, data:%s' % (ret, data))
            return ret, data
        #       code              time                 price        volume  turnover    ticker_direction       sequence   type      push_data_type
        # 0     HK_FUTURE.999010  2019-03-01 00:59:55  28655.0       1   28655.0              BUY  6663097136416030721  AUTO_MATCH          CACHE
        # ret, data = (0, {'code': ['HK_FUTURE.999010', 'HK_FUTURE.999011'],
        # 'time': ['2019-03-01 09:59:55', '2019-03-01 09:59:59'],
        # 'price': [28655.0, 28655.0],
        # 'volume': [1, 1],
        # 'turnover': [28655.0, 28655.0],
        # 'ticker_direction': ['BUY', 'BUY'],
        # 'sequence': [6663097136416030721, 6663097136416030721],
        # 'type': ['AUTO_MATCH', 'AUTO_MATCH'],
        # 'push_data_type': ['CACHE', 'CACHE']})
        # data = pd.DataFrame(data)

        data0 = data.iloc[0]
        # log.info('ticker push, data:\n%s' % data0)
        t = data0.time
        h = int(t[11:13])
        m = int(t[14:16])
        s = int(t[17:19])
        if h < 9 or h == 9 and m < 30 or h >= 16:
            # print(data)
            if h == 16 and m == 0 and s == 0:
                log.info('[%s]--------------------end--------------------' % t)
            return ret, data

        if h == 9 and m == 30 and s == 0:
            log.info('[%s]--------------------start--------------------' % t)
        elif h >= 15 and not glb['afternoon']:
            glb['afternoon'] = True

        if glb['trade_date'].get('trade_date_type') == 'MORNING' and h == 11 or h == 15:
            if m >= 30:
                glb['soon_over'] = True
            if m >= 55:
                if not glb['almost_over']:
                    glb['almost_over'] = True
                    cancel_all()
                    position_list_query()
                if m >= 59:
                    if not glb['to_over']:
                        glb['to_over'] = True
                        log.info('[%s]--------------------to_over--------------------' % t)
                        if not glb['over']:
                            if conf['BULL_CODE'] != '' and conf['BEAR_CODE'] != '':
                                sell_all()
                            elif conf['BULL_CODE'] != '':
                                sell_all(stock_type='bull')
                            elif conf['BEAR_CODE'] != '':
                                sell_all(stock_type='bear')
                return ret, data

        if glb['to_over']:
            return ret, data

        glb['cur_price'] = data0.price

        # 每波动10点查询持仓列表，方便统计盈亏和止损
        if abs(glb['cur_price'] - glb['last_price']) >= 10:
            glb['last_price'] = glb['cur_price']
            position_list_query(need_log=False)
        # 每10秒查询分割线，方便撤单和止损
        if s % 10 == 0:
            check_result = check_golden_line(need_log=True if s == 0 else False) or glb['golden_line']['check_result']
            if glb['submitted_buy_bull_data'] is not None and glb['submitted_buy_bull_data'].price > 0.02 and check_result == 'cancel_bull':
                cancel_all(glb['submitted_buy_bull_data'].code)
                log.info('cancel_all bull, check_result: %s' % check_result)
            elif glb['submitted_buy_bear_data'] is not None and glb['submitted_buy_bear_data'].price > 0.02 and check_result == 'cancel_bear':
                cancel_all(glb['submitted_buy_bear_data'].code)
                log.info('cancel_all bear, check_result: %s' % check_result)
            # 每分钟查询持仓列表
            if s == 0:
                position_list_query()

        # 自动买入和自动调价
        if conf['AUTO_BUY'] or conf['AUTO_ADJUST']:
            for index, row in data.iterrows():
                if conf['AUTO_BUY'] and not glb['soon_over']:
                    glb['ticker_list'].append(row)
                if conf['AUTO_ADJUST']:
                    glb['adjust_ticker_list'].append(row)
            # 尾盘就不买了
            if conf['AUTO_BUY'] and not glb['soon_over']:
                pre_buy()
            # 自动调价
            if conf['AUTO_ADJUST']:
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
    log.info('request_trading_days, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('request_trading_days error')
        return False
    if len(data) == 0 or data[0]['time'] != today.strftime('%Y-%m-%d'):
        log.info('not trading day')
        return False
    glb['trade_date'] = data[0]
    return glb['trade_date']


# 重置数据
def resetData():
    log.info('--------------------resetData--------------------')
    glb['afternoon'] = False
    glb['soon_over'] = False
    glb['almost_over'] = False
    glb['to_over'] = False
    glb['over'] = False
    request_trading_days()


# 限制2秒内最多查1次足够
# pre_buy = throttle(_pre_buy, 2, False)
# 限制3秒内最多查1次足够
check_golden_line = throttle(_check_golden_line, 3, False)
# 每 30 秒内最多请求 10 次查询持仓接口
position_list_query = throttle(_position_list_query, 3)
# 每 30 秒内最多请求 15 次下单接口，且连续两次请求的间隔不可小于 0.02 秒
smart_buy = throttle(_smart_buy, 2)
smart_sell = delay_execution(_smart_sell, 2) # 自动挂卖单是遍历的，所以不能节流，只能延时
# 每 30 秒内最多请求 60 次筛选窝轮接口
get_stock_code = throttle(_get_stock_code, 0.5)
# 每 30 秒内最多请求 10 次查询今日订单接口
order_list_query = throttle(_order_list_query, 3)
# 每 30 秒内最多请求 20 次改单撤单接口，且连续两次请求的间隔不可小于 0.04 秒
modify_order = delay_execution(_modify_order, 1.5) # 自动调价要连续执行，所以不能节流，只能延时
cancel_order = delay_execution(_cancel_order, 1.5) # 撤销订单是遍历的，所以不能节流，只能延时
cancel_all = delay_execution(_cancel_all, 1.5) # 撤销全部订单也是遍历的，所以不能节流，只能延时


def set_config(config):
    global conf
    conf.update(config)
    conf['MAX_ADJUST_DELTA_SECONDS'] = max(conf['ADJUST_BUY_DICT']['rise'][0], conf['ADJUST_BUY_DICT']['fall'][0], conf['ADJUST_SELL_DICT']['rise'][0], conf['ADJUST_SELL_DICT']['fall'][0])
    # MAX_ADJUST_DELTA_PRICE = max(conf['ADJUST_BUY_DICT']['rise'][1], conf['ADJUST_BUY_DICT']['fall'][1], conf['ADJUST_SELL_DICT']['rise'][1], conf['ADJUST_SELL_DICT']['fall'][1])

    if conf['TRADE_ENV'] == ft.TrdEnv.SIMULATE:
        conf['AUTO_BUY'] = True                         # 模拟盘强制开启自动买入
        conf['AUTO_ADJUST_BUY'] = False                 # 模拟盘强制关闭自动调价买单


def start(config=None):
    time.sleep(3)
    global log, quote_ctx, trade_ctx
    if config is not None:
        set_config(config)
    ft.set_futu_debug_model(False)
    log = Logger(conf['log_file']).get_logger()
    temp_quote_ctx = None
    temp_trade_ctx = None
    if quote_ctx is not None:
        temp_quote_ctx = quote_ctx
        temp_trade_ctx = trade_ctx
        log.info('restart new')
    quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
    trade_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.HK, host=conf['HOST'], port=conf['PORT'])
    resetData()
    if conf['TRADE_ENV'] == ft.TrdEnv.REAL:
        ret, data = trade_ctx.unlock_trade(password_md5=conf['PASSWORD_MD5'], password=conf['PASSWORD'])
        log.info('unlock_trade, ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('unlock_trade error')
            return False
    data = subscribe([CONST['HSI_CODE']], [ft.SubType.RT_DATA], subscribe_push=False)
    if data is False:
        return False
    data = subscribe([CONST['MHI_CODE']], [ft.SubType.TICKER])
    if data is False:
        return False
    data = subscribe([CONST['MHI_CODE']], [ft.SubType.K_1M], subscribe_push=False)
    if data is False:
        return False
    quote_ctx.set_handler(SysNotify())
    quote_ctx.set_handler(Ticker())
    trade_ctx.set_handler(TradeOrder())
    if conf['AUTO_ADJUST']:
        quote_ctx.set_handler(OrderBook())
    position_list_query()
    order_list_query()
    # get_stock_code(cur_price_min=0.01, cur_price_max=0.018)

    ret, data = quote_ctx.query_subscription()
    log.info('query_subscription, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('query_subscription error')
    quote_ctx.start()

    # ticker = Ticker()
    # ticker.on_recv_rsp()

    if temp_quote_ctx is not None:
        temp_quote_ctx.close()
        temp_trade_ctx.close()
        log.info('restart success')

