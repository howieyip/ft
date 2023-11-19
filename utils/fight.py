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

    'AUTO_BUY': True,                               # 是否自动买入，若是则下面的配置有效
    'FOLLOW_TREND': False,                          # 买入策略是否为顺势买入，逆势则为False
    'BULL_CODE': '',                                # 自动买入牛证的股票代码，格式HK.00700，填auto则会自动选股
    'BEAR_CODE': 'auto',                            # 自动买入熊证的股票代码，格式HK.00700，填auto则会自动选股
    'CHECK_GOLDEN_LINE': True,                      # 是否检查黄金分割线
    'GOLDEN_LINE_DIFF': 80,                         # 黄金分割线0-100之间要间隔多少点
    'BID_ASK_DIFF': 0.002,                          # 买一价和卖一价的价差小于等于多少元，才允许买入
    'CUR_PRICE_MIN': 0.04,
    'CUR_PRICE_MAX': 0.15,

    'DELTA_SECONDS': 60,                            # 多少秒内
    'DELTA_PRICE': 15,                              # 波动多少点
    'BUY_VOLUME': 100e3,                            # 下单多少股
    'MAX_VOLUME': 300e3,                            # 最大持仓股数，若超过则不会再买入

    'AUTO_ADJUST_BUY': True,                        # 是否自动调整挂的买单的价格，若是则下面的ADJUST_BUY_DICT有效
    'ADJUST_BUY_DICT': {
        'rise': [60, 1, 1],                          # 最近多少秒内，往持仓股票方向波动多少点，调整买单为第几档
        'fall': [60, 1, 2]                           # 最近多少秒内，往持仓股票反向波动多少点，调整买单为第几档
    },

    'ALLOW_ADD': True,                              # 是否允许补仓，若是则下面的ADD_PRICE_DIFF有效
    'ADD_PRICE_DIFF': 0.003,                        # 持仓股票的现价与最近一次成交价的价差大于等于多少元，才允许补仓

    'AUTO_PLACE_ORDER': True,                       # 买入后是否自动挂单分批卖出，若是则下面的ORDER_LIST有效
    'ORDER_LIST': [
        [400e3, 200e3, 2, 3],
        [300e3, 150e3, 2, 3],
        [200e3, 100e3, 2, 3],
        [100e3, 50e3, 2, 3]
    ],                                              # 下单多少股以上（大的写前面），每单挂多少股，一单挂高几格，下一单挂高几格

    'AUTO_ADJUST_SELL': True,                       # 是否自动调整挂的卖单的价格，若是则下面的ADJUST_SELL_DICT有效
    'ADJUST_SELL_DICT': {
        'rise': [2, 3, 2],                          # 最近多少秒内，往持仓股票方向波动多少点，调整卖单为第几档
        'fall': [2, 3, 1]                           # 最近多少秒内，往持仓股票反向波动多少点，调整卖单为第几档
    }
}


# 常量
HSI_CODE = 'HK.800000'                              # 恒指代码
MHI_CODE = 'HK.MHImain'                             # 小恒指代码


# 全局变量
log = None
quote_ctx = None
trade_ctx = None
glb = {
    'golden_line': {'0': 0, '100': 0, 'diff': 0, 'reverse': ''},
    'today_pl_val_bull': 0,
    'today_pl_val_bear': 0,
    'trade_date': {},
    'restarted': False,
    'afternoon': False,
    'soon_over': False,
    'almost_over': False,
    'to_over': False,
    'over': False,
    'ticker_list': [],
    'cur_price': 0,
    'last_price': 0,
    'last_filled_all_order': {},
    'adjust_ticker_list': [],
    'submitted_buy_bull': None,
    'submitted_buy_bear': None,
    'submitted_sell_bull': None,
    'submitted_sell_bear': None,
    'submitted_sell_bull_list': [],
    'submitted_sell_bear_list': [],
    'order_book': {},
    'auto_buy_list': [],
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
        'bull': {
            'data': None,
            'duration': 5,
            'last_time': 0
        },
        'bear': {
            'data': None,
            'duration': 5,
            'last_time': 0
        }
    },
    'stock_name': {
        'bull': '牛',
        'bear': '熊'
    }
}


# 添加数组元素，不重复
def add_unique_element(arr, element):
    if element not in arr:
        arr.append(element)
    return arr


# 节流函数
def throttle(fn, wait):
    last_call_time = None
    logged = False

    def throttled(*args, **kwargs):
        nonlocal last_call_time, logged
        current_time = time.time()

        if last_call_time is not None:
            countdown = round(wait - (current_time - last_call_time), 3)
        else:
            countdown = 0

        if countdown <= 0:
            last_call_time = current_time
            logged = False
            return fn(*args, **kwargs)
        else:
            if not logged:
                log.info(f'{fn.__name__} call throttling, {countdown}s remaining')
                logged = True

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
    # if re.fullmatch(pattern, time_str):
    return datetime.datetime.strptime(time_str, format_str).timestamp()
    # else:
    #     return time.time()


