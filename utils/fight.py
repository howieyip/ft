# -*- coding: utf-8 -*-
import time
import datetime
import math
import futu as ft
from utils.logger import Logger
from utils.timer import Timer
import pandas as pd
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)


# 配置
conf = {
    'log_file': 'logs/fight',
    'TRADE_ENV': ft.TrdEnv.REAL,                          # 实盘交易：REAL，模拟交易：SIMULATE
    'PASSWORD_MD5': '',                                   # 优先使用 PASSWORD_MD5 解锁
    'PASSWORD': '',                                       # 如果PASSWORD_MD5为空，则使用 PASSWORD 解锁
    'HOST': '127.0.0.1',
    'PORT': 11111,
    'acc_id': 0,

    'exclude_code_list': [],
    'AUTO_BUY': False,                              # 是否自动买入，若是则下面的配置有效
    'TRY_RECOVERY': False,                          # 是否买快回收的且价格比正常低很多的股票
    'TRY_FOLLOW_RECOVERY': False,                   # 是否顺势买快回收的反方向的股票
    'BULL_CODE': '',                                # 自动买入牛证的股票代码，格式HK.00700，填auto则会自动选股
    'LONG_BULL_CODE': '',
    'BEAR_CODE': '',                                # 自动买入熊证的股票代码，格式HK.00700，填auto则会自动选股
    'CUR_PRICE_MIN': 0.1,
    'CUR_PRICE_MAX': 0.2,                          # 这个值非常重要，当天买入的新股票如果低于这个价，会被当成是日内短炒

    'BUY_VOLUME': 100e3,                            # 下单多少股
    'MAX_VOLUME': 1000e3,                            # 最大持仓股数，若超过则不会再买入

    'AUTO_ADJUST_BUY': True,                        # 是否自动调整挂的买单的价格
    'AUTO_ADJUST_SELL': True,                       # 是否自动调整挂的卖单的价格

    'ALLOW_ADD': True,                              # 是否允许补仓，若是则下面的ADD_PRICE_DIFF有效
    'ADD_PRICE_DIFF': 0.004,                        # 持仓股票的现价与最近一次成交价的价差大于等于多少元，才允许补仓
    'AUTO_PLACE_ORDER': True,                       # 买入后是否自动挂单分批卖出，若是则下面的ORDER_LIST有效
    'ORDER_LIST': [                                 # 下单多少股以上（大的写前面），每单挂多少股，例如下单800k，分3档200k 200k 400k挂单
        [800e3, 200e3, 200e3, 200e3, 200e3],
        [700e3, 200e3, 200e3, 200e3, 100e3],
        [600e3, 200e3, 200e3, 100e3, 100e3],
        [500e3, 200e3, 100e3, 100e3, 100e3],
        [400e3, 100e3, 100e3, 100e3, 100e3],
        [300e3, 100e3, 100e3, 50e3, 50e3],
        [200e3, 50e3, 50e3, 50e3, 50e3],
        [100e3, 50e3, 50e3]
    ],
    'ADD_ORDER_LIST': [                             # 补仓的订单
        [400e3, 200e3, 200e3],
        [200e3, 100e3, 100e3],
        [100e3, 50e3, 50e3]
    ],
    'FIRST_ORDER_DIFF': 0.006,                      # 第一个卖单间隔多少
    'EVERY_ORDER_DIFF': 0.006,                      # 每个卖单间隔多少
    'NEED_LOSS': True,
    'LOSS_PRICE_DIFF': 0.006,                       # 卖一价距离买入后的最高价达到多少就止损
    'sell_all_to_over': False,                      # 尾盘清仓，只对日内短炒的生效，False时只有盈利时才清仓

    'AUTO_MOVE_POSITION': False,                    # 是否自动强制移仓，是则下面的MOVE_POSITION_DICT生效
    'MOVE_POSITION_DICT': {
        'from_code': 'HK.',                         # 指定code移仓目前是一次性应急用
        'to_code': 'auto',
        'volume': 400e3,
        'cur_price_min': 0.23,
        'cur_price_max': 0.25
    },
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
    'timer': None,
    'recovery_bull': None,
    'recovery_bear': None,
    'rt_data': None,
    'line': {},
    'golden_line': {},
    'loss': {},
    'today_pl_val_bull': 0,
    'today_pl_val_bear': 0,
    'trade_date': {},
    'afternoon': False,
    'soon_over': False,
    'almost_over': False,
    'to_over': False,
    'over': False,
    'cur_price': 0,
    'last_price': 0,
    'last_3s_price': 0,
    'klines': None,
    'max_nominal_price': {},
    'filled_all_last_order': {},
    'filled_all_buy_order': {},
    'submitted_buy_bull_flag': False,
    'submitted_buy_bear_flag': False,
    'submitted_buy_last_bull': None,
    'submitted_buy_last_bear': None,
    'submitted_sell_last_bull': None,
    'submitted_sell_last_bear': None,
    'submitted_sell_orders': {},
    'order_book': {},
    'auto_buy_list': [],
    'past_hold_code_list': [],
    'today_hold_code_list': [],
    'today_hold_bull_list': [],
    'today_hold_bear_list': [],
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
            caller = kwargs.get('caller', '')
            log.info(f'{fn.__name__} caller {caller} throttling, {countdown}s remaining')
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


def get_cur_kline(num=80, begin=None):
    ret, klines = quote_ctx.get_cur_kline(CONST['MHI_CODE'], num, ft.KLType.K_1M)
    # log.info('get_cur_kline, ret: %s, klines:%s' % (ret, klines))
    if ret != ft.RET_OK:
        log.info('get_cur_kline error, ret: %s, klines:\n%s' % (ret, klines))
        return False
    #            code         name             time_key     open    close     high      low  volume  turnover  pe_ratio  turnover_rate  last_close
    # 0   HK.MHImain  小恒指主连(2406)  2024-06-15 02:42:00  17773.0  17772.0  17773.0  17769.0      18  319883.0       0.0            0.0     17772.0
    # 1   HK.MHImain  小恒指主连(2406)  2024-06-15 02:43:00  17775.0  17776.0  17776.0  17775.0       8  142205.0       0.0            0.0     17772.0
    # 18  HK.MHImain  小恒指主连(2406)  2024-06-15 03:00:00  17796.0  17796.0  17796.0  17793.0      30  533842.0       0.0            0.0     17795.0
    # 19  HK.MHImain  小恒指主连(2406)  2024-06-17 09:16:00  17796.0  17796.0  17796.0  17796.0       0       0.0       0.0            0.0     17796.0
    glb['klines'] = klines
    if begin is not None:
        klines = klines[klines.time_key.str[11:19] > begin]
        klines = klines[-num:].reset_index(drop=True)
    return klines


def boll_bands(klines):
    mid = round(klines['close'].mean(), 3)
    std = klines['close'].std(ddof=0)
    upper = round(mid + 2 * std, 3)
    lower = round(mid - 2 * std, 3)
    return {'mid': mid, 'upper': upper, 'lower': lower}


def draw_line():
    klines = get_cur_kline(80)
    if klines is False or len(klines) < 20:
        log.info('draw_line error, klines:\n%s' % klines)
        return False, False
    line = glb['line']
    line['cur'] = klines.iloc[-1].close
    # line['10'] = round(klines[-10:]['close'].mean(), 3)
    line['long'] = round(klines[-80:]['close'].mean(), 3)
    # line['long2'] = round(klines[-81:-1]['close'].mean(), 3)
    last_boll_bands = boll_bands(klines[-20:])
    last2_boll_bands = boll_bands(klines[-21:-1])
    last3_boll_bands = boll_bands(klines[-22:-2])
    line['mid'] = last_boll_bands['mid']
    line['upper'] = last_boll_bands['upper']
    line['lower'] = last_boll_bands['lower']
    # line['mid2'] = last2_boll_bands['mid']
    line['upper2'] = last2_boll_bands['upper']
    line['lower2'] = last2_boll_bands['lower']
    # line['mid3'] = last3_boll_bands['mid']
    line['upper3'] = last3_boll_bands['upper']
    line['lower3'] = last3_boll_bands['lower']
    log.info('draw_line: %s' % line)
    return klines, line


def get_golden_line(line):
    diff = round(line['100'] - line['0'], 2)
    for i in range(0, 2):
        line[str(i*100 + 23.6)] = round(line['0'] + diff * (0.236 + i), 2)
        line[str(i*100 + 38.2)] = round(line['0'] + diff * (0.382 + i), 2)
        line[str(i*100 + 50)] = round(line['0'] + diff * (0.50 + i), 2)
        line[str(i*100 + 61.8)] = round(line['0'] + diff * (0.618 + i), 2)
        line[str(i*100 + 76.4)] = round(line['0'] + diff * (0.764 + i), 2)
        line[str(i*100 + 100)] = round(line['0'] + diff * (1 + i), 2)
    return line


def draw_golden_line():
    klines = get_cur_kline(331, '09:15:00')
    if klines is False or len(klines) < 20:
        return False
    max_data = klines.nlargest(1, 'high').iloc[0]
    min_data = klines.nsmallest(1, 'low').iloc[0]
    golden_line_diff = 80
    golden_line = glb['golden_line']
    golden_line['0'] = 0
    golden_line['100'] = 0
    if max_data.time_key > min_data.time_key:
        golden_line['0'] = min_data.low
        for i in range(min_data.name + 1, len(klines) - 1):
            max_price = klines.iloc[i].high
            if klines.iloc[i - 1].high < max_price > klines.iloc[i + 1].high and max_price - golden_line['0'] > golden_line_diff:
                golden_line['100'] = max_price
                golden_line = get_golden_line(golden_line)
                if max_data.close <= golden_line['200']:
                    break
    else:
        golden_line['0'] = max_data.high
        for i in range(max_data.name + 1, len(klines) - 1):
            min_price = klines.iloc[i].low
            if klines.iloc[i - 1].low > min_price < klines.iloc[i + 1].low and golden_line['0'] - min_price > golden_line_diff:
                golden_line['100'] = min_price
                golden_line = get_golden_line(golden_line)
                if min_data.close >= golden_line['200']:
                    break
    if golden_line['100'] == 0:
        return False
    glb['line']['golden'] = [golden_line['0'], golden_line['100']]
    return golden_line


def check_position(kline, band, direction=0):
    distance = 10
    golden_line = draw_golden_line()
    if golden_line is False:
        return False
    for k in golden_line:
        if direction == 0 and golden_line['100'] > golden_line['0'] and float(k) >= 150:
            return False
        if direction == 1 and golden_line['100'] < golden_line['0'] and float(k) >= 150:
            return False
        if kline.low - distance < golden_line[k] < kline.high + distance:
            if direction == 0:
                if kline.low - band < distance*1.5:
                    return True
            elif kline.high - band > -distance*1.5:
                return True
    return False


def check_line(buy_all=False):
    klines, line = draw_line()
    if line is False:
        return ''
    check_result = ''
    #            code         name             time_key     open    close     high      low  volume  turnover  pe_ratio  turnover_rate  last_close
    # 0   HK.MHImain  小恒指主连(2406)  2024-06-15 02:42:00  17773.0  17772.0  17773.0  17769.0      18  319883.0       0.0            0.0     17772.0
    last_kline = klines.iloc[-1]
    last2_kline = klines.iloc[-2]
    last3_kline = klines.iloc[-3]
    delta_price = last_kline.close - last_kline.last_close
    profit = 20
    kline_len = 10
    if line['upper'] - line['lower'] < 25:
        check_result = 'bands_narrow'
    elif (check_position(last_kline, line['lower']) or check_position(last2_kline, line['lower2']) or check_position(last3_kline, line['lower3'])) and line['mid'] - last_kline.close > profit:
        if delta_price > 0 or delta_price == 0 and last2_kline.close - last2_kline.last_close >= kline_len*2:
            if last_kline.close >= last3_kline.high and last3_kline.close < last3_kline.open and (last3_kline.open - last2_kline.close) / (last3_kline.high - last3_kline.low) < 1/3 and last3_kline.high - last3_kline.low >= kline_len:
                check_result = 'long_swallow1_bull'
            elif last_kline.close >= last3_kline.open and last_kline.high >= last3_kline.high and last2_kline.close < last2_kline.open and last3_kline.close < last3_kline.open and last2_kline.high - last2_kline.low + last3_kline.high - last3_kline.low >= kline_len*2:
                check_result = 'long_swallow2_bull'
            elif last2_kline.close > last2_kline.low and abs(last2_kline.close - last2_kline.open) / (last2_kline.close - last2_kline.low) < 1/3 and (last2_kline.high - last2_kline.close) / (last2_kline.close - last2_kline.low) < 1/3 and last2_kline.high - last2_kline.low >= kline_len*2:
                check_result = 'long_pinba_bull'
            else:
                check_result = 'wait_long_signal'
        else:
            check_result = 'wait_long_trend'
    elif buy_all and ((check_position(last_kline, line['upper'], 1) or check_position(last2_kline, line['upper2'], 1) or check_position(last3_kline, line['upper3'], 1)) and last_kline.close - line['mid'] > profit):
        if delta_price < 0 or delta_price == 0 and last2_kline.close - last2_kline.last_close <= -kline_len*2:
            if last_kline.close <= last3_kline.low and last3_kline.close > last3_kline.open and (last2_kline.close - last3_kline.open) / (last3_kline.high - last3_kline.low) < 1/3 and last3_kline.high - last3_kline.low >= kline_len:
                check_result = 'short_swallow1_bear'
            elif last_kline.close <= last3_kline.open and last_kline.low <= last3_kline.low and last2_kline.close > last2_kline.open and last3_kline.close > last3_kline.open and last2_kline.high - last2_kline.low + last3_kline.high - last3_kline.low >= kline_len*2:
                check_result = 'short_swallow2_bear'
            elif last2_kline.high > last2_kline.close and abs(last2_kline.close - last2_kline.open) / (last2_kline.high - last2_kline.close) < 1/3 and (last2_kline.close - last2_kline.low) / (last2_kline.high - last2_kline.close) < 1/3 and last2_kline.high - last2_kline.low >= kline_len*2:
                check_result = 'short_pinba_bear'
            else:
                check_result = 'wait_short_signal'
        else:
            check_result = 'wait_short_trend'
    else:
        check_result = 'not_near_bands'
    # if 'bull' in check_result or 'bear' in check_result:
    #     line['last_signal'] = check_result
    log.info('check_line: %s' % check_result)
    # 不符合条件就撤单
    if glb['submitted_buy_last_bull'] is not None and (check_result == 'not_near_bands' or 'bear' in check_result):
        cancel_all(glb['submitted_buy_last_bull'].code, trd_side=ft.TrdSide.BUY)
        log.info('cancel_all bull, check_result: %s' % check_result)
    elif glb['submitted_buy_last_bear'] is not None and (check_result == 'not_near_bands' or 'bull' in check_result):
        cancel_all(glb['submitted_buy_last_bear'].code, trd_side=ft.TrdSide.BUY)
        log.info('cancel_all bear, check_result: %s' % check_result)
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
        if type == 'Ask':
            price = max(0.01, data[type][0][0])
        else:
            price = max(0.01, data[type][1][0])
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.BUY, trd_env=conf['TRADE_ENV'], acc_id=conf['acc_id'])
    # log.info('_smart_buy, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('_smart_buy error, ret: %s, data:\n%s' % (ret, data))
        if '购买力不足' in data:
            conf['AUTO_BUY'] = False
        return False
    else:
        log.info('_smart_buy success, code: %s, price: %s, volume: %s' % (code, price, volume))
        return data


