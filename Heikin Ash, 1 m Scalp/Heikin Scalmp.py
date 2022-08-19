import ccxt,config
import talib
import pandas as pd
import numpy as np


#Api Connect
exchange=ccxt.binance({
"apiKey": config.apiKey,
"secret": config.secretKey,

"options":{
"defaultType": "future"
},
"enableRateLimit": True

})

#İnput
SymbolName = input("Coin Symbol(BTC,ETC,LTC):").upper()
TimeFrame = input("Time Frame (1m,3m,5m,15m,30m,45m,1h,2h,3h,4h.....): ")
leverage = input("Amount of leverage : " )
symbol = SymbolName+"USDT"

RSI = False
ema50timeframe = "4h"
C50ema = False
C9ema = False
Long_position = False
Position = False

Tp1=False
ShortTrend = False
Shortposition = False
ShortCEMA9 = False
RSI2 = False
TpShort = False

# We are using Heiking Ashi Candle and  2 EMA in this strategy....
# ==================================== BULL =================================
# First Step of Long Position:
# We must decide  direction of the Trend Are we in an uptrend or a downtrend? To find out, we set the EMA50 Time frame to be 4 hours.
# When Inside the 1m time frame,
# 1-) If the candles are above the EMA 50, it is an uptrend.As you guess,If the candles are below the EMA 50, it is a downtrend.
#  After deciding which direction the trend is in, we will use the RSI for the second confirmation.
# 2-) The second confirmation is completed when the RSI falls below 30.
# 3-) For the last confirmation, we will wait for last Heikin Ashi Candle must close above the EMA9
#  We can open Long Position....After That Point of Take Profit
# ============================================ BEAR =============================== #
# 1-) We know that If the candles are below the EMA 50, it is a downtrend.
# 2-) This time we will wait for the RSI to rise above 70/71/72
# 3-) For the last confirmation, If last Heikin Ashi candle close below EMA9, we can open Short Position



