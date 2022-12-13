import logging
import datetime
from binance.futures import Futures as Client
from binance.lib.utils import config_logging
from binance.error import ClientError
import time
import requests
import json

keyV1 = ""
secretV1 = ""


symbol = "BTCBUSD"  # **币种
baseQuantity = 0.002  # **基础下单数量
spacing = 38  # **基础格距
pre = 1  # **价格精度
u = 0.005  # **多仓最大限量
d = 0.1  # **空仓最大限量
s = 0  # **持仓超限后减仓系数,大于0将以市价减少 s*baseQuantity 仓位，如为0将挂一小平仓单等待
timeOut = 2000  # **每隔这么长时间重置一次格距
finishNumber = 2  # **或者每成交这么多次重置一次格距
recordsTime = '5m'  # **以此时间周期K线计算格距

# -----------------------------------------------------------
D = 0
Taker = 0
CutDownB = 0
CutDownS = 0
Price = 0

# ----------------------------------------------------------
# Account 账户信息对象
# client.get_position_risk(symbol=symbol) 查询持仓
client = Client(keyV1, secretV1, base_url="https://fapi.binance.com")


# Trade 交易对象
# client.new_order(symbol=symbol, side="SELL", type="LIMIT", quantity=quantity, timeInForce="GTX",price=46000) 限价
# ----timeInForce="GTX" 参数为只做maker
# client.new_order(symbol=symbol, side="BUY", type="MARKET", quantity=quantity)//市 价
# client.query_order(symbol=symbol, orderId=order['orderId'])查询订单
# client.cancel_order(symbol, order['orderId'])撤消订单

# Market 市场信息对象
# client.depth(symbol, **{"limit": 5})  全量深度
# client.book_ticker(symbol)  最优挂单


# ----------------------钉钉机器人
def dingmessage(talk):
    # 钉钉机器人Token
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=*****"
    header = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
    }
    tex = "sd"
    message = {
        "msgtype": "text",
        "text": {
            "content": tex + talk
        },
        "at": {
            "isAtAll": True
        }
    }
    message_json = json.dumps(message)
    info = requests.post(url=webhook, data=message_json, headers=header)
    print(info.text)


# ------------------------------


# 只做MAKER下单，读取当前买卖盘一价，以一价下单， 一直到以一价成功下单，返回订单ID字典
def MAKER(side, amount, price=0):
    while True:
        mar = client.book_ticker(symbol)
        if side > 0:
            try:
                od = client.new_order(symbol=symbol, side="BUY", type="LIMIT", quantity=amount, timeInForce="GTX",
                                      price=float(mar['bidPrice']))
            except Exception as e:
                print("except 01:", e)
                print('MAKER0下单不成功方向', side)
                return 0
            else:
                pass

        elif side < 0:
            try:
                od = client.new_order(symbol=symbol, side="SELL", type="LIMIT", quantity=amount, timeInForce="GTX",
                                      price=float(mar['askPrice']))
            except Exception as e:
                print("except 02:", e)
                print('MAKER0下单不成功方向', side)
                return 0
            else:
                pass
        try:
            ods = client.query_order(symbol=symbol, orderId=od['orderId'])
        except Exception as e:
            print("except 03:", e)
            print('MAKER0，查询订单出错，方向', side)
            return 0
        else:
            if ods['status'] == 'NEW':
                print('ok')
                print('MAKER0方向', side)
                return od


