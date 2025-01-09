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
start = '2025-01-08'
end = start
# end = '2024-10-08'
glb = {
    'line': {}
}

def boll_bands(kline_data):
    mid = round(kline_data['close'].mean(), 3)
    std = kline_data['close'].std(ddof=0)
    upper = round(mid + 2 * std, 3)
    lower = round(mid - 2 * std, 3)
    return {'mid': mid, 'upper': upper, 'lower': lower}


def draw_line():
    kline_data = glb['kline_data']
    if kline_data is False or len(kline_data) < 20:
        return False
    line = glb['line']
    line['cur'] = kline_data.iloc[-1].close
    line['10'] = round(kline_data[-10:]['close'].mean(), 3)
    line['long'] = round(kline_data[-80:]['close'].mean(), 3)
    last_boll_bands = boll_bands(kline_data[-20:])
    last2_boll_bands = boll_bands(kline_data[-21:-1])
    last3_boll_bands = boll_bands(kline_data[-22:-2])
    line['mid'] = last_boll_bands['mid']
    line['upper'] = last_boll_bands['upper']
    line['lower'] = last_boll_bands['lower']
    line['upper2'] = last2_boll_bands['upper']
    line['lower2'] = last2_boll_bands['lower']
    line['upper3'] = last3_boll_bands['upper']
    line['lower3'] = last3_boll_bands['lower']
    # log.info('draw_line: %s' % line)
    return line


def check_line():
    line = draw_line()
    if line is False:
        return ''
    check_result = ''
    #            code         name             time_key     open    close     high      low  volume  turnover  pe_ratio  turnover_rate  last_close
    # 0   HK.MHImain  小恒指主连(2406)  2024-06-15 02:42:00  17773.0  17772.0  17773.0  17769.0      18  319883.0       0.0            0.0     17772.0
    last_kline = glb['kline_data'].iloc[-1]
    last2_kline = glb['kline_data'].iloc[-2]
    last3_kline = glb['kline_data'].iloc[-3]
    delta_price = last_kline.close - last_kline.last_close
    near_long = line['10'] > line['mid']
    near_short = line['10'] < line['mid']
    far_long = line['lower'] > line['long']
    far_short = line['upper'] < line['long']
    if line['upper'] - line['lower'] < 25:
        check_result = 'bands_narrow'
    elif abs(last_kline.close - line['long']) < 20:
        check_result = 'close_long'
    elif (last_kline.low - line['lower'] < 10 or last2_kline.low - line['lower2'] < 10 or last3_kline.low - line['lower3'] < 10) and last_kline.close - line['mid'] < -10:
        if (far_long and near_long or not far_short and not far_long) and delta_price > -20:
            check_result = 'wave_bull'
        elif far_short and delta_price > 0:
            if last_kline.close > last3_kline.high and last2_kline.close > last3_kline.open > last2_kline.open and last3_kline.close < last3_kline.open and abs(last3_kline.close - last3_kline.open) >=10:
                check_result = 'long_swallow1_bull'
            elif last_kline.close > last3_kline.high and last2_kline.close < last2_kline.open and last3_kline.close < last3_kline.open and abs(last2_kline.close - last2_kline.open + last3_kline.close - last3_kline.open) >= 10:
                check_result = 'long_swallow2_bull'
            elif last2_kline.close > last2_kline.low and abs(last2_kline.close - last2_kline.open) / (last2_kline.close - last2_kline.low) < 1/3 and last2_kline.high - last2_kline.close / (last2_kline.close - last2_kline.low) < 1/3 and abs(last2_kline.high - last2_kline.low) >=10:
                check_result = 'long_pinba_bull'
            else:
                check_result = 'wait_long_signal'
        else:
            check_result = 'wait_long_trend'
    elif (last_kline.high - line['upper'] > -10 or last2_kline.high - line['upper2'] > -10 or last3_kline.high - line['upper3'] > -10) and last_kline.close - line['mid'] > 10:
        if (far_short and near_short or not far_short and not far_long) and delta_price < 20:
            check_result = 'wave_bear'
        elif far_long and delta_price < 0:
            if last_kline.close < last3_kline.low and last2_kline.close < last3_kline.open < last2_kline.open and last3_kline.close > last3_kline.open and abs(last3_kline.close - last3_kline.open) >=10:
                check_result = 'short_swallow1_bear'
            elif last_kline.close < last3_kline.low and last2_kline.close > last2_kline.open and last3_kline.close > last3_kline.open and abs(last2_kline.close - last2_kline.open + last3_kline.close - last3_kline.open) >= 10:
                check_result = 'short_swallow2_bear'
            elif last2_kline.high > last2_kline.close and abs(last2_kline.close - last2_kline.open) / (last2_kline.high - last2_kline.close) < 1/3 and last2_kline.close - last2_kline.low / (last2_kline.high - last2_kline.close) < 1/3 and abs(last2_kline.high - last2_kline.low) >=10:
                check_result = 'short_pinba_bear'
            else:
                check_result = 'wait_short_signal'
        else:
            check_result = 'wait_short_trend'
    else:
        check_result = 'not_near_bands'
    line['check_result'] = check_result
    return check_result


def cal(data):
    if data.empty:
        log.info('empty')
        return False
    delta = round(data.iloc[-1]['close'] - data.iloc[0]['close'], 3)
    log.info('**************** %s ********************* %s' % (data.iloc[0]['time_key'], delta))
    for index, row in data.iterrows():
        glb['kline_data'] = data[0:index+1]
        # if row.time_key == '2025-01-08 11:53:00':
        #     log.info('debugger')
        check_result = check_line()
        if 'bull' in check_result or 'bear' in check_result:
            log.info('%s %s' % (row.time_key, glb['line']))



def request(start, end=None):
    if end is None:
        end = start
    ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M)  # 每页5个，请求第一页
    if ret == ft.RET_OK:
        # log.info(data)
        cal(data)
    else:
        log.info('error:', data)
    while page_req_key != None:
        log.info('*************************************')
        ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M, page_req_key=page_req_key) # 请求翻页后的数据
        if ret == ft.RET_OK:
            # log.info(data)
            cal(data)
        else:
            log.info('error:', data)


quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
request(start, end)
quote_ctx.close()
