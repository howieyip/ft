import threading

class Timer:
    def __init__(self, fn, count=5, delay=2, *args, **kwargs):
        self.fn = fn
        self.count = count
        self.delay = delay
        self.args = args
        self.kwargs = kwargs
        self.running = True

    def clearTimeoutHandler(self):
        self.running = False

    def repeat(self):
        def wrapper(index):
            if index < self.count:
                if self.running:
                    self.fn(index=index, *self.args, **self.kwargs)
                    self.setTimeout(wrapper, self.delay, index + 1)
            else:
                self.running = False
        wrapper(0)

    def setTimeout(self, fn, delay=2, *args, **kwargs):
        timer = threading.Timer(delay, fn, args=args, kwargs=kwargs)
        timer.start()
        return timer


# order_list = [{'code':'1','price':1}, {'code':'2','price':4}, {'code':'3','price':9}, {'code':'4','price':13}]
# glb = {
#     'stop': False,
#     'timer': None,
#     'EVERY_ORDER_DIFF': 2,
# }


# def stop():
#     glb['stop'] = True


# def modify_order2(index, order_list, price):
#     order = order_list[index]
#     if glb['stop']:
#         print('modify_order %s warning, auto_place_order' % order['code'])
#         glb['timer'].clearTimeoutHandler()
#         print('running: %s' % glb['timer'].running)
#         return False
#     print('running: %s' % glb['timer'].running)
#     price2 = price + glb['EVERY_ORDER_DIFF'] * (index + 1)
#     if price2 < order['price']:
#         print('modify_order %s success, old price: %s, new price: %s' % (order['code'], order['price'], price2))
#     else:
#         print('modify_order %s error, old price: %s, new price: %s' % (order['code'], order['price'], price2))


# def loss_order(order_list):
#     order_list2 = order_list[:] # 用新的数组，因为旧的成交了就会变化
#     price = order_list2[0]['price']
#     order_list2 = order_list2[1:]
#     for i in range(0, len(order_list2)):
#         order = order_list2[i]
#         price2 = price + glb['EVERY_ORDER_DIFF'] * (i + 1)
#         if price2 < order['price']:
#             glb['timer'] = Timer(modify_order2, count=len(order_list2) - i, delay=2, order_list=order_list2[i:], price=price + glb['EVERY_ORDER_DIFF'] * i)
#             glb['timer'].repeat()
#             break


# loss_order(order_list)
# glb['timer'].setTimeout(stop, 3)