def get_golden_line(line=None):
    if line is None:
        line = glb['golden_line']
    d = dict()
    d['0'] = line['0']
    d['100'] = line['100']
    d['diff'] = d['100'] - d['0']
    glb['golden_line']['diff'] = glb['golden_line']['100'] - glb['golden_line']['0']
    d['reverse'] = glb['golden_line']['reverse']
    if d['diff'] > 0 and glb['golden_line']['diff'] < 0:
        d['reverse'] = 'bull'
    elif d['diff'] < 0 and glb['golden_line']['diff'] > 0:
        d['reverse'] = 'bear'
    # d['200'] = d['0'] + d['diff'] * 2
    d['2618'] = d['0'] + d['diff'] * 2.618
    glb['golden_line'] = d
    return d


def draw_golden_line():
    ret, data = quote_ctx.get_rt_data(HSI_CODE)
    # log.info('get_rt_data, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('get_rt_data error, ret: %s, data:%s' % (ret, data))
        return False
    if data.iloc[-1].time[0:10] != glb['trade_date'].get('time'):
        log.info('get_rt_data not today')
        # return False

    #       code                 time  is_blank  opened_mins  cur_price  last_close     avg_price  volume      turnover
    # 0    HK.800000  2023-10-31 09:30:00     False          570   17337.70    17406.36  17337.700000       0  1.682861e+09
    # 1    HK.800000  2023-10-31 09:31:00     False          571   17214.94    17406.36  17276.320000       0  1.822654e+09
    # 2    HK.800000  2023-10-31 09:32:00     False          572   17223.84    17406.36  17258.826667       0  8.516341e+08
    # 3    HK.800000  2023-10-31 09:33:00     False          573   17224.69    17406.36  17250.292500       0  7.468972e+08
    # ret, data = (0, {'opened_mins': [570, 571, 572, 573],
    # 'cur_price': [17337.70, 17214.94, 17223.84, 17212.21]})
    # data = pd.DataFrame(data)

    data_min = data[data.cur_price == min(data.cur_price)]
    data_max = data[data.cur_price == max(data.cur_price)]
    min_index = data_min.index.tolist()[0]
    max_index = data_max.index.tolist()[0]
    # cur_index = data.shape[0] - 1
    data_min = data_min.iloc[0]
    data_max = data_max.iloc[0]
    golden_line = {'0': 0, '100': 0}
    if data_max.opened_mins > data_min.opened_mins:
        golden_line['0'] = data_min.cur_price
        for i in range(min_index, max_index): # 买入要谨慎，需最大值和最小值之间有拐点
            if i >= 3:
                cur_price = data.iloc[i - 1].cur_price
                if ((data.iloc[i - 2].cur_price < cur_price > data.iloc[i].cur_price) and
                    (cur_price - golden_line['0'] > conf['GOLDEN_LINE_DIFF'])):
                        golden_line['100'] = cur_price
                        golden_line = get_golden_line(golden_line)
                        if (data_max.cur_price <= golden_line['2618']):
                            break
    else:
        golden_line['0'] = data_max.cur_price
        for i in range(max_index, min_index):
            if i >= 3:
                cur_price = data.iloc[i - 1].cur_price
                if ((data.iloc[i - 2].cur_price > cur_price < data.iloc[i].cur_price) and
                    (golden_line['0'] - cur_price > conf['GOLDEN_LINE_DIFF'])):
                        golden_line['100'] = cur_price
                        golden_line = get_golden_line(golden_line)
                        if (data_min.cur_price >= golden_line['2618']):
                            break
    if golden_line['100'] == 0:
        log.info('golden_line not ready')
        return False
    log.info('golden_line: %s' % golden_line)
    return golden_line

