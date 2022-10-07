import os
import datetime
import pandas as pd
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)
import futu as ft
quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
quote_ctx.subscribe(['HK.00700'], [ft.SubType.ORDER_BOOK])
print(quote_ctx.get_order_book('HK.00700'))
quote_ctx.close()

def append_data(dict_list, key, data):
    is_added = False
    for i in range(0, len(dict_list)):
        if dict_list[i][key] == data[key]:
            is_added = True
            break
    if not is_added:
        dict_list.append(data)


def del_data(dict_list, key, data):
    for i in range(0, len(dict_list)):
        if dict_list[i][key] == data[key]:
            del dict_list[i]
            break


print(0.058-0.057)
a = 5
print(1 < a < 3)
a = dict({'a': 1, 'b': 2})
c = []
append_data(c, 'a', a)
append_data(c, 'a', a)
print(c)
c[0] = 1
print(c)

today = datetime.date.today()
first_day = datetime.date(today.year, today.month, 1)
last_day = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
print(today.strftime('%Y-%m-%d'), first_day, last_day, datetime.timedelta(1))
dict = {'HK.61776':1}
print(dict)
print(len(dict))
print('Name' in dict)
dict.clear()
print(len(dict))
str = '恒指摩通九六熊E'
print(str[0:2])
print(str.find('熊'))
arr = [['HK_FUTURE.999010', '2019-03-25 15:52:20', 28478.0, 1, 28478.0, 'BUY', 6672233154624880646, 'AUTO_MATCH', 'REALTIME'], ['HK_FUTURE.999010', '2019-03-25 15:52:20', 28478.0, 1, 28478.0, 'BUY', 6672233154624880647, 'AUTO_MATCH', 'REALTIME']]
data = pd.DataFrame(arr, columns=['a', 'b', 'c', 'd','e','f','g','h','i'])
data = data[(data['d'] > 0) & (data['f'] == 'BUY')]
print(data)
print(data.d.tolist())
columns = data.columns.tolist()
print(columns)
print(columns.index('d'))
arr = data.values.tolist()