# 只做MAKER下单，读取当前买卖盘一价，以一价下单， 一直到以一价成功下单，返回订单ID字典
def MAKERP(side, amount, price=0):
    if price:
        if side > 0:
            try:
                od = client.new_order(symbol=symbol, side="BUY", type="LIMIT", quantity=amount, timeInForce="GTX",
                                      price=price)
            except Exception as e:
                print("except 04:", e)
                print('MAKER1下单不成功方向', side, price)
                time.sleep(1)
                return 0
            else:
                try:
                    ods = client.query_order(symbol=symbol, orderId=od['orderId'])
                except Exception as e:
                    print("except 05:", e)
                    print('MAKER1，查询订单出错，方向', side)
                    return 0
                else:
                    if ods['status'] == 'NEW':
                        print('MAKER1方向', side)
                        print('ok')
                        return od
                    elif ods['status'] == 'EXPIRED':
                        print('MAKER1订单过期，重以当前买卖一价下单', side)
                        od = MAKER(side, amount)
                        return od


        elif side < 0:
            try:
                od = client.new_order(symbol=symbol, side="SELL", type="LIMIT", quantity=amount, timeInForce="GTX",
                                      price=price)
            except Exception as e:
                print("except 06:", e)
                print('MAKER1下单不成功方向', side, price)
                time.sleep(1)
                return 0
            else:
                try:
                    ods = client.query_order(symbol=symbol, orderId=od['orderId'])
                except Exception as e:
                    print("except 07:", e)
                    print('MAKER1，查询订单出错，方向', side)
                    return 0
                else:
                    if ods['status'] == 'NEW':
                        print('MAKER1方向', side)
                        print('ok')
                        return od
                    elif ods['status'] == 'EXPIRED':
                        print('MAKER1订单过期，重以当前买卖一价下单', side)
                        od = MAKER(side, amount)
                        return od
    else:
        od = MAKER(side, amount)
        return od


# 查询仓位，多仓反回正值，空仓返回负，没仓位返回空值
def po():
    Po = 0
    positions = client.get_position_risk(symbol=symbol)
    if float(positions[0]['positionAmt']):  # 如果无仓位，po返回空值[]
        Po = float(positions[0]['positionAmt'])
        print('当前仓位', Po)
    return Po


def one(quantity):
    global D
    global Taker
    global Po
    global Price

    # -----持仓是否超过限量的1/3

    # ------
    if Price:
        odS = MAKERP(-1, quantity, round((Price + plus), pre))

        odB = MAKERP(1, quantity, round((Price - plus), pre))
    elif not Price:
        mar = client.book_ticker(symbol)
        Price = float(mar['bidPrice'])
        odS = MAKERP(-1, quantity, round((Price + plus), pre))

        odB = MAKERP(1, quantity, round((Price - plus), pre))

    # ---- 查询下单是否成功，否则返回
    if (not odS) or (not odB):
        return 0
    # ---- 查询订单状态，如果超时等异常，暂停0.08秒再查，查取正常，暂停0.05秒
    try:
        orders = client.query_order(symbol=symbol, orderId=odS['orderId'])
        orderb = client.query_order(symbol=symbol, orderId=odB['orderId'])
    except:
        try:
            time.sleep(1)
            orders = client.query_order(symbol=symbol, orderId=odS['orderId'])
            orderb = client.query_order(symbol=symbol, orderId=odB['orderId'])
        except:
            print('查询订单出错：BOTH')
            return 0

    else:
        time.sleep(0.01)

    # ------
    startTime = time.time()
    afterTime = time.time()

    while True:
        if orders['status'] == 'FILLED' or orderb['status'] == 'FILLED':
            if orders['status'] == 'FILLED' and orderb['status'] != 'FILLED':
                if float(orders['price']) < float(orders['avgPrice']):
                    Taker = Taker + quantity
                try:
                    client.cancel_order(symbol, odB['orderId'])
                except:
                    print('订单不存在')
                    Price = 0
                    return 3
                else:
                    Price = float(orders['price'])
                    print('订单成交，方向：卖，价格：', Price)
                    return 1

            elif orders['status'] != 'FILLED' and orderb['status'] == 'FILLED':
                if float(orderb['price']) > float(orderb['avgPrice']):
                    Taker = Taker + quantity
                try:
                    client.cancel_order(symbol, odS['orderId'])
                except:
                    print('订单不存在')
                    Price = 0
                    return 3
                else:
                    Price = float(orderb['price'])
                    print('订单成交，方向：买，价格：', Price)
                    return 2

            else:
                if float(orders['price']) < float(orders['avgPrice']):
                    Taker = Taker + quantity
                if float(orderb['price']) > float(orderb['avgPrice']):
                    Taker = Taker + quantity
                Price = 0
                print('订单成交，方向：BOTH，价格：', float(orders['avgPrice']), float(orderb['avgPrice']))
                return 3
        elif afterTime - startTime > timeOut:
            client.cancel_open_orders(symbol)
            print('超时取消挂单')
            return 0

        else:
            time.sleep(5)
            afterTime = time.time()
            try:
                orders = client.query_order(symbol=symbol, orderId=odS['orderId'])
                orderb = client.query_order(symbol=symbol, orderId=odB['orderId'])

            except:
                time.sleep(0.1)
                print('查询订单出错')
            else:
                time.sleep(0.1)