def _check_golden_line():
    golden_line = draw_golden_line()
    if golden_line is False:
        return 'null'
    if golden_line['100'] < golden_line['0']:
        value = 'bear'
    else:
        value = 'bull'
    return value


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
        price = data[type][0][0]
    if not price > 0:
        log.info('not price > 0, _smart_buy error')
        return False
    ret, data = trade_ctx.place_order(price=price, qty=volume, code=code, trd_side=ft.TrdSide.BUY, trd_env=conf['TRADE_ENV'])
    log.info('_smart_buy, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('code %s _smart_buy error, price %s, volume %s' % (code, price, volume))
        return False
    else:
        log.info('code %s _smart_buy success, price %s, volume %s' % (code, price, volume))
        return data


def _smart_sell(code, volume, price=None, type='Ask'):
    if price is None:
        data = get_order_book(code)
        if not data:
            return False
        price = data[type][0][0]
    if not price > 0:
        log.info('not price > 0, _smart_sell error')
        return False
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


def _order_list_query(code='', status=''):
    status_filter_list = [ft.OrderStatus.SUBMITTED, ft.OrderStatus.FILLED_PART]
    if status != '':
        status_filter_list.append(status)
    ret, data = trade_ctx.order_list_query(status_filter_list=status_filter_list, code=code, trd_env=conf['TRADE_ENV'], refresh_cache=True)
    # log.info('查询订单，ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('order_list_query error, code: %s' % code)
        return False
    log.info('order_list_query success, code: %s' % code)
    if ft.OrderStatus.FILLED_ALL in status_filter_list:
        filled_all_data = data[data.order_status == ft.OrderStatus.FILLED_ALL]
        if not filled_all_data.empty:
            for index, row in filled_all_data.iterrows():
                code, create_time, price = row.code, row.create_time, row.price
                if code not in glb['last_filled_all_order']:
                    glb['last_filled_all_order'][code] = {'create_time': create_time, 'price': price}
                else:
                    if create_time > glb['last_filled_all_order'][code].get('create_time'):
                        glb['last_filled_all_order'][code] = {'create_time': create_time, 'price': price}
            log.info('last_filled_all_order:\n%s' % glb['last_filled_all_order'])
        else:
            log.info('filled_all_data is empty')
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
        ret, data = trade_ctx.cancel_all_order(trd_env=conf['TRADE_ENV'])
        log.info('cancel_all_order, ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('cancel_all_order error')
    data = order_list_query(code)
    if data is False:
        log.info('_cancel_all => order_list_query error')
        return False
    if data is None:
        log.info('_cancel_all => order_list_query throttling')
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            if stock_type == '' and trd_side == '':
                cancel_order(data2.order_id)
            elif data2.stock_name.find(glb['stock_name'][stock_type]) > -1 and trd_side == '':
                cancel_order(data2.order_id)
            elif data2.stock_name.find(glb['stock_name'][stock_type]) > -1 and trd_side == data2.trd_side:
                cancel_order(data2.order_id)
            elif stock_type == '' and trd_side == data2.trd_side:
                cancel_order(data2.order_id)


# 清仓指定股票
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

# 清仓今日买的指定股票
def sell_all(code='', qty='', stock_type=''):
    if code != '':
        cancel_all(code=code)
        force_sell(code, qty)
        return True
    cancel_all() # 尽量调用撤销全部订单接口比较快
    data = _position_list_query(stock_type=stock_type)
    if data is False or data is None:
        return False
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            log.info('to sell all')
            if data2.qty > data2.can_sell_qty:
                cancel_all(code=data2.code)
            force_sell(data2.code, data2.qty)


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


def reset_has(stock_name='', real=False):
    if stock_name == '' or stock_name.find('牛') > -1:
        if real:
            glb['bull_stop_price'] = 0
            unsubscribe(glb['has_bull_list'], [ft.SubType.ORDER_BOOK])
        glb['has_bull_list'] = []
    if stock_name == '' or stock_name.find('熊') > -1:
        if real:
            glb['bear_stop_price'] = 0
            unsubscribe(glb['has_bear_list'], [ft.SubType.ORDER_BOOK])
        glb['has_bear_list'] = []


def set_submitted_buy(code, stock_name, data=None):
    if stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = True
        if data is not None:
            glb['submitted_buy_bull'] = data
        log.info('set_submitted_buy bull:%s' % code)
    elif stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = True
        if data is not None:
            glb['submitted_buy_bear'] = data
        log.info('set_submitted_buy bear: %s' % code)
    subscribe([code], [ft.SubType.ORDER_BOOK])


def reset_submitted_buy(code, stock_name=''):
    if stock_name == '' or stock_name.find('牛') > -1:
        glb['submitted_buy_bull_flag'] = False
        glb['submitted_buy_bull'] = None
        log.info('reset_submitted_buy bull: %s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        glb['submitted_buy_bear_flag'] = False
        glb['submitted_buy_bear'] = None
        log.info('reset_submitted_buy bear: %s' % code)
    # if not conf['AUTO_ADJUST_SELL']:
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
        log.info('set_submitted_sell bull: %s, price: %s' % (code, glb['submitted_sell_bull'].price))
    elif stock_name.find('熊') > -1:
        append_data(glb['submitted_sell_bear_list'], 'order_id', data)
        glb['submitted_sell_bear'] = glb['submitted_sell_bear_list'][-1]
        log.info('set_submitted_sell bear: %s, price: %s' % (code, glb['submitted_sell_bear'].price))


def reset_submitted_sell(code, stock_name='', data=None):
    if stock_name == '' or stock_name.find('牛') > -1:
        del_data(glb['submitted_sell_bull_list'], 'order_id', data)
        if len(glb['submitted_sell_bull_list']) > 0:
            glb['submitted_sell_bull'] = glb['submitted_sell_bull_list'][-1]
        else:
            glb['submitted_sell_bull'] = None
        log.info('reset_submitted_sell bull: %s' % code)
    if stock_name == '' or stock_name.find('熊') > -1:
        del_data(glb['submitted_sell_bear_list'], 'order_id', data)
        if len(glb['submitted_sell_bear_list']) > 0:
            glb['submitted_sell_bear'] = glb['submitted_sell_bear_list'][-1]
        else:
            glb['submitted_sell_bear'] = None
        log.info('reset_submitted_sell bear: %s' % code)


def _position_list_query(stock_type='', logging=True):
    ret, data = trade_ctx.position_list_query(trd_env=conf['TRADE_ENV'], refresh_cache=True)
    if logging:
        log.info('position_list_query, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('position_list_query error, ret: %s, data:\n%s' % (ret, data))
        return False
    reset_has()
    data = data[(data.today_buy_qty > 0) & data.stock_name.str.contains('恒指') & (data.nominal_price < conf['CUR_PRICE_MAX'])]

    # 统计今日盈亏
    glb['today_pl_val_bull'] = 0
    glb['today_pl_val_bear'] = 0
    for i in range(0, len(data)):
        data2 = data.iloc[i]
        if data2.stock_name.find('牛') > -1:
            glb['today_pl_val_bull'] += data2.today_pl_val
        elif data2.stock_name.find('熊') > -1:
            glb['today_pl_val_bear'] += data2.today_pl_val
        if data2.qty > 0 and data2.qty != data2.today_buy_qty - data2.today_sell_qty:
            log.info('position_list_query not today buy, data:\n%s' % data2)
    log.info('current price: %s, today bull: %s, today bear: %s' % (glb['cur_price'], glb['today_pl_val_bull'], glb['today_pl_val_bear']))

    data = data[(data.qty > 0) & (data.qty == data.today_buy_qty - data.today_sell_qty)]
    if len(data) > 0:
        for i in range(0, len(data)):
            data2 = data.iloc[i]
            set_has(data2.code, data2.stock_name)
            if data2.qty == data2.can_sell_qty:
                reset_submitted_buy(data2.code, data2.stock_name)
                if conf['AUTO_PLACE_ORDER'] and round(data2.nominal_price, 3) > 0.021 and not glb['to_over']:
                    if data2.stock_name.find('熊') > -1 or (data2.stock_name.find('牛') > -1 and conf['BULL_CODE'] == 'auto'):
                        log.info('code: %s, not auto_place_order, nominal_price: %s, cost_price: %s' % (data2.code, data2.nominal_price, data2.cost_price))
                        auto_place_order(data2.code, data2.qty, max(data2.nominal_price, data2.cost_price))
            if ((glb['golden_line']['reverse'] == 'bull' and data2.stock_name.find('熊') > -1) or
                (glb['golden_line']['reverse'] == 'bear' and data2.stock_name.find('牛') > -1 and conf['BULL_CODE'] == 'auto')):
                    log.info('code: %s, reverse_sell, nominal_price: %s, cost_price: %s' % (data2.code, data2.nominal_price, data2.cost_price))
                    sell_all(code=data2.code, qty=data2.qty)
            if round(data2.nominal_price, 3) <= 0.021:
                log.info('code: %s, force_replacing, nominal_price: %s, cost_price: %s' % (data2.code, data2.nominal_price, data2.cost_price))
                glb['force_replacing'] = True
                sell_all(code=data2.code, qty=data2.qty)
                if data2.stock_name.find('熊') > -1:
                    to_buy('bear', data2.qty, force=True)
                else:
                    to_buy('bull', data2.qty, force=True)
        bull_data = data[data.stock_name.str.contains('牛')]
        bear_data = data[data.stock_name.str.contains('熊')]
        if len(bull_data) == 0:
            reset_has('牛', True)
        if len(bear_data) == 0:
            reset_has('熊', True)
        if stock_type == 'bull':
            data = bull_data
        elif stock_type == 'bear':
            data = bear_data
        if logging:
            log.info('today buy %s, data:\n%s' % (stock_type, data))
        return data
    else:
        log.info('today buy qty has empty')
        reset_has(real=True) # TODO 没有取消订阅，因为has_bear_list已经在上面被清空了
        if glb['almost_over']:
            glb['over'] = True
            log.info('--------------------over--------------------')
        return []


class SysNotifyTest(ft.SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------SysNotify push--------------------')
        ret, data = super(SysNotifyTest, self).on_recv_rsp(rsp_pb)
        log.info('SysNotify push ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('SysNotify push error')
            return ret, data
        return ret, data


class OrderBookTest(ft.OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_str):
        ret, data = super(OrderBookTest, self).on_recv_rsp(rsp_str)
        # log.info('实时摆盘推送，ret: %s, data:%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('OrderBook push error，ret: %s, data:%s' % (ret, data))
            return ret, data
        glb['order_book'][data['code']] = data
        return ret, data


def auto_place_order(code, volume, price):
    if glb['auto_place_order_flag']:
        log.info('auto_place_order_flag True')
        return False
    if price > conf['CUR_PRICE_MAX']:
        return False
    if glb['almost_over']:
        glb['auto_place_order_flag'] = True
        data = smart_sell(code, volume)
        if data is False:
            log.info('auto_place_order => smart_sell error')
        glb['auto_place_order_flag'] = False
        return
    if volume < 100e3:
        return False
    # if glb['submitted_sell_bull'] is not None and glb['submitted_sell_bull'].code == code:
    #     return False
    # if glb['submitted_sell_bear'] is not None and glb['submitted_sell_bear'].code == code:
    #     return False
    glb['auto_place_order_flag'] = True
    item = []
    # conf['ORDER_LIST'] = [[400e3, 200e3, 2, 3],
    #     [200e3, 100e3, 2, 3],
    #     [100e3, 50e3, 2, 3]]            # 下单多少股以上（大的写前面），每单挂多少股，一单挂高几格，下一单挂高几格
    for i in range(0, len(conf['ORDER_LIST'])):
        if volume >= conf['ORDER_LIST'][i][0]:
            item = conf['ORDER_LIST'][i]
            break
    if glb['force_replacing']:
        price += 0.02
    for i in range(0, len(item) - 2):
        data = smart_sell(code, item[1], price + 0.001 * item[2 + i])
        if data is False:
            log.info('auto_place_order => smart_sell error')
        elif glb['force_replacing']:
            glb['force_replacing'] = False
    glb['auto_place_order_flag'] = False


class TradeOrderTest(ft.TradeOrderHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        log.info('--------------------TradeOrder--------------------')
        ret, data = super(TradeOrderTest, self).on_recv_rsp(rsp_pb)
        log.info('TradeOrder ret: %s, data:\n%s' % (ret, data))
        if ret != ft.RET_OK:
            log.info('TradeOrder error')
            return ret, data
        data = data.iloc[0]
        if data.trd_env != conf['TRADE_ENV']:
            log.info('TradeOrder not TRADE_ENV')
            return ret, data
        if data.order_status == ft.OrderStatus.FILLED_ALL:
            glb['last_filled_all_order'][data.code] = {'create_time': data.create_time, 'price': data.price}
            if data.trd_side == ft.TrdSide.BUY:
                log.info('TradeOrder FILLED_ALL buy')
                reset_submitted_buy(data.code, data.stock_name)
                set_has(data.code, data.stock_name)
                if conf['AUTO_PLACE_ORDER'] and not glb['to_over']:
                    if data.stock_name.find('熊') > -1 or (data.stock_name.find('牛') > -1 and conf['BULL_CODE'] == 'auto'):
                        time.sleep(2)
                        auto_place_order(data.code, data.dealt_qty, data.price)
            elif data.trd_side == ft.TrdSide.SELL:
                log.info('TradeOrder FILLED_ALL sell')
                reset_submitted_sell(data.code, data.stock_name, data)
                position_list_query()
        elif data.order_status == ft.OrderStatus.FILLED_PART:
            if data.trd_side == ft.TrdSide.BUY:
                log.info('TradeOrder FILLED_PART buy')
                set_has(data.code, data.stock_name)
            elif data.trd_side == ft.TrdSide.SELL:
                log.info('TradeOrder FILLED_PART sell')
        elif data.order_status == ft.OrderStatus.SUBMIT_FAILED or data.order_status == ft.OrderStatus.FAILED:
            log.info('TradeOrder SUBMIT_FAILED or FAILED')
            position_list_query()
        elif data.order_status == ft.OrderStatus.CANCELLED_ALL or data.order_status == ft.OrderStatus.CANCELLED_PART:
            log.info('TradeOrder CANCELLED_ALL or CANCELLED_PART')
            if data.trd_side == ft.TrdSide.BUY:
                reset_submitted_buy(data.code, data.stock_name)
            elif data.trd_side == ft.TrdSide.SELL:
                reset_submitted_sell(data.code, data.stock_name, data)
        elif data.order_status == ft.OrderStatus.SUBMITTED:
            log.info('TradeOrder %s SUBMITTED' % data.trd_side)
            if data.trd_side == ft.TrdSide.BUY:
                set_submitted_buy(data.code, data.stock_name, data)
            elif data.trd_side == ft.TrdSide.SELL:
                set_submitted_sell(data.code, data.stock_name, data)
        else:
            log.info('TradeOrder %s' % data.order_status)

        return ret, data


# class RTDataTest(ft.RTDataHandlerBase):
#     def on_recv_rsp(self, rsp_str):
#         # log.info('--------------------分时推送--------------------')
#         ret, data = super(RTDataTest, self).on_recv_rsp(rsp_str)
#         if ret != ft.RET_OK:
#             log.info('分时推送error')
#             return ret, data
#         #    code                 time      is_blank    opened_mins  cur_price  last_close     avg_price  turnover  volume
#         # 0  HK.800000  2019-08-14 13:01:00     False          781   25416.63     25281.3  25482.145921  660739.0       0
#         glb['rt_data'] = data.iloc[0]

#         return ret, data


def auto_adjust(delta_price, i, adjust_dict, submitted_type):
    data = glb[submitted_type]
    if data is None or data.code not in glb['order_book'] or (submitted_type.find('buy') > -1 and data.code not in glb['auto_buy_list']):
        return False
    order_book = glb['order_book'].get(data.code)
    bid_price = order_book['Bid'][0][0]
    ask_price = order_book['Ask'][0][0]
    if bid_price >= conf['CUR_PRICE_MAX']:
        return False
    rise_price = 0
    fall_price = 0
    if submitted_type.find('buy') > -1:
        rise_price = round(bid_price - (adjust_dict['rise'][2] - 1) * 0.001, 3)
        fall_price = round(bid_price - (adjust_dict['fall'][2] - 1) * 0.001, 3)
    elif submitted_type.find('sell') > -1:
        rise_price = round(ask_price + (adjust_dict['rise'][2] - 1) * 0.001, 3)
        fall_price = round(ask_price + (adjust_dict['fall'][2] - 1) * 0.001, 3)
    rise_condition = False
    fall_condition = False
    if submitted_type.find('bull') > -1:
        rise_condition = delta_price >= adjust_dict['rise'][1]
        fall_condition = delta_price <= -adjust_dict['fall'][1]
    elif submitted_type.find('bear') > -1:
        rise_condition = delta_price <= -adjust_dict['rise'][1]
        fall_condition = delta_price >= adjust_dict['fall'][1]
    # 要买入的时候才考虑升档，要卖出的时候只考虑降档
    if rise_condition and submitted_type.find('buy') > -1:
        delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['adjust_ticker_list'][i].get('time'))
        if delta_seconds <= adjust_dict['rise'][0] and data.price < rise_price:
            log.info('order price: %s, rise_price: %s' % (data.price, rise_price))
            data.price = rise_price
            modify_order(data.order_id, rise_price, data.qty)
    elif fall_condition:
        delta_seconds = datestr_to_timestamp(glb['adjust_ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['adjust_ticker_list'][i].get('time'))
        if delta_seconds <= adjust_dict['fall'][0] and data.price > fall_price:
            log.info('order price: %s, fall_price: %s' % (data.price, fall_price))
            data.price = fall_price
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
        auto_adjust(delta_price, i, conf['ADJUST_BUY_DICT'], 'submitted_buy_bear')
        auto_adjust(delta_price, i, conf['ADJUST_BUY_DICT'], 'submitted_buy_bull')
    # 快收盘清仓的时候才自动调价卖出
    if conf['AUTO_ADJUST_SELL'] and glb['almost_over']:
        auto_adjust(delta_price, i, conf['ADJUST_SELL_DICT'], 'submitted_sell_bear')
        auto_adjust(delta_price, i, conf['ADJUST_SELL_DICT'], 'submitted_sell_bull')


def _get_stock_code(stock_type='all', cache_first=False):
    cache = glb['cache_get_stock_code'].get(stock_type)
    if cache_first and cache['data'] is not None and time.time() - cache['last_time'] < cache['duration']:
        log.info('读取缓存数据：%s' % cache)
        return cache['data']
    cache['data'] = False

    req = ft.WarrantRequest()
    req.stock_owner = HSI_CODE  # 所属正股
    if stock_type == 'bull':
        req.type_list = [ft.WrtType.BULL]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    elif stock_type == 'bear':
        req.type_list = [ft.WrtType.BEAR]  # Qot_Common.WarrantType, 窝轮类型过滤列表 WrtType
    # req.issuer_list = [ft.Issuer.JP]  # Qot_Common.Issuer, 发行人过滤列表
    req.status = ft.WarrantStatus.NORMAL  # Qot_Common.WarrantStatus, 窝轮状态
    req.cur_price_min = conf['CUR_PRICE_MIN']  # 最新价过滤起点
    req.cur_price_max = conf['CUR_PRICE_MAX']  # 最新价过滤终点
    req.conversion_min = 10000  # 换股比率过滤起点
    req.conversion_max = 10000  # 换股比率过滤终点
    req.vol_min = 1000  # 成交量的过滤下限，单位K
    req.sort_field = ft.SortField.VOLUME  # 根据哪个字段排序
    req.ascend = False  # 升序ture, 降序false
    req.begin = 0  # 数据起始点
    req.num = 3  # 返回数据个数，最大200

    ret, data = quote_ctx.get_warrant(req=req)
    log.info('get_warrant, ret: %s, data:\n%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('get_warrant error')
    else:
        data = data[0]
        data = data[data.stock_owner == HSI_CODE] # 坑，返回的结果还要再过滤一次
        # data = data[data.cur_price == min(data.cur_price)]
        if len(data) > 0:
            data = data.iloc[0]
            bid_ask_diff = data.ask_price - data.bid_price
            if data.ask_price != 0 and (bid_ask_diff < conf['BID_ASK_DIFF'] or math.isclose(bid_ask_diff, conf['BID_ASK_DIFF'])):
                log.info('bid_price: %s, ask_price: %s, diff: %s <= %s, allow buy' % (data.bid_price, data.ask_price, bid_ask_diff, conf['BID_ASK_DIFF']))
                cache['data'] = data
            else:
                log.info('bid_price: %s, ask_price: %s, diff: %s > %s, not allow buy' % (data.bid_price, data.ask_price, bid_ask_diff, conf['BID_ASK_DIFF']))
        else:
            log.info('_get_stock_code error, conditions not met')
    cache['last_time'] = time.time()
    return cache['data']


def to_buy(stock_type, volume=None, force=False):
    if volume is None:
        volume = conf['BUY_VOLUME']
        if glb['afternoon']:
            volume /= 2
    code = ''
    if stock_type == 'bull':
        code = conf['BULL_CODE']
    elif stock_type == 'bear':
        code = conf['BEAR_CODE']
    if code == '':
        return False

    if force is False:
        data = position_list_query(stock_type=stock_type)
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
                reference_price = glb['last_filled_all_order'].get(data0.code, {}).get('price')
                if not reference_price:
                    log.info('code: %s, no last_filled_all_order，\n%s' % (data0.code, glb['last_filled_all_order']))
                    reference_price = data0.cost_price
                add_price_diff = round(reference_price - data0.nominal_price, 3)
                if add_price_diff < conf['ADD_PRICE_DIFF']:
                    log.info('code: %s, nominal_price: %s, reference_price: %s, diff: %s < %s, not allow add' % (data0.code, data0.nominal_price, reference_price, add_price_diff, conf['ADD_PRICE_DIFF']))
                    if conf['FOLLOW_TREND']:
                        if stock_type == 'bull':
                            glb['pre_buy_bull_flag'] = False
                        elif stock_type == 'bear':
                            glb['pre_buy_bear_flag'] = False
                    return False
                log.info('code: %s, nominal_price: %s, reference_price: %s, diff: %s >= %s, allow add' % (data0.code, data0.nominal_price, reference_price, add_price_diff, conf['ADD_PRICE_DIFF']))

    if code == 'auto':
        data = get_stock_code(stock_type=stock_type)
        if data is False or data is None:
            return False
        code = data.stock

    set_submitted_buy(code, glb['stock_name'][stock_type])
    if force:
        data = smart_buy(code, volume, type='Ask')
    else:
        data = smart_buy(code, volume)
    if data is False or data is None:
        reset_submitted_buy(code, glb['stock_name'][stock_type])
    else:
        add_unique_element(glb['auto_buy_list'], code)
        # 刚买入，先设置别追买，要等待时机才买
        if stock_type == 'bull':
            glb['pre_buy_bull_flag'] = False
        elif stock_type == 'bear':
            glb['pre_buy_bear_flag'] = False
    return data


def auto_buy(stock_type):
    # log.info('auto_buy，submitted_buy_bear_flag：%s' % glb['submitted_buy_bear_flag'])
    if stock_type == 'bull' and not glb['submitted_buy_bull_flag'] and (conf['ALLOW_ADD'] or len(glb['has_bull_list']) == 0):
        glb['pre_buy_bear_flag'] = True
        if conf['BULL_CODE'] == '':
            return False
        if not glb['pre_buy_bull_flag']:
            # log.info('not pre_buy_bull_flag')
            return False
        if not conf['CHECK_GOLDEN_LINE'] or check_golden_line() == 'bull':
            log.info('to buy bull')
            to_buy('bull')
    elif stock_type == 'bear' and not glb['submitted_buy_bear_flag'] and (conf['ALLOW_ADD'] or len(glb['has_bear_list']) == 0):
        glb['pre_buy_bull_flag'] = True
        if conf['BEAR_CODE'] == '':
            return False
        if not glb['pre_buy_bear_flag']:
            # log.info('not pre_buy_bear_flag')
            return False
        if not conf['CHECK_GOLDEN_LINE'] or check_golden_line() == 'bear':
            log.info('to buy bear')
            to_buy('bear')


def pre_buy():
    #       code              time                 price        volume  turnover    ticker_direction       sequence   type      push_data_type
    # 0     HK_FUTURE.999010  2019-03-01 00:59:55  28655.0       1   28655.0              BUY  6663097136416030721  AUTO_MATCH          CACHE
    while datestr_to_timestamp(glb['ticker_list'][-1].get('time')) - datestr_to_timestamp(glb['ticker_list'][0].get('time')) > conf['DELTA_SECONDS']:
        glb['ticker_list'].pop(0)
    # if glb['ticker_list'][-1][1][-2:] != '00':
    #     return False
    delta_price = glb['ticker_list'][-1].get('price') - glb['ticker_list'][0].get('price')
    # 60秒内上涨点数比预设点数还要大
    if delta_price >= conf['DELTA_PRICE']:
        if conf['FOLLOW_TREND']:
            auto_buy('bull')
        else:
            auto_buy('bear')
    # 60秒内下跌点数比预设点数还要小
    elif delta_price <= -conf['DELTA_PRICE']:
        if conf['FOLLOW_TREND']:
            auto_buy('bear')
        else:
            auto_buy('bull')


class TickerTest(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_str):
        # log.info('--------------------逐笔明细--------------------')
        ret, data = super(TickerTest, self).on_recv_rsp(rsp_str)
        if ret != ft.RET_OK:
            log.info('ticker push error')
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
            if h == 9 and m == 15 and not glb['restarted']:
                log.info('[%s]soon to start, need to resetData' % t)
                glb['restarted'] = True
                resetData()
            elif h == 16 and m == 0 and s == 0:
                log.info('[%s]--------------------end--------------------' % t)
            return ret, data

        if h == 9 and m == 30 and glb['restarted']:
            log.info('[%s]--------------------start--------------------' % t)
            glb['restarted'] = False
        elif h >= 13 and not glb['afternoon']:
            glb['afternoon'] = True

        if glb['trade_date'].get('trade_date_type') == 'MORNING' and h == 11 or h == 15:
            if ((len(glb['has_bull_list']) == 0 and len(glb['has_bear_list']) == 0) or
                (glb['golden_line']['reverse'] == 'bull' and len(glb['has_bull_list']) == 0) or
                (glb['golden_line']['reverse'] == 'bear' and len(glb['has_bear_list']) == 0)):
                    glb['soon_over'] = True
            elif m >= 30:
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

        # 有持仓的时候，每一分钟查询分割线，每波动10点查询持仓列表
        glb['cur_price'] = data0.price
        if (len(glb['has_bull_list']) > 0 or len(glb['has_bear_list']) > 0):
            if data0.get('time')[-2:] == '00' and conf['CHECK_GOLDEN_LINE']:
                check_golden_line()
            if abs(glb['cur_price'] - glb['last_price']) >= 10:
                glb['last_price'] = glb['cur_price']
                position_list_query(logging=False)

        # 自动买入和自动调价
        if conf['AUTO_BUY'] or conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']:
            for index, row in data.iterrows():
                if conf['AUTO_BUY'] and not glb['soon_over']:
                    glb['ticker_list'].append(row)
                if conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']:
                    glb['adjust_ticker_list'].append(row)
            # 尾盘就不买了
            if conf['AUTO_BUY'] and not glb['soon_over']:
                pre_buy()
            # 自动调价
            if conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']:
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
        glb['restarted'] = False
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
    if conf['FOLLOW_TREND']:
        glb['pre_buy_bull_flag'] = False
        glb['pre_buy_bear_flag'] = False
        conf['ADJUST_BUY_DICT']['rise'][2] = 0
    else:
        glb['pre_buy_bull_flag'] = True
        glb['pre_buy_bear_flag'] = True
        conf['ADJUST_BUY_DICT']['rise'][2] = 1
    request_trading_days()


# 限制3秒内最多查1次足够
check_golden_line = throttle(_check_golden_line, 3)
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
            glb['restarted'] = False
            log.info('unlock_trade error')
            return False
    data = subscribe([MHI_CODE], [ft.SubType.TICKER])
    if data is False:
        glb['restarted'] = False
        return False
    quote_ctx.set_handler(SysNotifyTest())
    quote_ctx.set_handler(TickerTest())
    trade_ctx.set_handler(TradeOrderTest())
    if conf['AUTO_ADJUST_BUY'] or conf['AUTO_ADJUST_SELL']:
        quote_ctx.set_handler(OrderBookTest())
    position_list_query()
    order_list_query(status=ft.OrderStatus.FILLED_ALL)
    # get_stock_code('熊')
    if conf['CHECK_GOLDEN_LINE']:
        data = subscribe([HSI_CODE], [ft.SubType.RT_DATA], subscribe_push=False)
        if data is False:
            glb['restarted'] = False
            return False
        check_golden_line()

    ret, data = quote_ctx.query_subscription()
    log.info('query_subscription, ret: %s, data:%s' % (ret, data))
    if ret != ft.RET_OK:
        log.info('query_subscription error')
    quote_ctx.start()

    # ticker_test = TickerTest()
    # ticker_test.on_recv_rsp()

    if temp_quote_ctx is not None:
        temp_quote_ctx.close()
        temp_trade_ctx.close()
        log.info('restart success')