def main():
    global C9ema,C50ema,ShortTrend
    while True:
        try:
            # Balance and position information
            balance = exchange.fetch_balance()
            free_balance = exchange.fetch_free_balance()
            positions = balance["info"]["positions"]
            current_positions = [position for position in positions if float(position["positionAmt"]) != 0 and position["symbol"] == symbol]
            position_inform = pd.DataFrame(current_positions,columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet","positionAmt", "positionSide"])

            # Position Check

            if not position_inform.empty and position_inform["positionAmt"][len(position_inform.index) - 1] != 0:
                waitingPosition = True
            else:
                waitingPosition = False
                Shortposition = False
                Long_position = False

                # Is it LONG ?
            if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) > 0:
                Long_position = True
                Shortposition = False
                # Is it SHORT?
            if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) < 0:
                Shortposition = True
                Long_position = False

            # BARS

            bars = exchange.fetch_ohlcv(symbol, timeframe=TimeFrame, since=None, limit=500)
            df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

            dfHa = df.copy()
            for i in range(len(dfHa.index) - 1):
                if i > 0:
                    dfHa["open"][i] = (float(dfHa["open"][i - 1]) + float(dfHa["close"][i - 1])) / 2
                dfHa["close"][i] = (float(dfHa["close"][i]) + float(dfHa["open"][i]) + float(dfHa["high"][i]) + float(
                    dfHa["low"][i])) / 4
                dfHa["high"][i] = max(dfHa["high"][i], dfHa["open"][i], dfHa["close"][i])
                dfHa["low"][i] = min(dfHa["low"][i], dfHa["open"][i], dfHa["close"][i])

            bars2 = exchange.fetch_ohlcv(symbol, timeframe=ema50timeframe, since=None, limit=500)
            df2 = pd.DataFrame(bars2, columns=["timestamp", "open", "high", "low", "close", "volume"])

            dfHa2 = df2.copy()

            for i in range(len(dfHa2.index) - 1):
                if i > 0:
                    dfHa2["open"][i] = (float(dfHa2["open"][i - 1]) + float(dfHa2["close"][i - 1])) / 2
                dfHa2["close"][i] = (float(df2["close"][i]) + float(df2["open"][i]) + float(df2["high"][i]) + float(
                    df2["low"][i])) / 4
                dfHa2["high"][i] = max(dfHa2["high"][i], dfHa2["open"][i], dfHa2["close"][i])
                dfHa2["low"][i] = min(dfHa2["low"][i], dfHa2["open"][i], dfHa2["close"][i])

            # Ema Check

            Ema50 = talib.EMA(dfHa2["close"], timeperiod=55)

            # RSI
            RSI_period = 14
            rsi = talib.RSI(dfHa["close"], timeperiod=RSI_period)

            # Ema2 = 9  1m TimeFrame
            Ema9 = talib.EMA(dfHa["close"], timeperiod=9)

            if np.mean(dfHa["close"][496:499]) > Ema50[499]:
                C50ema = True
            else:
                C50ema = False

            if dfHa["close"][498] > Ema9[498]:
                C9ema = True
            else:
                C9ema = False


            # AMOUNT

            amount = (((float(free_balance["USDT"]) / 100) * 70) * float(leverage)) / float(df["close"][len(df.index) - 1])
            amount2 = amount / 2

            # LONG ENTER
            def longEnter(amount):
                global order
                order = exchange.create_market_buy_order(symbol, amount)

            def long_Exit2(amount):
                global order
                order = exchange.create_market_sell_order(symbol, amount, {"reduceOnly": True})

            # LONG EXIT
            def longExit():
                global order
                order = exchange.create_market_sell_order(symbol, float(
                    position_inform["positionAmt"][len(position_inform.index) - 1]), {"reduceOnly": True})

            # SHORT ENTER
            def shortEnter(amount):
                global order
                order = exchange.create_market_sell_order(symbol, amount)

            # SHORT EXIT
            def shortExit():
                global order
                order = exchange.create_market_buy_order(symbol, ( float(position_inform["positionAmt"][len(position_inform.index) - 1]) * -1),{"reduceOnly": True})

            # If the program quit unexpectedly
            if Long_position == True:
                gain()
            # For Long
            if rsi[499] <= 30:
                chase()



            if waitingPosition == False:
                print("WAITING FOR POSITION..")
            if Shortposition:
                print("In SHORT")
            if Long_position:
                print("IN LONG")

        except ccxt.BaseError as Error:
            print("[ERROR]", Error)
            continue

