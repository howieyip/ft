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


code = 'HK.51539'
start = '2024-10-21'
end = start
max_count = 500

buy_price = 0.115
last_filled_price = buy_price
per_volume = 50e5
diff1 = 0.01
diff2 = 0.004
sell_times = 0
buy_times = 0
sum = 0
money = 0

def cal(data):
    _cal(data, diff1)
    _cal(data, diff2)
    log.info('*************************************')

def _cal(data, diff):
    global last_filled_price, sell_times, buy_times, sum
    last_filled_price = buy_price
    sell_times = 0
    buy_times = 0
    sum = 0
    for index, row in data.iterrows():
        _diff = round(row.close - last_filled_price, 3)
        if _diff >= diff:
            sum = round(sum + _diff, 3)
            last_filled_price = row.close
            sell_times += 1
            # log.info('time: %s, sell: %s, _diff: %s' % (row.time_key, last_filled_price, _diff))
        elif _diff <= -diff:
            last_filled_price = row.close
            buy_times += 1
            # log.info('time: %s, buy: %s, _diff: %s' % (row.time_key, last_filled_price, _diff))
    log.info('buy_volume: %s, diff: %s, buy_times: %s, sell_times: %s, sum: %s, money: %s' % (per_volume*diff, diff, buy_times, sell_times, sum*1e3, sum*per_volume*diff - sell_times*20))

quote_ctx = ft.OpenQuoteContext(host=conf['HOST'], port=conf['PORT'])
trade_ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.HK, host=conf['HOST'], port=conf['PORT'])
ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, max_count=max_count, ktype=ft.KLType.K_1M)  # 每页5个，请求第一页
if ret == ft.RET_OK:
    # log.info(data)
    cal(data.iloc[1:])
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
# log.info('buy_volume: %s, diff: %s, buy_times: %s, sell_times: %s, sum: %s, money: %s' % (per_volume*diff, diff, buy_times, sell_times, sum*1e3, sum*per_volume*diff - sell_times*20))
quote_ctx.close() # 结束后记得关闭当条连接，防止连接条数用尽
