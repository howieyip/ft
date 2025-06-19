import datetime
import futu as ft
from logger import Logger

conf = {
    'log_file': 'logs/fight.log',
    'TRADE_ENV': ft.TrdEnv.REAL,                          # 实盘交易：REAL，模拟交易：SIMULATE
    'PASSWORD_MD5': 'd7866f93b87fc9c1b0a06a6a6669bada',   # 优先使用 PASSWORD_MD5 解锁
    'PASSWORD': '',                                       # 如果PASSWORD_MD5为空，则使用 PASSWORD 解锁
    'HOST': '127.0.0.1',
    'PORT': 11111,
    'acc_id': 281756481226004224,
}
log = Logger(conf['log_file']).get_logger()


code = 'HK.MHImain'
max_count = 16*60 + 1
start = datetime.date.today().strftime('%Y-%m-%d')
# start = '2025-02-10'
end = start
# end = '2024-10-08'
glb = {
    'line': {
        'pre_min_price': 99999,
        'pre_max_price': 0,
    },
    'klines': None,
    'golden_line': {}
}


def get_cur_kline(num=80, begin=None):
    klines = glb['klines']
    if begin is not None:
        klines = klines[(klines.time_key.str[11:19] > begin) & (klines.time_key.str[11:19] < '16:00:00')]
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
        # log.info('draw_line error, klines:\n%s' % klines)
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
    # log.info('draw_line: %s' % line)
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


def get_pre_inflection(klines, line):
    line['pre_min_price'] = 0
    line['pre_max_price'] = 0
    for i in range(-3, -len(klines) + 1, -1):
        pre_min_price = klines.iloc[i].close
        if klines.iloc[i - 2].close >= pre_min_price and klines.iloc[i - 1].close >= pre_min_price <= klines.iloc[i + 1].close and pre_min_price <= klines.iloc[i + 2].close:
            line['pre_min_price'] = pre_min_price
            line['pre_min_time'] = klines.iloc[i].time_key
        pre_max_price = klines.iloc[i].close
        if klines.iloc[i - 2].close <= pre_max_price and klines.iloc[i - 1].close <= pre_max_price >= klines.iloc[i + 1].close and pre_max_price >= klines.iloc[i + 2].close:
            line['pre_max_price'] = pre_max_price
            line['pre_max_time'] = klines.iloc[i].time_key
        if line['pre_min_price'] > 0 and line['pre_max_price'] > 0:
            break
    return line


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
        elif last_kline.low - line['lower'] < 5:
            if last_kline.close > line['long'] and delta_price > -kline_len*3:
                check_result = 'wave_bull'
            else:
                check_result = 'wait_long_wave'
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
        elif last_kline.high - line['upper'] > -5:
            if last_kline.close < line['long'] and delta_price < kline_len*3:
                check_result = 'wave_bear'
            else:
                check_result = 'wait_short_wave'
        else:
            check_result = 'wait_short_trend'
    else:
        check_result = 'not_near_bands'
    return check_result


def cal(klines):
    if klines.empty:
        log.info('empty')
        return False
    delta = round(klines.iloc[-1]['close'] - klines.iloc[0]['close'], 3)
    log.info('-------------------- %s -------------------- %s' % (klines.iloc[0]['time_key'], delta))
    for index, row in klines.iterrows():
        glb['klines'] = klines[0:index+1]
        # if row.time_key == '2025-06-19 10:15:00':
        #     log.info('draw_line: %s' % glb['line'])
        check_result = check_line()
        if 'bull' in check_result or 'bear' in check_result:
            log.info('draw_line: %s' % glb['line'])
            # log.info('golden_line: %s' % glb['golden_line'])
            log.info('*************** %s %s ***************' % (row.time_key, check_result))



def request(start, end=None):
    if end is None:
        end = start
    ret, klines, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M)
    if ret == ft.RET_OK:
        # log.info(klines)
        cal(klines)
    else:
        log.info('error:', klines)
    while page_req_key != None:
        log.info('******************************')
        ret, klines, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M, page_req_key=page_req_key)
        if ret == ft.RET_OK:
            # log.info(klines)
            cal(klines)
        else:
            log.info('error:', klines)


quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
request(start, end)
quote_ctx.close()