def chase():
    while True:
        global Long_position, Shortposition
        # Balance and position information
        balance = exchange.fetch_balance()
        free_balance = exchange.fetch_free_balance()
        positions = balance["info"]["positions"]
        current_positions = [position for position in positions if
                             float(position["positionAmt"]) != 0 and position["symbol"] == symbol]
        position_inform = pd.DataFrame(current_positions,
                                       columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet",
                                                "positionAmt", "positionSide"])

        # Position Check

        if not position_inform.empty and position_inform["positionAmt"][len(position_inform.index) - 1] != 0:
            waitingPosition = True
        else:
            waitingPosition = False
            Shortposition = False
            Long_position = False

            # Is it LONG ?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) > 0:
            Long_position = True
            Shortposition = False
            # Is it SHORT?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) < 0:
            Shortposition = True
            Long_position = False

        # BARS

        bars = exchange.fetch_ohlcv(symbol, timeframe=TimeFrame, since=None, limit=500)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa = df.copy()
        for i in range(len(dfHa.index) - 1):
            if i > 0:
                dfHa["open"][i] = (float(dfHa["open"][i - 1]) + float(dfHa["close"][i - 1])) / 2
            dfHa["close"][i] = (float(dfHa["close"][i]) + float(dfHa["open"][i]) + float(dfHa["high"][i]) + float(dfHa["low"][i])) / 4
            dfHa["high"][i] = max(dfHa["high"][i], dfHa["open"][i], dfHa["close"][i])
            dfHa["low"][i] = min(dfHa["low"][i], dfHa["open"][i], dfHa["close"][i])

        bars2 = exchange.fetch_ohlcv(symbol, timeframe=ema50timeframe, since=None, limit=500)
        df2 = pd.DataFrame(bars2, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa2 = df2.copy()

        for i in range(len(dfHa2.index) - 1):
            if i > 0:
                dfHa2["open"][i] = (float(dfHa2["open"][i - 1]) + float(dfHa2["close"][i - 1])) / 2
            dfHa2["close"][i] = (float(df2["close"][i]) + float(df2["open"][i]) + float(df2["high"][i]) + float(df2["low"][i])) / 4
            dfHa2["high"][i] = max(dfHa2["high"][i], dfHa2["open"][i], dfHa2["close"][i])
            dfHa2["low"][i] = min(dfHa2["low"][i], dfHa2["open"][i], dfHa2["close"][i])

        # Ema Check

        Ema50 = talib.EMA(dfHa2["close"], timeperiod=55)

        # RSI
        RSI_period = 14
        rsi = talib.RSI(dfHa["close"], timeperiod=RSI_period)

        # Ema2 = 9  1m TimeFrame
        Ema9 = talib.EMA(dfHa["close"], timeperiod=9)

        # Check EMA Long
        if np.mean(dfHa["close"][496:499]) > Ema50[499]:
            C50ema = True
        else:
            C50ema = False


        if dfHa["close"][498] > Ema9[498]:
            C9ema = True
        else:
            C9ema = False

        #Check Ema Short

        if np.mean(dfHa["close"][496:499]) < Ema50[499]:
            ShortTrend = True
        else:
            ShortTrend = False

        if dfHa["close"][498] < Ema9[498]:
            ShortCEMA9 = True
        else:
            ShortCEMA9 = False

        # AMOUNT
        amount = (((float(free_balance["USDT"]) / 100) * 70) * float(leverage)) / float(df["close"][len(df.index) - 1])
        amount2 = amount / 1.5

        # LONG ENTER Func
        def longEnter(amount):
            global order
            order = exchange.create_market_buy_order(symbol, amount)

        def long_Exit2(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount, {"reduceOnly": True})

        # LONG EXIT Func
        def longExit():
            global order
            order = exchange.create_market_sell_order(symbol, float(position_inform["positionAmt"][len(position_inform.index) - 1]), {"reduceOnly": True})
        # Short Enter Func

        def shortEnter(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount)

        def shortExit():
            global order
            order = exchange.create_market_buy_order(symbol, (float(position_inform["positionAmt"][len(position_inform.index) - 1]) * -1),{"reduceOnly": True})

        Long_position = False
        Shortposition = False

        #Long Enter
        if C9ema == True and C50ema == True:
            Long_position = True
            longEnter(amount)
            print("Long Enter")
            if Long_position == True:  # Need Chasing Point of Profit
                gain()

def gain():
    global Long_position,Shortposition,RSI,RSI2,TpShort
    while True:

        # Balance and position information
        balance = exchange.fetch_balance()
        free_balance = exchange.fetch_free_balance()
        positions = balance["info"]["positions"]
        current_positions = [position for position in positions if
                             float(position["positionAmt"]) != 0 and position["symbol"] == symbol]
        position_inform = pd.DataFrame(current_positions,columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet","positionAmt", "positionSide"])

        # Position Check

        if not position_inform.empty and position_inform["positionAmt"][len(position_inform.index) - 1] != 0:
            waitingPosition = True
        else:
            waitingPosition = False
            Shortposition = False
            Long_position = False

            # Is it LONG ?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) > 0:
            Long_position = True
            Shortposition = False
            # Is it SHORT?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) < 0:
            Shortposition = True
            Long_position = False

        # BARS

        bars = exchange.fetch_ohlcv(symbol, timeframe=TimeFrame, since=None, limit=500)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa = df.copy()
        for i in range(len(dfHa.index) - 1):
            if i > 0:
                dfHa["open"][i] = (float(dfHa["open"][i - 1]) + float(dfHa["close"][i - 1])) / 2
            dfHa["close"][i] = (float(dfHa["close"][i]) + float(dfHa["open"][i]) + float(dfHa["high"][i]) + float(dfHa["low"][i])) / 4
            dfHa["high"][i] = max(dfHa["high"][i], dfHa["open"][i], dfHa["close"][i])
            dfHa["low"][i] = min(dfHa["low"][i], dfHa["open"][i], dfHa["close"][i])

        bars2 = exchange.fetch_ohlcv(symbol, timeframe=ema50timeframe, since=None, limit=500)
        df2 = pd.DataFrame(bars2, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa2 = df2.copy()

        for i in range(len(dfHa2.index) - 1):
            if i > 0:
                dfHa2["open"][i] = (float(dfHa2["open"][i - 1]) + float(dfHa2["close"][i - 1])) / 2
            dfHa2["close"][i] = (float(df2["close"][i]) + float(df2["open"][i]) + float(df2["high"][i]) + float(
                df2["low"][i])) / 4
            dfHa2["high"][i] = max(dfHa2["high"][i], dfHa2["open"][i], dfHa2["close"][i])
            dfHa2["low"][i] = min(dfHa2["low"][i], dfHa2["open"][i], dfHa2["close"][i])

        # Ema Check

        Ema50 = talib.EMA(dfHa2["close"], timeperiod=55)

        # RSI
        RSI_period = 14
        rsi = talib.RSI(dfHa["close"], timeperiod=RSI_period)

        # For bull
        if rsi[498]  >= 70:
            RSI = True
        # For Bear


        # Ema2 = 9  1m TimeFrame
        Ema9 = talib.EMA(dfHa["close"], timeperiod=9)

        # AMOUNT

        amount = (((float(free_balance["USDT"]) / 100) * 70) * float(leverage)) / float(df["close"][len(df.index) - 1])
        amount2 = amount / 1.5


        # LONG ENTER
        def longEnter(amount):
            global order
            order = exchange.create_market_buy_order(symbol, amount)

        def long_Exit2(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount, {"reduceOnly": True})

        # LONG EXIT
        def longExit():
            global order
            order = exchange.create_market_sell_order(symbol, float(
                position_inform["positionAmt"][len(position_inform.index) - 1]), {"reduceOnly": True})

        def shortEnter(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount)

        def shortExit():
            global order
            order = exchange.create_market_buy_order(symbol, (float(position_inform["positionAmt"][len(position_inform.index) - 1]) * -1),{"reduceOnly": True})

        def shortExit2(amount):
            global order
            order = exchange.create_market_buy_order(symbol,amount)


        EntryPrice = float(position_inform["entryPrice"][len(position_inform.index) - 1])
        Stop_Loss_Point = float(EntryPrice * 0.9980)  # You can Change your stoploss length
        Tpp = EntryPrice + ((EntryPrice - Stop_Loss_Point) * 1.8)  # Take Profit Point for long


        # For Bull


        if Long_position == True:
            Tp1 = False
            if dfHa["close"][499] >= Tpp:
                Tp1 = True


            if RSI == True and Tp1 == True:
                longExit()
                print("TakeProfit Long First")
                main()


            if RSI == True and Tp1 == False:
                print("Take Profit 2 ")
                long_Exit2(amount2)
                gain2()


            if dfHa["close"][498] < Stop_Loss_Point:
                longExit()
                main()


def gain2():
    global Shortposition,Long_position
    while True:
        print("gain2 deyim")
        # Balance and position information
        balance = exchange.fetch_balance()
        free_balance = exchange.fetch_free_balance()
        positions = balance["info"]["positions"]
        current_positions = [position for position in positions if
                             float(position["positionAmt"]) != 0 and position["symbol"] == symbol]
        position_inform = pd.DataFrame(current_positions,columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet","positionAmt", "positionSide"])



        if not position_inform.empty and position_inform["positionAmt"][len(position_inform.index) - 1] != 0:
            waitingPosition = True
        else:
            waitingPosition = False
            Shortposition = False
            Long_position = False

            # Is it LONG ?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) > 0:
            Long_position = True
            Shortposition = False
            # Is it SHORT?
        if waitingPosition and float(position_inform["positionAmt"][len(position_inform.index) - 1]) < 0:
            Shortposition = True
            Long_position = False

        # BARS

        bars = exchange.fetch_ohlcv(symbol, timeframe=TimeFrame, since=None, limit=500)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa = df.copy()
        for i in range(len(dfHa.index) - 1):
            if i > 0:
                dfHa["open"][i] = (float(dfHa["open"][i - 1]) + float(dfHa["close"][i - 1])) / 2
            dfHa["close"][i] = (float(dfHa["close"][i]) + float(dfHa["open"][i]) + float(dfHa["high"][i]) + float(dfHa["low"][i])) / 4
            dfHa["high"][i] = max(dfHa["high"][i], dfHa["open"][i], dfHa["close"][i])
            dfHa["low"][i] = min(dfHa["low"][i], dfHa["open"][i], dfHa["close"][i])

        bars2 = exchange.fetch_ohlcv(symbol, timeframe=ema50timeframe, since=None, limit=500)
        df2 = pd.DataFrame(bars2, columns=["timestamp", "open", "high", "low", "close", "volume"])

        dfHa2 = df2.copy()

        for i in range(len(dfHa2.index) - 1):
            if i > 0:
                dfHa2["open"][i] = (float(dfHa2["open"][i - 1]) + float(dfHa2["close"][i - 1])) / 2
            dfHa2["close"][i] = (float(df2["close"][i]) + float(df2["open"][i]) + float(df2["high"][i]) + float(df2["low"][i])) / 4
            dfHa2["high"][i] = max(dfHa2["high"][i], dfHa2["open"][i], dfHa2["close"][i])
            dfHa2["low"][i] = min(dfHa2["low"][i], dfHa2["open"][i], dfHa2["close"][i])

        # Ema Check

        Ema50 = talib.EMA(dfHa2["close"], timeperiod=55)

        # RSI
        RSI_period = 14
        rsi = talib.RSI(dfHa["close"], timeperiod=RSI_period)

        # Ema2 = 9  1m TimeFrame
        Ema9 = talib.EMA(dfHa["close"], timeperiod=9)

        # AMOUNT

        amount = (((float(free_balance["USDT"]) / 100) * 70) * float(leverage)) / float(df["close"][len(df.index) - 1])
        amount2 = amount / 1.5

        # LONG Position
        def longEnter(amount):
            global order
            order = exchange.create_market_buy_order(symbol, amount)

        def long_Exit2(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount, {"reduceOnly": True})


        def longExit():
            global order
            order = exchange.create_market_sell_order(symbol, float(position_inform["positionAmt"][len(position_inform.index) - 1]), {"reduceOnly": True})

        # Short Position

        def shortEnter(amount):
            global order
            order = exchange.create_market_sell_order(symbol, amount)

        def shortExit():
            global order
            order = exchange.create_market_buy_order(symbol, (float(position_inform["positionAmt"][len(position_inform.index) - 1]) * -1),
                                                     {"reduceOnly": True})

        def shortExit2(amount):
            global order
            order = exchange.create_market_buy_order(symbol, amount)

        EntryPrice = float(position_inform["entryPrice"][len(position_inform.index) - 1])
        Stop_Loss_Point = float(EntryPrice * 0.9980)  # You can Change your stoploss length
        Tpp = EntryPrice + ((EntryPrice - Stop_Loss_Point) * 1.8)  # Take Profit Point

        Long_position = True
        # Long End
        if Long_position == True :

            if dfHa["close"][498] >= Tpp:
                print("Closing And Looping Again")
                longExit()
                main()
            if  dfHa["close"][498] < EntryPrice:
                longExit()
                main()


main()