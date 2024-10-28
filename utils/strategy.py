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


code = 'HK.50063'
max_count = 331
start = '2024-03-01'
end = start
end = '2024-03-30'
need_log = False
last_filled_price1 = 0
last_filled_price2 = 0
last_day_filled_price = 0
per_volume = 10e3/0.002
diff1 = 0.004
diff2 = 0.01
sell_times = 0
buy_times = 0
sum = 0
delta_times1 = 0
delta_times2 = 0
money1 = 0
money2 = 0


def cal(data):
    global last_filled_price1, last_filled_price2, money1, money2, delta_times1, delta_times2
    data = data.iloc[1:]
    if data.empty:
        log.info('empty')
        return False
    delta = round(data.iloc[-1]['close'] - data.iloc[0]['close'], 3)*1e3
    log.info('**************** %s ********************* %s' % (data.iloc[0]['time_key'], delta))
    last_filled_price1, d1, m1 = _cal(data, diff1, last_filled_price1)
    delta_times1 += d1
    money1 += m1
    last_filled_price2, d2, m2 = _cal(data, diff2, last_filled_price2)
    delta_times2 += d2
    money2 += m2


def _cal(data, diff, last_filled_price):
    global sell_times, buy_times, sum
    if last_filled_price == 0:
      last_filled_price = data.iloc[0]['close']
    sell_times = 0
    buy_times = 0
    sum = 0
    for index, row in data.iterrows():
        _diff = round(row.close - last_filled_price, 3)
        if _diff >= diff:
            sum = round(sum + _diff, 3)
            last_filled_price = row.close
            sell_times += 1
            if need_log:
                log.info('time: %s, sell: %s, _diff: %s' % (row.time_key, last_filled_price, _diff))
        elif _diff <= -diff:
            last_filled_price = row.close
            buy_times += 1
            if need_log:
                log.info('time: %s, buy: %s, _diff: %s' % (row.time_key, last_filled_price, _diff))
    buy_volume = per_volume*diff
    money = sum*buy_volume - sell_times*20
    delta_times = sell_times - buy_times
    log.info('buy_volume: %s, diff: %s, buy_times: %s, sell_times: %s, delta_times: %s, last_filled_price: %s, money: %s' % (buy_volume, diff, buy_times, sell_times, delta_times, last_filled_price, money))
    return last_filled_price, delta_times, money


def request(start, end=None):
    if end is None:
        end = start
    ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M)  # 每页5个，请求第一页
    if ret == ft.RET_OK:
        # log.info(data)
        cal(data)
    else:
        log.info('error:', data)
    while page_req_key != None:  # 请求后面的所有结果
        log.info('*************************************')
        ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M, page_req_key=page_req_key) # 请求翻页后的数据
        if ret == ft.RET_OK:
            # log.info(data)
            cal(data)
        else:
            log.info('error:', data)


quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
trade_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.HK, host=conf['HOST'], port=conf['PORT'])
request(start, end)
log.info('money1: %s, money2: %s, delta_times1: %s, delta_times2: %s' % (money1, money2, delta_times1, delta_times2))
quote_ctx.close() # 结束后记得关闭当条连接，防止连接条数用尽