def UpdateSpacing():
    global plus
    Ksum = 0
    Kaverage = 0
    qt = 0
    l = client.klines(symbol, interval=recordsTime, limit=6)
    for x in l:
        Ksum = Ksum + float(x[2]) - float(x[3])
    Kaverage = round(Ksum / 6, pre)
    if Kaverage > spacing * 6:
        Kaverage = round(spacing * 8, pre)
    elif Kaverage < spacing / 1.5:
        Kaverage = round(spacing / 1.5, pre)
    qt = round(Kaverage / (spacing * 2.5), 0) + 1
    plus = Kaverage
    print('更新格距为', plus)
    return qt


if __name__ == '__main__':
    Po = po()
    CutDownB = 0
    CutDownS = 0
    c = 0
    cc = 1
    Po = 0
    cn = 0
    plus = spacing
    Quantity = baseQuantity * UpdateSpacing()

    while True:
        Po = po()
        if Po:
            while Po > u:
                print('持有多仓仓位大于持仓限量')
                if s:

                    q = baseQuantity * s
                    client.new_order(symbol=symbol, side="SELL", type="MARKET", quantity=q)
                    CutDownB = CutDownB + 1
                    Taker = Taker + q
                    Po = po()
                else:
                    try:
                        print('挂一空仓等待')
                        mar = client.book_ticker(symbol)
                        od = client.new_order(symbol=symbol, side="SELL", type="LIMIT", quantity=Quantity,
                                              timeInForce="GTX",
                                              price=(float(mar['askPrice']) + plus))
                    except Exception as e:
                        print("except 10:", e)
                        print('MAKER0下单不成功方向', "SELL,try again")
                    else:
                        while Po > u:
                            Po = po()
                            time.sleep(2)

            while Po + d < 0:
                print('持有空仓仓位大于持仓限量')
                if s:
                    q = baseQuantity * s
                    client.new_order(symbol=symbol, side="BUY", type="MARKET", quantity=q)
                    CutDownS = CutDownS + 1
                    Taker = Taker + q
                    Po = po()
                else:
                    try:
                        print('挂一多仓等待')
                        mar = client.book_ticker(symbol)
                        od = client.new_order(symbol=symbol, side="BUY", type="LIMIT", quantity=Quantity,
                                              timeInForce="GTX",
                                              price=(float(mar['bidPrice']) - plus))
                    except Exception as e:
                        print("except 10:", e)
                        print('MAKER0下单不成功方向', "SELL,try again")
                    else:
                        while Po + d < 0:
                            Po = po()
                            time.sleep(2)

        if one(Quantity):
            c = c + Quantity
            cc = cc + 1
            cn = cn + 1
        else:
            client.cancel_open_orders(symbol)
            print('取消现在挂单')
            Quantity = baseQuantity * UpdateSpacing()

        print('成交', cn, '次,成交', c, '张--吃单成交', Taker)
        print('强减多仓', CutDownB, '--次，强减空仓', CutDownS)
        print('当前格距', plus, '--当前格单量', Quantity)
        print(datetime.datetime.now())

        if cc % finishNumber == 1:
            Quantity = baseQuantity * UpdateSpacing()

        time.sleep(0.01)
        if cn % 25 == 1:
            print('钉钉推送-----')
            try:
                takl1 = symbol + '网格成交' + str(cn) + '次,成交' + str(c) + '张--吃单成交' + str(Taker)
                talk2 = "\n" + '强减多仓' + str(CutDownB) + '次，强减空仓' + str(CutDownS)
                talk3 = "\n" + '当前格距' + str(plus) + '--当前格单量' + str(Quantity) + "\n" + str(datetime.datetime.now())
                talk = takl1 + talk2 + talk3
                dingmessage(talk)
            except:
                print('钉钉推送出错')
                pass