def _smart_sell(code, volume, price=None, type='Ask'):
    if price is None:
        data = get_order_book(code)
        if not data or not data[type][0]:
            return False
        price = max(0.01, data[type][0][0])
    price = round(price, 3)
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.SELL, trd_env=conf['TRADE_ENV'], acc_id=conf['acc_id'])
    # log.info('_smart_sell, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('_smart_sell error, ret: %s, data:\n%s' % (ret, data))
        return False
    else:
        log.info('_smart_sell success, code: %s, price: %s, volume: %s' % (code, price, volume))
        return data


def _cancel_order(order_id):
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.CANCEL, order_id=order_id, price=0, qty=0, trd_env=conf['TRADE_ENV'], acc_id=conf['acc_id'])
    # log.info('_cancel_order, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('_cancel_order error, ret: %s, data:\n%s' % (ret, data))
        return False
    else:
        log.info('_cancel_order success')
        return data


def _modify_order(order, price, qty=None):
    price = round(price, 3)
    if not qty and price == order.price:
        log.info('modify_order warning %s, old price: %s == new price: %s, qty: %s' % (order.code, order.price, price, qty))
        return False
    qty = qty or order.qty
    ret, data = trade_ctx.modify_order(modify_order_op=ft.ModifyOrderOp.NORMAL, order_id=order.order_id, price=price, qty=qty, trd_env=conf['TRADE_ENV'], acc_id=conf['acc_id'])
    # log.info('modify_order, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('modify_order error, ret: %s, old price: %s, new price: %s, qty: %s, data:\n%s' % (ret, order.price, price, qty, data))
        return False
    else:
        log.info('modify_order success, old price: %s, new price: %s, qty: %s' % (order.price, price, qty))
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
    ret, data = trade_ctx.order_list_query(status_filter_list=status_filter_list, code=code, trd_env=conf['TRADE_ENV'], refresh_cache=True, acc_id=conf['acc_id'])
    # log.info('order_list_query, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('order_list_query error, ret: %s, data:\n%s, code: %s' % (ret, data, code))
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
    data = data[~data.code.isin(glb['past_hold_code_list']) & ~data.stock_name.str.contains('瑞银')]
    data = data[(data.order_status == ft.OrderStatus.SUBMITTED) | (data.order_status == ft.OrderStatus.FILLED_PART)]
    for i in range(0, len(data)):
        item = data.iloc[i]
        if item.trd_side == ft.TrdSide.BUY:
            set_submitted_buy(item.code, item.stock_name, item)
        elif item.trd_side == ft.TrdSide.SELL:
            set_submitted_sell(item)
    if ft.OrderStatus.FILLED_ALL in status_filter_list:
        return filled_all_data
    return data


def _cancel_all(code='', trd_side=''):
    if code is None:
        return False
    if code == '' and trd_side == '':
        ret, data = trade_ctx.cancel_all_order(trd_env=conf['TRADE_ENV'], acc_id=conf['acc_id'])
        log.info('cancel_all_order, ret: %s, data: %s' % (ret, data))
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
            if trd_side == '':
                cancel_order(item.order_id)
            elif trd_side == item.trd_side:
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
            modify_order(data0, data0.price - 0.001)
        else:
            log.info('force_sell success')

# 卖掉指定的股票
def sell_all(code='', qty='', stock_type=''):
    if code != '':
        cancel_all(code)
        force_sell(code, qty)
        return True
    cancel_all() # 尽量调用撤销全部订单接口比较快
    data = _position_list_query(stock_type=stock_type, caller='sell_all')
    if data is False or data is None:
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            item = data.iloc[i]
            log.info('to sell all')
            if item.qty > item.can_sell_qty:
                cancel_all(item.code)
            force_sell(item.code, item.qty)


def subscribe(code_list, subtype_list, subscribe_push=True, need_log=True):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.subscribe(code_list, subtype_list, subscribe_push=subscribe_push)
    if need_log:
        log.info('subscribe %s %s, ret: %s, data: %s' % (code_list, subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('subscribe error %s %s' % (code_list, subtype_list))
        return False
    else:
        return True


def unsubscribe(code_list, subtype_list):
    if len(code_list) == 0:
        return False
    ret, data = quote_ctx.unsubscribe(code_list, subtype_list)
    log.info('unsubscribe %s %s, ret: %s, data: %s' % (code_list, subtype_list, ret, data))
    if ret != ft.RET_OK:
        log.info('unsubscribe error %s %s' % (code_list, subtype_list))
        return False
    else:
        return True


def set_submitted_buy(code, stock_name, order=None):
    if stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = True
        glb['submitted_buy_last_bull'] = order
        log.info('set_submitted_buy bull:%s' % code)
    elif stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = True
        glb['submitted_buy_last_bear'] = order
        log.info('set_submitted_buy bear: %s' % code)
    subscribe([code], [ft.SubType.ORDER_BOOK])


def reset_submitted_buy(code, stock_name):
    if stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = False
        glb['submitted_buy_last_bull'] = None
        log.info('reset_submitted_buy bull: %s' % code)
    elif stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = False
        glb['submitted_buy_last_bear'] = None
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


def log_submitted_sell_price(code, caller=''):
    price_list = []
    for item in glb['submitted_sell_orders'][code]:
        price_list.append(item.price)
    log.info('%s code: %s, price_list: %s' % (caller, code, price_list))


def set_submitted_sell(order):
    code = order.code
    if code not in glb['submitted_sell_orders']:
        glb['submitted_sell_orders'][code] = []
    append_data(glb['submitted_sell_orders'][code], 'order_id', order)
    if '牛' in order.stock_name:
        glb['submitted_sell_last_bull'] = glb['submitted_sell_orders'][code][-1]
    elif '熊' in order.stock_name:
        glb['submitted_sell_last_bear'] = glb['submitted_sell_orders'][code][-1]
    log_submitted_sell_price(code, 'set')


def reset_submitted_sell(order):
    code = order.code
    if code not in glb['submitted_sell_orders']:
        glb['submitted_sell_orders'][code] = []
    del_data(glb['submitted_sell_orders'][code], 'order_id', order)
    if '牛' in order.stock_name:
        if len(glb['submitted_sell_orders'][code]) > 0:
            glb['submitted_sell_last_bull'] = glb['submitted_sell_orders'][code][-1]
        else:
            glb['submitted_sell_last_bull'] = None
    elif '熊' in order.stock_name:
        if len(glb['submitted_sell_orders'][code]) > 0:
            glb['submitted_sell_last_bear'] = glb['submitted_sell_orders'][code][-1]
        else:
            glb['submitted_sell_last_bear'] = None
    log_submitted_sell_price(code, 'reset')


def set_hold(code, stock_name):
    if stock_name.find('牛') > -1:
        glb['today_hold_bull_list'].append(code)
    elif stock_name.find('熊') > -1:
        glb['today_hold_bear_list'].append(code)
    glb['today_hold_code_list'].append(code)
    subscribe([code], [ft.SubType.ORDER_BOOK], need_log=False)


def reset_hold():
    glb['today_hold_bull_list'] = []
    glb['today_hold_bear_list'] = []
    glb['today_hold_code_list'] = []


# 统计今日盈亏
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
                to_buy('bear', volume=item.qty, force=True, cur_price_min=conf['CUR_PRICE_MAX'] + 0.03, cur_price_max=conf['CUR_PRICE_MAX'] + 0.08)
            elif item.stock_name.find('牛') > -1:
                to_buy('bull', volume=item.qty, force=True, cur_price_min=conf['CUR_PRICE_MAX'] + 0.03, cur_price_max=conf['CUR_PRICE_MAX'] + 0.08)
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


def _position_list_query(stock_type='', need_log=True, caller='', code=''):
    # log.info('position_list_query, caller: %s' % caller)
    ret, data = trade_ctx.position_list_query(trd_env=conf['TRADE_ENV'], refresh_cache=True, acc_id=conf['acc_id'])
    if need_log:
        log.info('position_list_query, caller: %s, data:\n%s' % (caller, data))
    if ret != ft.RET_OK:
        log.info('position_list_query error, ret: %s, data:\n%s' % (ret, data))
        return False
    reset_hold()
    hsi_data = data[data.stock_name.str.contains('恒指') & ~data.stock_name.str.contains('瑞银')]

    # 自动移仓
    if auto_move_position(hsi_data):
        return False

    # today_buy_hold_data要符合5个条件
    today_buy_data = hsi_data[(hsi_data.code == conf['LONG_BULL_CODE']) | ~hsi_data.code.isin(conf['exclude_code_list']) & (hsi_data.today_buy_qty > 0) & (hsi_data.qty == hsi_data.today_buy_qty - hsi_data.today_sell_qty)]
    sum_today_pl_val(today_buy_data)

    position_list = []
    today_buy_hold_data = today_buy_data[today_buy_data.qty > 0]
    if len(today_buy_hold_data) > 0:
        for i in range(0, len(today_buy_hold_data)):
            item = today_buy_hold_data.iloc[i]
            set_hold(item.code, item.stock_name)
            # 如果一单也没挂，则自动挂单
            if item.can_sell_qty == item.qty and item.code in glb['submitted_sell_orders'] and len(glb['submitted_sell_orders'][item.code]) == 0:
                log.info('auto_place_order, code: %s, nominal_price: %s, can_sell_qty: %s' % (item.code, item.nominal_price, item.can_sell_qty))
                auto_place_order(item.code, item.qty, item.nominal_price)
            # 检查止损
            # if conf['NEED_LOSS'] and caller in ['per_min', 'fluctuate']:
            #     check_profit_loss(item.code, item.nominal_price, round(item.nominal_price + 0.001, 3), caller='position')

        if stock_type == 'bull':
            position_list = today_buy_hold_data[today_buy_hold_data.stock_name.str.contains('牛')]
        elif stock_type == 'bear':
            position_list = today_buy_hold_data[today_buy_hold_data.stock_name.str.contains('熊')]
        elif code != '':
            position_list = today_buy_hold_data[today_buy_hold_data.code == code]
        else:
            position_list = today_buy_hold_data
    else:
        if conf['NEED_LOSS']:
            glb['max_nominal_price'] = {}
            glb['loss'] = {}
        if glb['almost_over']:
            end()
    glb['past_hold_code_list'] = conf['exclude_code_list']
    for index, row in hsi_data.iterrows():
        if row.code not in glb['today_hold_code_list'] and row.qty > 0:
            add_unique_element(glb['past_hold_code_list'], row.code)
    if need_log:
        log.info('today_hold_code_list: %s, past_hold_code_list: %s' % (glb['today_hold_code_list'], glb['past_hold_code_list']))
    return position_list


class SysNotify(ft.SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------SysNotify push--------------------')
        ret, data = super(SysNotify, self).on_recv_rsp(rsp_pb)
        log.info('SysNotify push ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('SysNotify push error')
            return ret, data
        return ret, data


def modify_order2(index, order_list, price):
    order = order_list[index]
    if glb['auto_place_order_flag'] or glb['loss'][order.code]:
        glb['timer'].clearTimeoutHandler()
        return False
    _modify_order(order, price + conf['EVERY_ORDER_DIFF'] * (index + 1))


def _profit_order(order_list):
    order_list2 = order_list[:] # 用新的数组，因为旧的成交了就会变化
    order = order_list2[0]
    if glb['timer'] and glb['timer'].running:
        return False
    order_list2 = order_list2[1:]
    for i in range(0, len(order_list2)):
        item = order_list2[i]
        price2 = round(order.price + conf['EVERY_ORDER_DIFF'] * (i + 1), 3)
        if price2 != item.price:
            glb['timer'] = Timer(modify_order2, count=len(order_list2) - i, delay=1.5, order_list=order_list2[i:], price=order.price + conf['EVERY_ORDER_DIFF'] * i)
            glb['timer'].repeat()
            break


def _check_profit_loss(code, bid_price, ask_price, caller='', need_log=True):
    if code not in glb['today_hold_code_list'] or code not in glb['submitted_sell_orders'] or len(glb['submitted_sell_orders'][code]) == 0:
        return False
    order_list = glb['submitted_sell_orders'][code]
    order = order_list[0]
    if code not in glb['max_nominal_price'] or bid_price > glb['max_nominal_price'][code]:
        glb['max_nominal_price'][code] = bid_price
    last_filled_price = glb['filled_all_last_order'].get(code, {}).get('price')
    if last_filled_price > glb['max_nominal_price'][code]:
        glb['max_nominal_price'][code] = last_filled_price

    if code not in glb['loss']:
        glb['loss'][code] = False

    max_price = glb['max_nominal_price'][code]
    if need_log and not glb['loss'][code]:
        log.info('%s check_profit_loss %s, ask_price: %s, max_price: %s' % (caller, code, ask_price, max_price))

    max_price_diff = round(max_price - ask_price, 3)
    if max_price_diff >= conf['LOSS_PRICE_DIFF'] or glb['almost_over']:
        glb['loss'][code] = True
        buy_price = find_buy_price(order)
        if need_log:
            log.info('%s loss %s, buy_price: %s, ask_price: %s, max_price: %s' % (caller, code, buy_price, ask_price, max_price))
        loss_price = min(ask_price, last_filled_price) + conf['EVERY_ORDER_DIFF']
        force_loss = ask_price <= buy_price and ('牛' in order.stock_name and glb['cur_price'] < glb['line']['long'] or '熊' in order.stock_name and glb['cur_price'] > glb['line']['long'])
        if (force_loss or glb['almost_over']) and ask_price < last_filled_price:
            loss_price = ask_price + 0.001
        if loss_price < order.price:
            modify_order(order, loss_price)
    else:
        glb['loss'][code] = False
        if len(order_list) > 1:
            profit_order(order_list)


class OrderBook(ft.OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret, data = super(OrderBook, self).on_recv_rsp(rsp_str)
        # log.info('OrderBook push ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('OrderBook push error, ret: %s, data:%s' % (ret, data))
            return ret, data
        t = data['svr_recv_time_ask']
        if len(t) < 19: # 部分数据的接收时间为空字符串，例如服务器重启或第一次推送的缓存数据
            # log.info('OrderBook push warning, t: %s, data:%s' % (t, data))
            return ret, data
        s = int(t[17:19])
        if s % 3 == 0 and data['Bid'][0] and data['Ask'][0]:
            if data['code'] not in glb['order_book']:
                glb['order_book'][data['code']] = data
            if conf['NEED_LOSS']:
                check_profit_loss(data['code'], data['Bid'][0][0], data['Ask'][0][0], caller='order_book', need_log=s%9==0)
            glb['order_book'][data['code']] = data

        return ret, data


def auto_place_order(code, volume, price, cancel=False):
    if not conf['AUTO_PLACE_ORDER'] or glb['to_over']:
        return False
    if glb['auto_place_order_flag']:
        log.info('auto_place_order_flag True')
        return False
    glb['auto_place_order_flag'] = True
    first_order_price = price + conf['FIRST_ORDER_DIFF']
    order_list = conf['ORDER_LIST']
    if code in glb['submitted_sell_orders'] and len(glb['submitted_sell_orders'][code]) > 0:
        order_list = conf['ADD_ORDER_LIST']
        _modify_order(glb['submitted_sell_orders'][code][0], first_order_price)
        first_order_price += 0.004
    if cancel:
        cancel_all(code, trd_side=ft.TrdSide.SELL)
    if volume < 100e3 or glb['almost_over']:
        data = smart_sell(code, volume, first_order_price)
        if data is False:
            log.info('auto_place_order => smart_sell error')
        glb['auto_place_order_flag'] = False
        return
    item = []
    # [[600e3, 150e3, 150e3, 150e3, 150e3]]
    for i in range(0, len(order_list)):
        if volume >= order_list[i][0]:
            item = order_list[i]
            break
    volume_diff = volume - item[0]
    if glb['move_position']:
        first_order_price += 0.015
    last_order_price = 0
    for i in range(1, len(item)): # 从1开始
        vol = item[i]
        if volume_diff > 0 and i == 1:
            vol += volume_diff
        if vol == 0:
            continue
        last_order_price = first_order_price + conf['EVERY_ORDER_DIFF'] * (i - 1)
        data = smart_sell(code, vol, last_order_price)
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
        order = data.iloc[0]
        if order.trd_env != conf['TRADE_ENV']:
            log.info('TradeOrder not TRADE_ENV')
            return ret, data
        log.info('TradeOrder trd_side: %s, order_status: %s' % (order.trd_side, order.order_status))
        if order.code in glb['past_hold_code_list'] or '瑞银' in order.stock_name:
            return ret, data
        if order.order_status == ft.OrderStatus.FILLED_ALL or order.order_status == ft.OrderStatus.CANCELLED_PART:
            glb['filled_all_last_order'][order.code] = {'updated_time': order.updated_time, 'price': order.price, 'trd_side': order.trd_side}
            glb['filled_all_last_order']['last'] = {'updated_time': order.updated_time, 'price': order.price, 'trd_side': order.trd_side}
            if order.trd_side == ft.TrdSide.BUY:
                if conf['NEED_LOSS']:
                    glb['max_nominal_price'][order.code] = order.price
                reset_submitted_buy(order.code, order.stock_name)
                set_hold(order.code, order.stock_name)
                time.sleep(2)
                auto_place_order(order.code, order.dealt_qty, order.price)
            elif order.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(order)
                position_list_query(caller=order.order_status + '-' + order.trd_side)
        elif order.order_status == ft.OrderStatus.FILLED_PART:
            if order.trd_side == ft.TrdSide.BUY:
                set_hold(order.code, order.stock_name)
        elif order.order_status == ft.OrderStatus.SUBMIT_FAILED or order.order_status == ft.OrderStatus.FAILED:
            position_list_query(caller=order.order_status + '-' + order.trd_side)
        elif order.order_status == ft.OrderStatus.CANCELLED_ALL:
            if order.trd_side == ft.TrdSide.BUY:
                reset_submitted_buy(order.code, order.stock_name)
            elif order.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(order)
        elif order.order_status == ft.OrderStatus.SUBMITTED:
            if order.trd_side == ft.TrdSide.BUY:
                set_submitted_buy(order.code, order.stock_name, order)
            elif order.trd_side == ft.TrdSide.SELL:
                set_submitted_sell(order)
        elif order.order_status == ft.OrderStatus.DISABLED:
            # 需要重新获取订单以重置一些全局变量
            order_list_query()

        return ret, data


def _get_stock_code(stock_type='all', cache_first=False, cur_price_min=None, cur_price_max=None, sort_field=ft.SortField.VOLUME, ascend=False, get_list=False):
    cache = glb['cache_get_stock_code'].get(stock_type)
    if cache_first and cache['data'] is not None and time.time() - cache['last_time'] < cache['duration']:
        log.info('读取缓存数据：%s' % cache)
        return cache['data']
    cache['data'] = None

    req = ft.WarrantRequest()
    if stock_type == 'bull':
        req.type_list = [ft.WrtType.BULL]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    elif stock_type == 'bear':
        req.type_list = [ft.WrtType.BEAR]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    req.issuer_list = [ft.Issuer.JP, ft.Issuer.UB, ft.Issuer.BP, ft.Issuer.CT, ft.Issuer.HS, ft.Issuer.MS, ft.Issuer.GJ]  # Qot_Common.Issuer, 发行人过滤列表
    req.status = ft.WarrantStatus.NORMAL  # Qot_Common.WarrantStatus, 窝轮状态
    req.cur_price_min = cur_price_min or conf['CUR_PRICE_MIN']  # 最新价过滤起点
    req.cur_price_max = cur_price_max or conf['CUR_PRICE_MAX']  # 最新价过滤终点
    req.conversion_min = 10000  # 换股比率过滤起点
    req.conversion_max = 10000  # 换股比率过滤终点
    req.vol_min = 1000  # 成交量的过滤下限，单位K
    req.sort_field = sort_field  # 根据哪个字段排序
    req.ascend = ascend  # 升序True, 降序False
    req.begin = 0  # 数据起始点
    req.num = 40 if cur_price_min == 0.01 else 3  # 返回数据个数，最大200

    ret, data = quote_ctx.get_warrant(CONST['HSI_CODE'], req=req)
    # log.info('get_warrant, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('get_warrant error')
    else:
        data = data[0]
        # FUTU BUG: 返回的结果还要再过滤一次
        data = data[(data.stock_owner == CONST['HSI_CODE']) & (data.status == ft.WarrantStatus.NORMAL)]
        data = data[~data.stock.isin(glb['past_hold_code_list']) & (data.bid_price >= 0.01)]
        if len(data) > 0:
            if get_list:
                cache['data'] = data
            elif conf['TRY_RECOVERY'] and cur_price_max == 0.02:
                rt_data = get_rt_data()
                if rt_data is False:
                    return False
                cur_rt_data = rt_data.iloc[-1]
                intrinsic_price = round(abs(cur_rt_data.cur_price - data['strike_price']) / data.conversion_ratio, 3)
                data.insert(loc=data.columns.get_loc('ask_price') + 1, column='intrinsic_price', value=intrinsic_price)
                data.insert(loc=data.columns.get_loc('intrinsic_price') + 1, column='ibp_diff', value=data.intrinsic_price - data.bid_price)
                data = data.sort_values(by='ibp_diff', ascending=False)
                # log.info('ibp_diff, data:\n%s' % data)
                data = data.iloc[0]
                if data.ibp_diff >= 0.008:
                    log.info('ibp_diff allow buy, %s code: %s, bid_price: %s, ask_price: %s, intrinsic_price: %s' % (stock_type, data.stock, data.bid_price, data.ask_price, data.intrinsic_price))
                    cache['data'] = data
                else:
                    log.info('ibp_diff not allow buy, %s code: %s, bid_price: %s, ask_price: %s, intrinsic_price: %s' % (stock_type, data.stock, data.bid_price, data.ask_price, data.intrinsic_price))
            else:
                cache['data'] = data.iloc[0]
                if sort_field == ft.SortField.RECOVERY_PRICE:
                    log.info('_get_stock_code, %s code: %s, recovery_price: %s' % (stock_type, cache['data']['stock'], cache['data']['recovery_price']))
        else:
            log.info('_get_stock_code, %s conditions not met' % stock_type)
    cache['last_time'] = time.time()
    return cache['data']


def to_buy(stock_type, code='', volume=None, type='Bid', force=False, cur_price_min=None, cur_price_max=None):
    log.info('to buy %s' % stock_type)
    if volume is None:
        volume = conf['BUY_VOLUME']
        # if glb['afternoon']:
        #     volume /= 2
    if code == '':
        if stock_type == 'bull':
            code = conf['BULL_CODE']
        elif stock_type == 'bear':
            code = conf['BEAR_CODE']
        else:
            code = 'auto'
    if code == '':
        return False

    if not force:
        data = _position_list_query(stock_type=stock_type, need_log=False, caller='to_buy-' + stock_type)
        if data is False or data is None:
            return False
        if len(data) > 0:
            if not conf['ALLOW_ADD']:
                log.info('not allow add')
                return False
            total_qty = sum(data.qty)
            if total_qty + volume > conf['MAX_VOLUME']:
                if conf['MAX_VOLUME'] - total_qty >= 100e3:
                    volume = math.floor((conf['MAX_VOLUME'] - total_qty) / 100e3) * 100e3
                    log.info('current total_qty: %s, MAX_VOLUME: %s, can only buy %s' % (total_qty, conf['MAX_VOLUME'], volume))
                else:
                    log.info('current total_qty: %s, MAX_VOLUME: %s, not allow add' % (total_qty, conf['MAX_VOLUME']))
                    return False
            data0 = data.iloc[0]
            code = data0.code
            last_price = glb['filled_all_last_order'].get(code, {}).get('price')
            if not last_price:
                log.info('to_buy code: %s, no filled_all_last_order, \n%s' % (code, glb['filled_all_last_order']))
                last_price = data0.cost_price
            add_price_diff = round(last_price - data0.nominal_price, 3)
            if total_qty >= conf['BUY_VOLUME'] and add_price_diff < conf['ADD_PRICE_DIFF']:
                log.info('code: %s, nominal_price: %s, last_price: %s, diff: %s < %s, not allow add' % (code, data0.nominal_price, last_price, add_price_diff, conf['ADD_PRICE_DIFF']))
                return False
            log.info('code: %s, nominal_price: %s, last_price: %s, diff: %s >= %s, allow add' % (code, data0.nominal_price, last_price, add_price_diff, conf['ADD_PRICE_DIFF']))

    if code == 'auto':
        data = _get_stock_code(stock_type=stock_type, cur_price_min=cur_price_min, cur_price_max=cur_price_max)
        if data is False or data is None:
            return False
        code = data.stock
        if '牛' in data['name']: # 必须用中括号，data.name会访问到name属性而不是列
            stock_type = 'bull'
        elif '熊' in data['name']:
            stock_type = 'bear'

    set_submitted_buy(code, CONST[stock_type])
    data = smart_buy(code, volume, type='Ask' if force else type)
    if data is False or data is None:
        reset_submitted_buy(code, CONST[stock_type])
    else:
        add_unique_element(glb['auto_buy_list'], code)
    return data


def _pre_buy():
    check_result = check_line()
    if 'bull' in check_result and conf['BULL_CODE'] != '' and not glb['submitted_buy_bull_flag'] and (conf['ALLOW_ADD'] or len(glb['today_hold_bull_list']) == 0):
        to_buy('bull')
    elif 'bear' in check_result and conf['BEAR_CODE'] != '' and not glb['submitted_buy_bear_flag'] and (conf['ALLOW_ADD'] or len(glb['today_hold_bear_list']) == 0):
        to_buy('bear')


def _get_recovery_code():
    glb['recovery_bull'] = _get_stock_code(stock_type='bull', cur_price_min=0.01, cur_price_max=0.1, sort_field=ft.SortField.RECOVERY_PRICE, ascend=False)
    glb['recovery_bear'] = _get_stock_code(stock_type='bear', cur_price_min=0.01, cur_price_max=0.1, sort_field=ft.SortField.RECOVERY_PRICE, ascend=True)


def _buy_recovery_code():
    to_buy('bear', cur_price_min=0.01, cur_price_max=0.02)
    to_buy('bull', cur_price_min=0.01, cur_price_max=0.02)



class RTData(ft.RTDataHandlerBase):
    def on_recv_rsp(self, rsp_str):
        # log.info('--------------------分时推送--------------------')
        ret, data = super(RTData, self).on_recv_rsp(rsp_str)
        if ret != ft.RET_OK:
            log.info('RTData push error, ret: %s, data: %s' % (ret, data))
            return ret, data
        #       code                 time  is_blank  opened_mins  cur_price  last_close     avg_price  volume      turnover
        # 0    HK.800000  2023-10-31 09:30:00     False          570   17337.70    17406.36  17337.700000       0  1.682861e+09
        rt_data = data.iloc[-1]
        # log.info('rtdata push, data:\n%s' % rt_data)

        if conf['TRY_FOLLOW_RECOVERY'] and not glb['afternoon']:
            if glb['recovery_bear'] is not None and rt_data.cur_price >= glb['recovery_bear']['recovery_price']:
                log.info('recovery_bear, price: %s' % rt_data.cur_price)
                glb['recovery_bear'] = None
                to_buy('bull', force=True)
            elif glb['recovery_bull'] is not None and rt_data.cur_price <= glb['recovery_bull']['recovery_price']:
                log.info('recovery_bull, price: %s' % rt_data.cur_price)
                glb['recovery_bull'] = None
                to_buy('bear')
        if conf['TRY_RECOVERY']:
            buy_recovery_code()

        return ret, data


def _auto_adjust_sell(delta_price):
    order = glb['submitted_sell_last_bull']
    if order is None:
        order = glb['submitted_sell_last_bear']
    if order is None or order.code not in glb['order_book'] or order.code not in glb['auto_buy_list']:
        return False
    order_book = glb['order_book'][order.code]
    rise_price = order_book['Ask'][1][0]
    fall_price = order_book['Ask'][0][0]
    if order.code in glb['today_hold_code_list']:
        fall_price = max(glb['filled_all_last_order'].get(order.code, {}).get('price') + conf['EVERY_ORDER_DIFF'], fall_price)
    rise_condition = False
    if '牛' in order.stock_name:
        rise_condition = delta_price >= 5
    else:
        rise_condition = delta_price <= -5
    if rise_condition:
        if rise_price > order.price:
            log.info('auto_adjust_sell order price: %s, rise_price: %s' % (order.price, rise_price))
            modify_order(order, rise_price)
    elif fall_price < order.price:
        log.info('auto_adjust_sell order price: %s, fall_price: %s' % (order.price, fall_price))
        modify_order(order, fall_price)

def _auto_adjust_buy(delta_price):
    order = glb['submitted_buy_last_bull']
    if order is None:
        order = glb['submitted_buy_last_bear']
    if order is None or order.code not in glb['order_book'] or order.code not in glb['auto_buy_list']:
        return False
    order_book = glb['order_book'][order.code]
    rise_price = order_book['Bid'][0][0]
    fall_price = order_book['Bid'][1][0]
    # if order.code in glb['today_hold_code_list']:
    #     rise_price = round(min(rise_price, find_buy_price(order) - conf['ADD_PRICE_DIFF']), 3)
    fall_condition = False
    if '牛' in order.stock_name:
        fall_condition = delta_price <= -5
    else:
        fall_condition = delta_price >= 5
    if fall_condition:
        if fall_price < order.price:
            log.info('auto_adjust_buy order price: %s, fall_price: %s' % (order.price, fall_price))
            modify_order(order, fall_price)
    elif rise_price > order.price:
        log.info('auto_adjust_buy order price: %s, rise_price: %s' % (order.price, rise_price))
        modify_order(order, rise_price)


class Ticker(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_str):
        # log.info('--------------------逐笔明细--------------------')
        ret, data = super(Ticker, self).on_recv_rsp(rsp_str)
        if ret != ft.RET_OK:
            log.info('Ticker push error, ret: %s, data:%s' % (ret, data))
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

        cur_ticker = data.iloc[-1]
        # log.info('ticker push, data:\n%s' % cur_ticker)
        t = cur_ticker.time
        h = int(t[11:13])
        m = int(t[14:16])
        s = int(t[17:19])
        if h < 9 or h == 9 and m < 30 or h >= 16:
            # log.info(data)
            if h == 16 and m == 0 and s == 0:
                end()
            return ret, data

        if h == 9 and m == 30 and s == 0:
            log.info('[%s]--------------------start--------------------' % t)
        elif h >= 13 and not glb['afternoon']:
            glb['afternoon'] = True

        if glb['trade_date'].get('trade_date_type') == 'MORNING' and h == 11 or h == 15:
            if m >= 30:
                glb['soon_over'] = True
            if m >= 55:
                if not glb['almost_over']:
                    glb['almost_over'] = True
                    # cancel_all()
                    position_list_query(caller='almost_over')
                if m >= 59:
                    if not glb['to_over']:
                        glb['to_over'] = True
                        log.info('[%s]--------------------to_over--------------------' % t)
                        if not glb['over'] and (conf['sell_all_to_over'] or (glb['today_pl_val_bull'] + glb['today_pl_val_bear']) > 0):
                            if conf['BULL_CODE'] != '' and conf['BEAR_CODE'] != '':
                                sell_all()
                            elif conf['BULL_CODE'] != '':
                                sell_all(stock_type='bull')
                            elif conf['BEAR_CODE'] != '':
                                sell_all(stock_type='bear')
                return ret, data

        if glb['to_over']:
            return ret, data

        glb['cur_price'] = cur_ticker.price

        # 每波动20点查询持仓列表，方便统计盈亏和止损
        if abs(glb['cur_price'] - glb['last_price']) >= 20:
            glb['last_price'] = glb['cur_price']
            position_list_query(need_log=False, caller='fluctuate')
        # 每分钟查询持仓列表
        if s == 29:
            position_list_query(need_log=False, caller='per_min')

        # 自动买入
        if conf['AUTO_BUY'] and not glb['soon_over'] and (s == 56 or s == 57 or s == 58 or s == 59):
            pre_buy()
        # 自动调价
        if (conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']) and s % 3 == 0:
            delta_price = glb['cur_price'] - glb['last_3s_price']
            auto_adjust_buy(delta_price)
            auto_adjust_sell(delta_price)
            glb['last_3s_price'] = glb['cur_price']

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


# 限制n秒内最多查1次
pre_buy = throttle(_pre_buy, 1, need_log=False)
check_profit_loss = throttle(_check_profit_loss, 2, need_log=False)
profit_order = throttle(_profit_order, 2)
auto_adjust_buy = throttle(_auto_adjust_buy, 2, need_log=False)
auto_adjust_sell = throttle(_auto_adjust_sell, 2, need_log=False)
# 每 30 秒内最多请求 10 次查询持仓接口
position_list_query = throttle(_position_list_query, 3, need_log=False)
# 每 30 秒内最多请求 15 次下单接口，且连续两次请求的间隔不可小于 0.02 秒
smart_buy = throttle(_smart_buy, 2)
smart_sell = delay_execution(_smart_sell, 1.5) # 自动挂卖单需要遍历，所以不能节流，只能延时
# 每 30 秒内最多请求 60 次筛选窝轮接口
get_stock_code = throttle(_get_stock_code, 0.5)
# 每 300 秒内最多请求 1 次筛选最近回收牛熊接口
get_recovery_code = throttle(_get_recovery_code, 300)
# 每 60 秒内最多请求 1 次购买最近回收牛熊接口
buy_recovery_code = throttle(_buy_recovery_code, 60)
# 每 30 秒内最多请求 10 次查询今日订单接口
order_list_query = throttle(_order_list_query, 3)
# 每 30 秒内最多请求 20 次改单撤单接口，且连续两次请求的间隔不可小于 0.04 秒
modify_order = delay_execution(_modify_order, 1.5) # 自动调价需要遍历，所以不能节流，只能延时
cancel_order = delay_execution(_cancel_order, 1.5) # 撤销订单需要遍历，所以不能节流，只能延时
cancel_all = delay_execution(_cancel_all, 1.5) # 撤销全部订单需要遍历，所以不能节流，只能延时


def set_config(config):
    global conf
    conf.update(config)


def start(config=None):
    global log, quote_ctx, trade_ctx
    if config is not None:
        set_config(config)
    ft.set_futu_debug_model(False)
    log = Logger(conf['log_file']).get_logger()
    quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
    trade_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.HK, host=conf['HOST'], port=conf['PORT'])
    # ret, data = trade_ctx.get_acc_list()
    # log.info(data)
    resetData()
    if conf['TRADE_ENV'] == ft.TrdEnv.REAL:
        ret, data = trade_ctx.unlock_trade(password_md5=conf['PASSWORD_MD5'], password=conf['PASSWORD'])
        log.info('unlock_trade, ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('unlock_trade error')
            return False
    data = subscribe([CONST['MHI_CODE']], [ft.SubType.TICKER], subscribe_push=True)
    if data is False:
        return False
    data = subscribe([CONST['MHI_CODE']], [ft.SubType.K_1M], subscribe_push=False)
    if data is False:
        return False
    if conf['TRY_RECOVERY'] or conf['TRY_FOLLOW_RECOVERY']:
        data = subscribe([CONST['HSI_CODE']], [ft.SubType.RT_DATA], subscribe_push=conf['TRY_FOLLOW_RECOVERY'])
        if data is False:
            return False
    # 查询最近回收牛熊
    # get_recovery_code()
    # 查询并检查均线
    check_line()
    position_list_query(caller='start')
    order_list_query()

    quote_ctx.set_handler(SysNotify())
    quote_ctx.set_handler(Ticker())
    if conf['TRY_FOLLOW_RECOVERY']:
        quote_ctx.set_handler(RTData())
    trade_ctx.set_handler(TradeOrder())
    if conf['NEED_LOSS'] or conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']:
        quote_ctx.set_handler(OrderBook())

    ret, data = quote_ctx.query_subscription()
    log.info('query_subscription, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('query_subscription error')
    quote_ctx.start()


def end():
    glb['over'] = True
    log.info('--------------------over--------------------')
    # quote_ctx.close()
    # trade_ctx.close()
