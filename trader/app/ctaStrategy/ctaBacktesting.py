# encoding: UTF-8

'''
本檔中包含的是CTA模組的回測引擎，回測引擎的API和CTA引擎一致，
可以使用和實盤相同的代碼進行回測。
'''
from __future__ import division
from __future__ import print_function

from datetime import datetime, timedelta
from collections import OrderedDict
from itertools import product
import multiprocessing
import copy

import pyodbc
# import pymongo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker

from vnpy.rpc import RpcClient, RpcServer, RemoteException

# 如果安裝了seaborn則設置為白色風格
try:
    import seaborn as sns

    sns.set_style('whitegrid')
except ImportError:
    pass

from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtObject import VtTickData, VtBarData
from vnpy.trader.vtConstant import *
from vnpy.trader.vtGateway import VtOrderData, VtTradeData

from .ctaBase import *


########################################################################
class BacktestingEngine(object):
    """
    CTA回測引擎
    函數介面和策略引擎保持一樣，
    從而實現同一套代碼從回測到實盤。
    """

    BAR_MODE = 'bar'
    TRADE_MODE = 'trade'  # i020
    BOOK_MODE = 'book'  # i080
    HYBER_MODE = 'trade_book'  # i020、i080

    EASY_MODE = 'easy'  # 下單價即為成交價
    DEFAULT_MODE = 'default'  # 以080判斷成交價量
    TRADEFILLED_MODE = 'tradefilled'  # 加入020判斷成交價量

    ORDER_MODE = 'order'  # 標示下單點
    DEAL_MODE = 'deal'  # 標示成交點

    Simple_Mode = 'simple'
    Detail_Mode = 'detail'

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        # 本地停止單
        self.stopOrderCount = 0  # 編號計數：stopOrderID = STOPORDERPREFIX + str(stopOrderCount)

        # 本地停止單字典, key為stopOrderID，value為stopOrder對象
        self.stopOrderDict = {}  # 停止單撤銷後不會從本字典中刪除
        self.workingStopOrderDict = {}  # 停止單撤銷後會從本字典中刪除

        self.engineType = ENGINETYPE_BACKTESTING  # 引擎類型為回測

        self.strategy = None  # 回測策略
        self.mode = None  # 回測模式，預設為K線
        self.simulateMode = None
        self.plotMode = None
        self.printMode = None # 成交明細

        self.startDate = ''
        self.initDays = 0
        self.endDate = ''

        self.capital = 1000000  # 回測時的起始本金（默認100萬）
        self.slippage = 0  # 回測時假設的滑點
        self.rate = 0  # 回測時假設的傭金比例（適用於百分比傭金）
        self.size = 1  # 合約大小，默認為1
        self.priceTick = 0  # 價格最小變動

        self.dbClient = None  # 資料庫用戶端
        self.dbCursor = None  # 資料庫指標
        self.hdsClient = None  # 歷史資料伺服器用戶端

        self.S = []  # 紀錄S
        self.T = []  # 記錄T
        self.BuyDeal = []  # 記錄買成交
        self.BuyDealTime = []
        self.SellDeal = []  # 記錄賣成交
        self.SellDealTime = []
        self.OrderBuy = []  # 記錄委託買
        self.OrderBuyTime = []
        self.OrderSell = []  # 記錄委託賣
        self.OrderSellTime = []
        self.pos = [0]
        self.tradeTime = [0]

        self.initData = []  # 初始化用的數據
        self.dbName = ''  # 回測資料庫名
        self.symbol = ''  # 回測集合名

        self.dataStartDate = None  # 回測資料開始日期，datetime物件
        self.dataEndDate = None  # 回測資料結束日期，datetime物件
        self.strategyStartDate = None  # 策略啟動日期（即前面的資料用於初始化），datetime物件

        self.limitOrderCount = 0  # 限價單編號
        self.limitOrderDict = OrderedDict()  # 限價單字典
        self.workingLimitOrderDict = OrderedDict()  # 活動限價單字典，用於進行撮合用
        self.sortedWorkingLimitOrderList = []  # 排序ROD單

        self.tradeCount = 0  # 成交編號
        self.tradeDict = OrderedDict()  # 成交字典

        self.logList = []  # 日誌記錄

        # 當前最新資料，用於類比成交用
        self.tick = None
        self.bar = None
        self.dt = None  # 最新的時間

        # 日線回測結果計算用
        self.dailyResultDict = OrderedDict()

        # save result
        self.d_result = None

    # ------------------------------------------------
    # 通用功能
    # ------------------------------------------------

    def init(self):
        self.stopOrderCount = 0  # 編號計數：stopOrderID = STOPORDERPREFIX + str(stopOrderCount)

        # 本地停止單字典, key為stopOrderID，value為stopOrder對象
        self.stopOrderDict = {}  # 停止單撤銷後不會從本字典中刪除
        self.workingStopOrderDict = {}  # 停止單撤銷後會從本字典中刪除

        self.S = []  # 紀錄S
        self.T = []  # 記錄T
        self.BuyDeal = []  # 記錄買成交
        self.BuyDealTime = []
        self.SellDeal = []  # 記錄賣成交
        self.SellDealTime = []
        self.OrderBuy = []  # 記錄委託買
        self.OrderBuyTime = []
        self.OrderSell = []  # 記錄委託賣
        self.OrderSellTime = []
        self.pos = [0]
        self.tradeTime = [0]

        self.limitOrderCount = 0  # 限價單編號
        self.limitOrderDict = OrderedDict()  # 限價單字典
        self.workingLimitOrderDict = OrderedDict()  # 活動限價單字典，用於進行撮合用
        self.sortedWorkingLimitOrderList = []  # 排序ROD單

        self.tradeCount = 0  # 成交編號
        self.tradeDict = OrderedDict()  # 成交字典

        self.logList = []  # 日誌記錄

        # 當前最新資料，用於類比成交用
        self.tick = None
        self.bar = None
        self.dt = None  # 最新的時間

        # 日線回測結果計算用
        self.dailyResultDict = OrderedDict()

        # save result
        self.d_result = None

    # ----------------------------------------------------------------------
    def roundToPriceTick(self, price):
        """取整價格到合約最小價格變動"""
        if not self.priceTick:
            return price

        newPrice = round(price / self.priceTick, 0) * self.priceTick
        return newPrice

    # ----------------------------------------------------------------------
    def output(self, content):
        """輸出內容"""
        print(str(datetime.now()) + "\t" + content)

        # ------------------------------------------------

    # 參數設置相關
    # ------------------------------------------------

    # ----------------------------------------------------------------------
    def setStartDate(self, startDate='20100416', initDays=0):
        """設置回測的啟動日期"""
        self.startDate = startDate
        self.initDays = initDays

        self.dataStartDate = datetime.strptime(startDate, '%Y%m%d')

        initTimeDelta = timedelta(initDays)
        self.strategyStartDate = self.dataStartDate + initTimeDelta

    # ----------------------------------------------------------------------
    def setEndDate(self, endDate=''):
        """設置回測的結束日期"""
        self.endDate = endDate

        if endDate:
            self.dataEndDate = datetime.strptime(endDate, '%Y%m%d')

            # 若不修改時間則會導致不包含dataEndDate當天資料
            self.dataEndDate = self.dataEndDate.replace(hour=23, minute=59)

            # ----------------------------------------------------------------------

    def setBacktestingMode(self, mode):
        """設置回測模式"""
        self.mode = mode

    # ----------------------------------------------------------------------
    def setSimulatingMode(self, simulatemode):
        """設置回測模式"""
        self.simulateMode = simulatemode

    # ----------------------------------------------------------------------
    def setPlotMode(self, plotmode):
        """設置回測模式"""
        self.plotMode = plotmode

    # ----------------------------------------------------------------------
    def setPrintDetailMode(self, printmode):
        """設置回測模式"""
        self.printMode = printmode

    # ----------------------------------------------------------------------
    def setDatabase(self, dbName, symbol):
        """設置歷史資料所用的資料庫"""
        self.dbName = dbName
        self.symbol = symbol

    # ----------------------------------------------------------------------
    def setCapital(self, capital):
        """設置資本金"""
        self.capital = capital

    # ----------------------------------------------------------------------
    def setSlippage(self, slippage):
        """設置滑點點數"""
        self.slippage = slippage

    # ----------------------------------------------------------------------
    def setSize(self, size):
        """設置合約大小"""
        self.size = size

    # ----------------------------------------------------------------------
    def setRate(self, rate):
        """設置傭金比例"""
        self.rate = rate

    # ----------------------------------------------------------------------
    def setPriceTick(self, priceTick):
        """設置價格最小變動"""
        self.priceTick = priceTick

    # ------------------------------------------------
    # 資料重播相關
    # ------------------------------------------------

    # ----------------------------------------------------------------------
    def initHdsClient(self):
        """初始化歷史資料伺服器用戶端"""
        reqAddress = 'tcp://localhost:5555'
        subAddress = 'tcp://localhost:7777'

        self.hdsClient = RpcClient(reqAddress, subAddress)
        self.hdsClient.start()

    # ----------------------------------------------------------------------
    def loadHistoryData(self):
        """載入歷史資料"""
        self.dbClient = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
        collection = self.dbClient[self.dbName][self.symbol]

        self.output(u'開始載入資料')

        # 首先根據回測模式，確認要使用的資料類
        # Alternative (just in case)
        # mapping ={self.BAR_MODE:VtBarData, ...}
        # mapping[self.mode]

        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
        elif self.mode == self.TRADE_MODE:
            dataClass = VtTickData
        elif self.mode == self.BOOK_MODE:
            dataClass = VtTickData
        else:
            dataClass = VtTickData

        # 載入初始化需要用的資料
        if self.hdsClient:
            initCursor = self.hdsClient.loadHistoryData(self.dbName,
                                                        self.symbol,
                                                        self.dataStartDate,
                                                        self.strategyStartDate)
        else:
            flt = {'datetime': {'$gte': self.dataStartDate,
                                '$lt': self.strategyStartDate}}
            initCursor = collection.find(flt).sort('datetime')

        # 將資料從查詢指標中讀取出，並生成列表
        self.initData = []  # 清空initData列表
        for d in initCursor:
            print(d)
            data = dataClass()
            data.__dict__ = d
            self.initData.append(data)
        # 載入回測數據
        if self.hdsClient:
            self.dbCursor = self.hdsClient.loadHistoryData(self.dbName,
                                                           self.symbol,
                                                           self.strategyStartDate,
                                                           self.dataEndDate)
        else:
            if not self.dataEndDate:
                flt = {'datetime': {'$gte': self.strategyStartDate}}  # 資料過濾條件
            else:
                flt = {'datetime': {'$gte': self.strategyStartDate,
                                    '$lte': self.dataEndDate}}
            self.dbCursor = collection.find(flt).sort('datetime')

        if isinstance(self.dbCursor, list):
            count = len(initCursor) + len(self.dbCursor)
        else:
            count = initCursor.count() + self.dbCursor.count()
        self.output(u'載入完成，資料量：%s' % count)

    # ----------------------------------------------------------------------
    def loadHistoryDataSql(self):
        """載入歷史資料"""

        cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=192.168.0.5;DATABASE=msdb;UID=sa;PWD=9685')
        cursor = cnxn.cursor()

        cursor.execute("select * from TXFTickData")
        row = cursor.fetchall()

        self.output(u'開始載入資料')

        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
        elif self.mode == self.TRADE_MODE:
            dataClass = VtTickData
        elif self.mode == self.BOOK_MODE:
            dataClass = VtTickData
        else:
            dataClass = VtTickData

        # 載入初始化需要用的資料
        if self.hdsClient:
            initCursor = self.hdsClient.loadHistoryData(self.dbName,
                                                        self.symbol,
                                                        self.dataStartDate,
                                                        self.strategyStartDate)
        else:
            flt = {'datetime': {'$gte': self.dataStartDate,
                                '$lt': self.strategyStartDate}}
            initCursor = row
        # 將資料從查詢指標中讀取出，並生成列表
        self.initData = []  # 清空initData列表
        headers = ['SeqNo', 'datetime', 'time', 'microSec', 'Seq', 'symbol', 'lastPrice', 'lastVolume', 'bidPrice1',
                   'bidPrice2', 'bidPrice3', 'bidPrice4', 'bidPrice5', 'askPrice1', 'askPrice2', 'askPrice3',
                   'askPrice4', 'askPrice5', \
                   'bidVolume1', 'bidVolume2', 'bidVolume3', 'bidVolume4', 'bidVolume5', 'askVolume1', 'askVolume2',
                   'askVolume3', 'askVolume4', 'askVolume5', 'ptype', 'volume', 'Status', 'MulticastGroup', 'MsgTime']

        for d in initCursor:
            data = dataClass()
            data.__dict__ = dict(zip(headers, d))
            self.initData.append(data)
        # 載入回測數據
        if self.hdsClient:
            self.dbCursor = self.hdsClient.loadHistoryData(self.dbName,
                                                           self.symbol,
                                                           self.strategyStartDate,
                                                           self.dataEndDate)
        else:
            if not self.dataEndDate:
                flt = {'datetime': {'$gte': self.strategyStartDate}}  # 資料過濾條件
            else:
                flt = {'datetime': {'$gte': self.strategyStartDate,
                                    '$lte': self.dataEndDate}}
            self.dbCursor = row
        if isinstance(self.dbCursor, list):
            count = len(initCursor) + len(self.dbCursor)
        else:
            count = initCursor.count() + self.dbCursor.count()
        self.output(u'載入完成，資料量：%s' % count)

    # ----------------------------------------------------------------------

    def loadHistoryDataCsv(self):
        """載入歷史資料"""

        df = pd.read_csv(
            'C:/Users/Bette/Desktop/20190117.csv', index_col=False)

        df = df.rename(
            columns={"txDate": "date", "txTime": "time", "Pid": "symbol", "Dp": "lastPrice", "Dv": "lastVolume",
                     "Bp1": "bidPrice1" \
                , "Bp2": "bidPrice2", "Bp3": "bidPrice3", "Bp4": "bidPrice4", "Bp5": "bidPrice5", "Sp1": "askPrice1",
                     "Sp2": "askPrice2", "Sp3": "askPrice3" \
                , "Sp4": "askPrice4", "Sp5": "askPrice5", "Bv1": "bidVolume1", "Bv2": "bidVolume2", "Bv3": "bidVolume3",
                     "Bv4": "bidVolume4", "Bv5": "bidVolume5" \
                , "Sv1": "askVolume1", "Sv2": "askVolume2", "Sv3": "askVolume3", "Sv4": "askVolume4",
                     "Sv5": "askVolume5", "Tvolume": "volume"})

        # df['datetime'] = df['date'].str.cat(df['time'])
        # print(df['datetime'].astype(str) + " " + df['time'].astype(str))
        df['datetime'] = df['date'].astype(str) + " " + df['time'].astype(str)
        # df['datetime'] = df['datetime'].strftime('%Y/%m/%d %H:%M:%S.%f')
        df['datetime'] = pd.to_datetime(df['datetime'], format='%Y/%m/%d %H%M%S%f')

        row = df.to_dict('records')

        self.output(u'開始載入資料')
        #
        # if self.mode == self.BAR_MODE:
        #     dataClass = VtBarData
        # elif self.mode == self.TRADE_MODE:
        #     dataClass = VtTickData
        # elif self.mode == self.BOOK_MODE:
        #     dataClass = VtTickData
        # else:
        #     dataClass = VtTickData
        #
        # # 載入初始化需要用的資料
        # if self.hdsClient:
        #     initCursor = self.hdsClient.loadHistoryData(self.dbName,
        #                                                 self.symbol,
        #                                                 self.dataStartDate,
        #                                                 self.strategyStartDate)
        # else:
        #     flt = {'datetime': {'$gte': self.dataStartDate,
        #                         '$lt': self.strategyStartDate}}
        #     initCursor = row
        # # 將資料從查詢指標中讀取出，並生成列表
        # self.initData = []  # 清空initData列表
        #
        # for d in initCursor:
        #     data = dataClass()
        #     data.__dict__ = d
        #     self.initData.append(data)
        #
        # # 載入回測數據
        # if self.hdsClient:
        #     self.dbCursor = self.hdsClient.loadHistoryData(self.dbName,
        #                                                    self.symbol,
        #                                                    self.strategyStartDate,
        #                                                    self.dataEndDate)
        # else:
        #     if not self.dataEndDate:
        #         flt = {'datetime': {'$gte': self.strategyStartDate}}  # 資料過濾條件
        #     else:
        #         flt = {'datetime': {'$gte': self.strategyStartDate,
        #                             '$lte': self.dataEndDate}}
        self.dbCursor = row
        count = len(self.dbCursor)

        self.output(u'載入完成，資料量：%s' % count)

    # ----------------------------------------------------------------------

    def runBacktesting(self):
        """運行回測"""
        # 首先根據回測模式，確認要使用的資料類
        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
            func = self.newBar
        elif self.mode == self.TRADE_MODE:
            dataClass = VtTickData
            func = self.newTrade
        elif self.mode == self.BOOK_MODE:
            dataClass = VtTickData
            func = self.newBook
        else:
            dataClass = VtTickData
            func = self.newTradeBook

        self.output(u'開始回測')
        self.strategy.onInit()
        self.strategy.inited = True
        self.output(u'策略初始化完成')

        self.strategy.trading = True
        self.strategy.onStart()
        self.output(u'策略啟動完成')

        self.output(u'開始重播資料')

        for d in self.dbCursor:  # DB逐筆資料
            data = dataClass()
            data.__dict__ = d
            func(data)

        self.output(u'數據重播結束')

    # ----------------------------------------------------------------------
    def runBacktestingSql(self):
        """運行回測"""
        # 首先根據回測模式，確認要使用的資料類
        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
            func = self.newBar
        elif self.mode == self.TRADE_MODE:
            dataClass = VtTickData
            func = self.newTrade
        elif self.mode == self.BOOK_MODE:
            dataClass = VtTickData
            func = self.newBook
        else:
            dataClass = VtTickData
            func = self.newTradeBook

        self.output(u'開始回測')
        self.strategy.onInit()
        self.strategy.inited = True
        self.output(u'策略初始化完成')

        self.strategy.trading = True
        self.strategy.onStart()
        self.output(u'策略啟動完成')

        self.output(u'開始重播資料')
        headers = ['SeqNo', 'datetime', 'time', 'microSec', 'Seq', 'symbol', 'lastPrice', 'lastVolume', 'bidPrice1',
                   'bidPrice2', 'bidPrice3', 'bidPrice4', 'bidPrice5', 'askPrice1', 'askPrice2', 'askPrice3',
                   'askPrice4', 'askPrice5', \
                   'bidVolume1', 'bidVolume2', 'bidVolume3', 'bidVolume4', 'bidVolume5', 'askVolume1', 'askVolume2',
                   'askVolume3', 'askVolume4', 'askVolume5', 'ptype', 'volume', 'Status', 'MulticastGroup', 'MsgTime']
        for d in self.dbCursor:  # DB逐筆資料
            data = dataClass()
            data.__dict__ = dict(zip(headers, d))
            func(data)

        self.output(u'數據重播結束')

    # ----------------------------------------------------------------------

    def newBar(self, bar):
        """新的K線"""
        self.bar = bar
        self.dt = bar.datetime

        self.crossLimitOrder()  # 先撮合限價單
        self.crossStopOrder()  # 再撮合停止單
        self.strategy.onBar(bar)  # 推送K線到策略中

        self.updateDailyClose(bar.datetime, bar.close)

    # ----------------------------------------------------------------------
    def newTradeBook(self, tick):

        if tick.lastPrice > 0:
            self.newTrade(tick)
        else:
            self.newBook(tick)
    # ----------------------------------------------------------------------
    def newTrade(self, tick):
        """新的Tick"""
        self.tick = tick
        self.dt = tick.datetime

        # self.S.append(tick.lastPrice)
        # self.T.append(self.dt)

        # self.crossLimitOrder()
        # self.crossStopOrder()
        self.strategy.onTick(tick)

        # self.updateDailyClose(tick.datetime, tick.lastPrice)

    # ----------------------------------------------------------------------
    def newBook(self, tick):
        """新的Trade"""
        self.tick = tick
        self.dt = tick.datetime

        self.crossLimitOrder()
        # self.lagDealOrder()
        # self.cancelAll()
        # self.crossStopOrder()
        self.strategy.onBook(tick)

        # self.updateDailyClose(tick.datetime, tick.lastPrice)

    # ----------------------------------------------------------------------
    def initStrategy(self, strategyClass, setting=None):
        """
        初始化策略
        setting是策略的參數設置，如果使用類中寫好的默認設置則可以不傳該參數
        """
        self.strategy = strategyClass(self, setting)
        self.strategy.name = self.strategy.className

    # ----------------------------------------------------------------------
    def crossLimitOrder(self):
        """基於最新資料撮合限價單"""
        # 先確定會撮合成交的價格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low  # 若買入方向限價單價格高於該價格，則會成交
            sellCrossPrice = self.bar.high  # 若賣出方向限價單價格低於該價格，則會成交
            buyBestCrossPrice = self.bar.open  # 在當前時間點前發出的買入委託可能的最優成交價
            sellBestCrossPrice = self.bar.open  # 在當前時間點前發出的賣出委託可能的最優成交價
        elif self.mode == self.TRADE_MODE:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            buyBestCrossPrice = self.tick.lastPrice
            sellBestCrossPrice = self.tick.lastPrice
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1

        # Get index, find order list
        # 遍歷限價單字典中的所有限價單
        for orderID, order in self.workingLimitOrderDict.items():
            # 推送委託進入佇列（未成交）的狀態更新
            if not order.status:
                order.status = STATUS_NOTTRADED
                self.strategy.onOrder(order)

            if self.simulateMode == self.EASY_MODE:
                buyCross = (order.direction == DIRECTION_LONG )
                sellCross = (order.direction == DIRECTION_SHORT)

            elif self.simulateMode == self.DEFAULT_MODE:
                # 以080判斷是否成交
                buyCross = (order.direction == DIRECTION_LONG and
                            order.price >= buyCrossPrice and
                            buyCrossPrice > 0)

                sellCross = (order.direction == DIRECTION_SHORT and
                             order.price <= sellCrossPrice and
                             sellCrossPrice > 0)
            else:
                # 同時以080及020判斷是否成交
                if self.tick.lastPrice > 0:
                    buyCross = (order.direction == DIRECTION_LONG and
                                order.price >= self.tick.lastPrice)

                    sellCross = (order.direction == DIRECTION_SHORT and
                                 order.price <= self.tick.lastPrice)
                else:
                    buyCross = (order.direction == DIRECTION_LONG and
                                order.price >= buyCrossPrice and
                                buyCrossPrice > 0)

                    sellCross = (order.direction == DIRECTION_SHORT and
                                 order.price <= sellCrossPrice and
                                 sellCrossPrice > 0)

            # 如果發生了成交
            if buyCross or sellCross:
                # 推送成交資料
                self.tradeCount += 1  # 成交編號自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset
                trade.bookNumber = order.bookNumber

                if self.simulateMode == self.DEFAULT_MODE:
                    if buyCross:
                        trade.price = min(order.price, buyBestCrossPrice)
                    else:
                        trade.price = max(order.price, sellBestCrossPrice)
                else:
                    trade.price = order.price

                if buyCross:
                    self.strategy.pos += order.totalVolume
                    # self.pos.append(self.pos[-1] + 1)
                    # self.tradeTime.append(self.dt)
                    # self.BuyDeal.append(trade.price)
                    # self.BuyDealTime.append(self.tick.time)
                else:
                    self.strategy.pos -= order.totalVolume
                    # self.pos.append(self.pos[-1] - 1)
                    # self.tradeTime.append(self.dt)
                    # self.SellDeal.append(trade.price)
                    # self.SellDealTime.append(self.tick.time)
                # Print 成交資料
                if self.printMode == self.Detail_Mode:
                    print("tradeID: " + str(tradeID))
                    print("trade.price: " + str(trade.price))
                    print("trade.direction: " + trade.direction)
                    print("trade.time: " + str(self.tick.time))
                    # print("----------------------------------------------")

                trade.volume = order.totalVolume
                trade.tradeTime = self.dt.strftime('%H:%M:%S.%f')
                trade.dt = self.dt
                self.strategy.onTrade(trade)

                self.tradeDict[tradeID] = trade
                # 推送委託數據
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
                self.strategy.onOrder(order)

                # 從字典中刪除該限價單
                if orderID in self.workingLimitOrderDict:
                    del self.workingLimitOrderDict[orderID]


    # ----------------------------------------------------------------------
    def crossStopOrder(self):
        """基於最新資料撮合停止單"""
        # 先確定會撮合成交的價格，這裡和限價單規則相反
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.high  # 若買入方向停止單價格低於該價格，則會成交
            sellCrossPrice = self.bar.low  # 若賣出方向限價單價格高於該價格，則會成交
            bestCrossPrice = self.bar.open  # 最優成交價，買入停止單不能低於，賣出停止單不能高於
        elif self.mode == self.BOOK_MODE:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            bestCrossPrice = self.tick.lastPrice
        else:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            bestCrossPrice = self.tick.lastPrice

        # 遍歷停止單字典中的所有停止單
        for stopOrderID, so in self.workingStopOrderDict.items():
            # 判斷是否會成交
            buyCross = so.direction == DIRECTION_LONG and so.price <= buyCrossPrice
            sellCross = so.direction == DIRECTION_SHORT and so.price >= sellCrossPrice

            # 如果發生了成交
            if buyCross or sellCross:
                # 更新停止單狀態，並從字典中刪除該停止單
                so.status = STOPORDER_TRIGGERED
                if stopOrderID in self.workingStopOrderDict:
                    del self.workingStopOrderDict[stopOrderID]

                    # 推送成交資料
                self.tradeCount += 1  # 成交編號自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = so.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID

                if buyCross:
                    self.strategy.pos += so.volume
                    trade.price = max(bestCrossPrice, so.price)
                else:
                    self.strategy.pos -= so.volume
                    trade.price = min(bestCrossPrice, so.price)

                self.limitOrderCount += 1
                orderID = str(self.limitOrderCount)
                trade.orderID = orderID
                trade.vtOrderID = orderID
                trade.direction = so.direction
                trade.offset = so.offset
                trade.volume = so.volume
                trade.tradeTime = self.dt.strftime('%H:%M:%S.%f')
                trade.dt = self.dt

                self.tradeDict[tradeID] = trade

                # 推送委託數據
                order = VtOrderData()
                order.vtSymbol = so.vtSymbol
                order.symbol = so.vtSymbol
                order.orderID = orderID
                order.vtOrderID = orderID
                order.direction = so.direction
                order.offset = so.offset
                order.price = so.price
                order.totalVolume = so.volume
                order.tradedVolume = so.volume
                order.status = STATUS_ALLTRADED
                order.orderTime = trade.tradeTime

                self.limitOrderDict[orderID] = order

                # 按照順序推送資料
                self.strategy.onStopOrder(so)
                self.strategy.onOrder(order)
                self.strategy.onTrade(trade)

    # ------------------------------------------------
    # 策略介面相關
    # ------------------------------------------------

    # ----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """發單"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.bookNumber = self.strategy.onbook


        if self.simulateMode == self.EASY_MODE:
            order.price = price
        else:
            order.price = self.roundToPriceTick(price)

        order.totalVolume = volume
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = self.dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        # order.orderTime = self.tick.time

        # CTA委託類型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
            # self.OrderBuy.append(order.price)
            # self.OrderBuyTime.append(self.dt)
        elif orderType == CTAORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
            # self.OrderSell.append(order.price)
            # self.OrderSellTime.append(self.dt)
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
            # self.OrderSell.append(order.price)
            # self.OrderSellTime.append(self.dt)
        elif orderType == CTAORDER_COVER:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE
            # self.OrderBuy.append(order.price)
            # self.OrderBuyTime.append(self.dt)

        # 保存到限價單字典中
        self.workingLimitOrderDict[orderID] = order
        # 判斷insert位置，價 & orderID(binary tree)
        # self.sortedWorkingLimitOrderList.insert()
        self.limitOrderDict[orderID] = order
        if self.printMode == self.Detail_Mode:
            print("orderID: " + str(orderID))
            print("order.price: " + str(order.price))
            print("order.direction: " + order.direction)
            print("order.time: " + str(self.tick.time))
            print("order.bookNumber:" + str(order.bookNumber))
        return [orderID]

    # ----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤單"""
        if vtOrderID in self.workingLimitOrderDict:
            order = self.workingLimitOrderDict[vtOrderID]

            order.status = STATUS_CANCELLED
            order.cancelTime = self.dt.strftime('%H:%M:%S.%f')

            self.strategy.onOrder(order)

            del self.workingLimitOrderDict[vtOrderID]

    # ----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """發停止單（本地實現）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)

        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.price = self.roundToPriceTick(price)
        so.volume = volume
        so.strategy = strategy
        so.status = STOPORDER_WAITING
        so.stopOrderID = stopOrderID

        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE

            # 保存stopOrder物件到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so
        # 推送停止單初始更新
        self.strategy.onStopOrder(so)

        return [stopOrderID]

    # ----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤銷停止單"""
        # 檢查停止單是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]
            self.strategy.onStopOrder(so)

    # ----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """發送策略更新事件，回測中忽略"""
        pass

    # ----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """考慮到回測中不允許向資料庫插入資料，防止實盤交易中的一些代碼出錯"""
        pass

    # ----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, startDate):
        """直接返回初始化資料清單中的Bar"""
        return self.initData

    # ----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, startDate):
        """直接返回初始化資料清單中的Tick"""
        return self.initData

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """記錄日誌"""
        log = str(self.dt) + ' ' + content
        self.logList.append(log)

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤單"""
        # 撤銷限價單
        for orderID in self.workingLimitOrderDict.keys():
            self.cancelOrder(orderID)

        # 撤銷停止單
        for stopOrderID in self.workingStopOrderDict.keys():
            self.cancelStopOrder(stopOrderID)

    # ----------------------------------------------------------------------
    def saveSyncData(self, strategy):
        """保存同步資料（無效）"""
        pass

    # ----------------------------------------------------------------------
    def getPriceTick(self, strategy):
        """獲取最小價格變動"""
        return self.priceTick

    # ------------------------------------------------
    # 結果計算相關
    # ------------------------------------------------

    # ----------------------------------------------------------------------
    def calculateBacktestingResult(self):
        """
        計算回測結果
        """
        self.output(u'計算回測結果')
        # 檢查成交記錄

        if not self.tradeDict:
            self.output(u'成交記錄為空，無法計算回測結果')
            return {}

        # 首先基於回測後的成交記錄，計算每筆交易的盈虧
        resultList = []  # 交易結果清單

        longTrade = []  # 未平倉的多單
        shortTrade = []  # 未平倉的空單

        tradeTimeList = []  # 每筆成交時間戳記
        posList = []  # 每筆成交後的持倉情況

        for trade in self.tradeDict.values():
            # 複製成交物件，因為下面的開平倉交易配對涉及到對成交數量的修改
            # 若不進行複製直接操作，則計算完後所有成交的數量會變成0
            trade = copy.copy(trade)
            # 多頭交易
            if trade.direction == DIRECTION_LONG:
                # 如果尚無空頭交易
                if not shortTrade:
                    longTrade.append(trade)
                # 當前多頭交易為平空
                else:
                    while True:
                        entryTrade = shortTrade[0]
                        exitTrade = trade

                        # 清算開平倉交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               -closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([-1, 0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])
                        # 計算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果開倉交易已經全部清算，則從清單中移除
                        if not entryTrade.volume:
                            shortTrade.pop(0)

                        # 如果平倉交易已經全部清算，則退出迴圈
                        if not exitTrade.volume:
                            break

                        # 如果平倉交易未全部清算，
                        if exitTrade.volume:
                            # 且開倉交易已經全部清算完，則平倉交易剩餘的部分
                            # 等於新的反向開倉交易，添加到佇列中
                            if not shortTrade:
                                longTrade.append(exitTrade)
                                break
                            # 如果開倉交易還有剩餘，則進入下一輪迴圈
                            else:
                                pass

            # 空頭交易
            else:
                # 如果尚無多頭交易
                if not longTrade:
                    shortTrade.append(trade)
                # 當前空頭交易為平多
                else:
                    while True:
                        entryTrade = longTrade[0]
                        exitTrade = trade

                        # 清算開平倉交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([1, 0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 計算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果開倉交易已經全部清算，則從清單中移除
                        if not entryTrade.volume:
                            longTrade.pop(0)

                        # 如果平倉交易已經全部清算，則退出迴圈
                        if not exitTrade.volume:
                            break

                        # 如果平倉交易未全部清算，
                        if exitTrade.volume:
                            # 且開倉交易已經全部清算完，則平倉交易剩餘的部分
                            # 等於新的反向開倉交易，添加到佇列中
                            if not longTrade:
                                shortTrade.append(exitTrade)
                                break
                            # 如果開倉交易還有剩餘，則進入下一輪迴圈
                            else:
                                pass

        # 到最後交易日尚未平倉的交易，則以最後價格平倉
        if self.mode == self.BAR_MODE:
            endPrice = self.bar.close
        elif self.mode == self.BOOK_MODE:
            endPrice = (self.tick.bidPrice1 + self.tick.askPrice1) / 2
        else:
            endPrice = self.tick.lastPrice

        if self.printMode == self.Detail_Mode:
            print("endPrice: " + str(endPrice))

        for trade in longTrade:
            result = TradingResult(trade.price, trade.dt, endPrice, exitTrade.dt,
                                   trade.volume, self.rate, self.slippage, self.size)
            resultList.append(result)

        for trade in shortTrade:
            result = TradingResult(trade.price, trade.dt, endPrice, exitTrade.dt,
                                   -trade.volume, self.rate, self.slippage, self.size)
            resultList.append(result)

            # 檢查是否有交易
        if not resultList:
            self.output(u'無交易結果')
            return {}

        # 然後基於每筆交易的結果，我們可以計算具體的盈虧曲線和最大回撤等
        capital = 0  # 資金
        maxCapital = 0  # 資金最高淨值
        drawdown = 0  # 回撤

        totalResult = 0  # 總成交數量
        totalTurnover = 0  # 總成交金額（合約面值）
        totalCommission = 0  # 總手續費
        totalSlippage = 0  # 總滑點

        timeList = []  # 時間序列
        pnlList = []  # 每筆盈虧序列
        capitalList = []  # 盈虧匯總的時間序列
        drawdownList = []  # 回撤的時間序列

        winningResult = 0  # 盈利次數
        losingResult = 0  # 虧損次數
        totalWinning = 0  # 總盈利金額
        totalLosing = 0  # 總虧損金額

        for result in resultList:
            capital += result.pnl
            maxCapital = max(capital, maxCapital)
            drawdown = capital - maxCapital

            pnlList.append(result.pnl)
            timeList.append(result.exitDt)  # 交易的時間戳記使用平倉時間

            capitalList.append(capital)
            drawdownList.append(drawdown)

            totalResult += 1
            totalTurnover += result.turnover
            totalCommission += result.commission
            totalSlippage += result.slippage

            if result.pnl >= 0:
                winningResult += 1
                totalWinning += result.pnl
            else:
                losingResult += 1
                totalLosing += result.pnl

        # 計算盈虧相關資料
        winningRate = winningResult / totalResult * 100  # 勝率

        averageWinning = 0  # 這裡把資料都初始化為0
        averageLosing = 0
        profitLossRatio = 0

        if winningResult:
            averageWinning = totalWinning / winningResult  # 平均每筆盈利
        if losingResult:
            averageLosing = totalLosing / losingResult  # 平均每筆虧損
        if averageLosing:
            profitLossRatio = -averageWinning / averageLosing  # 盈虧比

        # 返回回測結果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['posList'] = posList
        d['tradeTimeList'] = tradeTimeList
        d['resultList'] = resultList

        return d

    # ----------------------------------------------------------------------
    def showBacktestingResult(self):
        """顯示回測結果"""
        d = self.calculateBacktestingResult()
        self.d_result = d

        # 輸出
        self.output('-' * 30)
        # self.output(u'第一筆交易平倉：\t%s' % d['timeList'][0])
        self.output(u'最後一筆交易平倉：\t%s' % d['timeList'][-1])

        self.output(u'總交易次數：\t%s' % formatNumber(d['totalResult']))
        self.output(u'總盈虧：\t%s' % formatNumber(d['capital']))
        self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))

        self.output(u'平均每筆盈利：\t%s' % formatNumber(d['capital'] / d['totalResult']))
        self.output(u'平均每筆滑點：\t%s' % formatNumber(d['totalSlippage'] / d['totalResult']))
        self.output(u'平均每筆傭金：\t%s' % formatNumber(d['totalCommission'] / d['totalResult']))

        self.output(u'勝率\t\t%s%%' % formatNumber(d['winningRate']))
        self.output(u'盈利交易平均值\t%s' % formatNumber(d['averageWinning']))
        self.output(u'虧損交易平均值\t%s' % formatNumber(d['averageLosing']))
        self.output(u'盈虧比：\t%s' % formatNumber(d['profitLossRatio']))

        self.output(u'勝率\t\t%s%%' % formatNumber(self.strategy.bingo/self.strategy.round*100))

    # ----------------------------------------------------------------------

    def plotResult(self):
        # 绘图

        fig = plt.figure(figsize=(10, 16))

        pCapital = plt.subplot(3, 1, 1)
        pCapital.set_ylabel("capital")
        pCapital.plot(self.d_result['capitalList'], color='r', lw=0.8)

        # pDD = plt.subplot(4, 1, 2)
        # pDD.set_ylabel("DD")
        # pDD.bar(range(len(self.d_result['drawdownList'])), self.d_result['drawdownList'], color='r')

        pPnl = plt.subplot(3, 1, 2)
        pPnl.set_ylabel("pnl")
        pPnl.hist(self.d_result['pnlList'], bins=50, color='c')

        pPos = plt.subplot(3, 1, 3)
        pPos.set_ylabel("Position")
        if self.d_result['posList'][-1] == 0:
            del self.d_result['posList'][-1]
        tradeTimeIndex = [item.strftime("%m/%d %H:%M:%S") for item in self.d_result['tradeTimeList']]
        xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex) / 10))
        tradeTimeIndex = list(map(lambda i: tradeTimeIndex[i], xindex))
        pPos.plot(self.d_result['posList'], color='k', drawstyle='steps-pre')
        plt.sca(pPos)
        plt.tight_layout()
        plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15

        plt.show()

    # ----------------------------------------------------------------------

    def plotResultWithTime(self):
        # 繪圖
        # fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1)
        fig, (ax1, ax3, ax4) = plt.subplots(3, 1, sharex=True, figsize=(10, 16))
        df1 = pd.DataFrame({'Time': self.T, 'S': self.S})

        df4 = pd.DataFrame({'Time': self.d_result['timeList'], 'capital': self.d_result['capitalList']})
        ax1.set_ylabel("capital")
        # ax1.plot(df1['Time'], df1['S'])
        times4 = [d.to_pydatetime() for d in df4.Time]
        ax1.plot(times4, df4['capital'], color='k', lw=0.8)

        df5 = pd.DataFrame({'Time': self.tradeTime, 'Position': self.pos})
        ax4.set_ylabel("Position")
        # ax4.plot(df1['Time'], df1['S'])
        times5 = [d.to_pydatetime() for d in df5.Time[1:]]
        ax4.plot(times5, df5['Position'][1:], color='r', lw=0.8)

        # tradeTimeIndex = [item.strftime("%m/%d %H:%M:%S") for item in self.d_result['tradeTimeList']]
        # xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex) / 10))
        # tradeTimeIndex = list(map(lambda i: tradeTimeIndex[i], xindex))

        # ax1.set_ylabel("capital")
        # ax1.plot(self.d_result['capitalList'], color='k')
        # plt.sca(ax1)
        # plt.tight_layout()
        # plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15
        #
        # ax4.set_ylabel("Position")
        # ax4.plot(self.pos, color='r')
        # plt.sca(ax4)
        # plt.tight_layout()
        # plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15

        # df4 = pd.DataFrame({'Time': self.tradeTime, 'capital': self.d_result['capitalList']})
        # ax1.plot(df1['Time'], df1['S'], color='c', lw=0.8)
        # times4 = [d.to_pydatetime() for d in df4.Time]
        # ax1.scatter(times4, df4['capital'], color='r')
        #
        #
        # ax1.plot(self.d_result['capitalList'], color='r', lw=0.8)
        # plt.sca(ax1)
        # # plt.tight_layout()
        # plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15

        # ax1.set_ylabel("capital")
        # ax1.plot(self.d_result['capitalList'], color='r', lw=0.8)

        # ax2.set_ylabel("DD")
        # ax2.bar(range(len(self.d_result['drawdownList'])), self.d_result['drawdownList'], color='g')

        ax3.set_ylabel("S")

        if self.plotMode == self.ORDER_MODE:
            df2 = pd.DataFrame({'Time': self.OrderBuyTime, 'OrderBuy': self.OrderBuy})
            df3 = pd.DataFrame({'Time': self.OrderSellTime, 'OrderSell': self.OrderSell})
            ax3.plot(df1['Time'], df1['S'], color='c', lw=0.8)
            times2 = [d.to_pydatetime() for d in df2.Time]
            ax3.plot(times2, df2['OrderBuy'], color='r', marker='o', linestyle="")
            times3 = [d.to_pydatetime() for d in df3.Time]
            ax3.plot(times3, df3['OrderSell'], color='g', marker='*', linestyle="")

        else:
            df2 = pd.DataFrame({'Time': self.BuyDealTime, 'BuyDeal': self.BuyDeal})
            df3 = pd.DataFrame({'Time': self.SellDealTime, 'SellDeal': self.SellDeal})
            ax3.plot(df1['Time'], df1['S'], color='c', lw=0.8)
            times2 = [d.to_pydatetime() for d in df2.Time]
            ax3.plot(times2, df2['BuyDeal'], color='r', marker='o', linestyle="")
            times3 = [d.to_pydatetime() for d in df3.Time]
            ax3.plot(times3, df3['SellDeal'], color='g', marker='*', linestyle="")

        # if self.d_result['posList'][-1] == 0:
        #     del self.d_result['posList'][-1]
        # tradeTimeIndex = [item.strftime("%m/%d %H:%M:%S.%f") for item in self.d_result['tradeTimeList']]
        # xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex) / 2))
        # tradeTimeIndex = map(lambda i: tradeTimeIndex[i], xindex)
        # ax4.plot(self.d_result['posList'], color='k', lw=0.8)
        # ax4.set_ylim(-1.2, 1.2)
        # plt.sca(ax4)
        # plt.tight_layout()
        # plt.xticks(rotation=90)  # 旋轉15
        plt.show()



    # ----------------------------------------------------------------------
    def decorateAx(self, ax, xs, ys, x_func):

        ax.plot(xs, ys, color="green", linewidth=1, linestyle="-")
        ax.plot(ax.get_xlim(), [0, 0], color="blue",
                linewidth=0.5, linestyle="--")
        if x_func:
            # set数据代理func
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(x_func))
        ax.grid(True)
        return

    # ----------------------------------------------------------------------
    def clearBacktestingResult(self):
        """清空之前回測的結果"""
        # 清空限價單相關
        self.limitOrderCount = 0
        self.limitOrderDict.clear()
        self.workingLimitOrderDict.clear()

        # 清空停止單相關
        self.stopOrderCount = 0
        self.stopOrderDict.clear()
        self.workingStopOrderDict.clear()

        # 清空成交相關
        self.tradeCount = 0
        self.tradeDict.clear()

    # ----------------------------------------------------------------------
    def runOptimization(self, strategyClass, optimizationSetting):
        """優化參數"""
        # 獲取優化設置
        settingList = optimizationSetting.generateSetting()
        targetName = optimizationSetting.optimizeTarget

        # 檢查參數設置問題
        if not settingList or not targetName:
            self.output(u'優化設置有問題，請檢查')

        # 遍歷優化
        resultList = []
        for setting in settingList:
            self.clearBacktestingResult()
            self.output('-' * 30)
            self.output('setting: %s' % str(setting))
            self.initStrategy(strategyClass, setting)
            self.runBacktesting()
            df = self.calculateDailyResult()
            df, d = self.calculateDailyStatistics(df)
            try:
                targetValue = d[targetName]
            except KeyError:
                targetValue = 0
            resultList.append(([str(setting)], targetValue, d))

        # 顯示結果
        resultList.sort(reverse=True, key=lambda result: result[1])
        self.output('-' * 30)
        self.output(u'優化結果：')
        for result in resultList:
            self.output(u'參數：%s，目標：%s' % (result[0], result[1]))
        return resultList

    # ----------------------------------------------------------------------
    def runParallelOptimization(self, strategyClass, optimizationSetting):
        """並行優化參數"""
        # 獲取優化設置
        settingList = optimizationSetting.generateSetting()
        targetName = optimizationSetting.optimizeTarget

        # 檢查參數設置問題
        if not settingList or not targetName:
            self.output(u'優化設置有問題，請檢查')

        # 多進程優化，啟動一個對應CPU核心數量的進程池
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        l = []

        for setting in settingList:
            l.append(pool.apply_async(optimize, (strategyClass, setting,
                                                 targetName, self.mode,
                                                 self.startDate, self.initDays, self.endDate,
                                                 self.slippage, self.rate, self.size, self.priceTick,
                                                 self.dbName, self.symbol)))
        pool.close()
        pool.join()

        # 顯示結果
        resultList = [res.get() for res in l]
        resultList.sort(reverse=True, key=lambda result: result[1])
        self.output('-' * 30)
        self.output(u'優化結果：')
        for result in resultList:
            self.output(u'參數：%s，目標：%s' % (result[0], result[1]))

        return resultList

    # ----------------------------------------------------------------------
    def updateDailyClose(self, dt, price):
        """更新每日收盤價"""
        date = dt.date()

        if date not in self.dailyResultDict:
            self.dailyResultDict[date] = DailyResult(date, price)
        else:
            self.dailyResultDict[date].closePrice = price

    # ----------------------------------------------------------------------
    def calculateDailyResult(self):
        """計算按日統計的交易結果"""
        self.output(u'計算按日統計結果')

        # 檢查成交記錄
        if not self.tradeDict:
            self.output(u'成交記錄為空，無法計算回測結果')
            return {}

        # 將成交添加到每日交易結果中
        for trade in self.tradeDict.values():
            date = trade.dt.date()
            dailyResult = self.dailyResultDict[date]
            dailyResult.addTrade(trade)

        # 遍歷計算每日結果
        previousClose = 0
        openPosition = 0
        for dailyResult in self.dailyResultDict.values():
            dailyResult.previousClose = previousClose
            previousClose = dailyResult.closePrice

            dailyResult.calculatePnl(openPosition, self.size, self.rate, self.slippage)
            openPosition = dailyResult.closePosition

        # 生成DataFrame
        resultDict = {k: [] for k in dailyResult.__dict__.keys()}
        for dailyResult in self.dailyResultDict.values():
            for k, v in dailyResult.__dict__.items():
                resultDict[k].append(v)

        resultDf = pd.DataFrame.from_dict(resultDict)

        # 計算衍生資料
        resultDf = resultDf.set_index('date')

        return resultDf

    # ----------------------------------------------------------------------
    def calculateDailyStatistics(self, df):
        """計算按日統計的結果"""
        df['balance'] = df['netPnl'].cumsum() + self.capital
        df['return'] = (np.log(df['balance']) - np.log(df['balance'].shift(1))).fillna(0)
        df['highlevel'] = df['balance'].rolling(min_periods=1, window=len(df), center=False).max()
        df['drawdown'] = df['balance'] - df['highlevel']
        df['ddPercent'] = df['drawdown'] / df['highlevel'] * 100

        # 計算統計結果
        startDate = df.index[0]
        endDate = df.index[-1]

        totalDays = len(df)
        profitDays = len(df[df['netPnl'] > 0])
        lossDays = len(df[df['netPnl'] < 0])

        endBalance = df['balance'].iloc[-1]
        maxDrawdown = df['drawdown'].min()
        maxDdPercent = df['ddPercent'].min()

        totalNetPnl = df['netPnl'].sum()
        dailyNetPnl = totalNetPnl / totalDays

        totalCommission = df['commission'].sum()
        dailyCommission = totalCommission / totalDays

        totalSlippage = df['slippage'].sum()
        dailySlippage = totalSlippage / totalDays

        totalTurnover = df['turnover'].sum()
        dailyTurnover = totalTurnover / totalDays

        totalTradeCount = df['tradeCount'].sum()
        dailyTradeCount = totalTradeCount / totalDays

        totalReturn = (endBalance / self.capital - 1) * 100
        annualizedReturn = totalReturn / totalDays * 240
        dailyReturn = df['return'].mean() * 100
        returnStd = df['return'].std() * 100

        if returnStd:
            sharpeRatio = dailyReturn / returnStd * np.sqrt(240)
        else:
            sharpeRatio = 0

        # 返回結果
        result = {
            'startDate': startDate,
            'endDate': endDate,
            'totalDays': totalDays,
            'profitDays': profitDays,
            'lossDays': lossDays,
            'endBalance': endBalance,
            'maxDrawdown': maxDrawdown,
            'maxDdPercent': maxDdPercent,
            'totalNetPnl': totalNetPnl,
            'dailyNetPnl': dailyNetPnl,
            'totalCommission': totalCommission,
            'dailyCommission': dailyCommission,
            'totalSlippage': totalSlippage,
            'dailySlippage': dailySlippage,
            'totalTurnover': totalTurnover,
            'dailyTurnover': dailyTurnover,
            'totalTradeCount': totalTradeCount,
            'dailyTradeCount': dailyTradeCount,
            'totalReturn': totalReturn,
            'annualizedReturn': annualizedReturn,
            'dailyReturn': dailyReturn,
            'returnStd': returnStd,
            'sharpeRatio': sharpeRatio
        }

        return df, result

    # ----------------------------------------------------------------------
    def showDailyResult(self, df=None, result=None):
        """顯示按日統計的交易結果"""
        if df is None:
            df = self.calculateDailyResult()
            df, result = self.calculateDailyStatistics(df)

        # 輸出統計結果
        self.output('-' * 30)
        self.output(u'首個交易日：\t%s' % result['startDate'])
        self.output(u'最後交易日：\t%s' % result['endDate'])

        self.output(u'總交易日：\t%s' % result['totalDays'])
        self.output(u'盈利交易日\t%s' % result['profitDays'])
        self.output(u'虧損交易日：\t%s' % result['lossDays'])

        self.output(u'起始資金：\t%s' % self.capital)
        self.output(u'結束資金：\t%s' % formatNumber(result['endBalance']))

        self.output(u'總收益率：\t%s%%' % formatNumber(result['totalReturn']))
        self.output(u'年化收益：\t%s%%' % formatNumber(result['annualizedReturn']))
        self.output(u'總盈虧：\t%s' % formatNumber(result['totalNetPnl']))
        self.output(u'最大回撤: \t%s' % formatNumber(result['maxDrawdown']))
        self.output(u'百分比最大回撤: %s%%' % formatNumber(result['maxDdPercent']))

        self.output(u'總手續費：\t%s' % formatNumber(result['totalCommission']))
        self.output(u'總滑點：\t%s' % formatNumber(result['totalSlippage']))
        self.output(u'總成交金額：\t%s' % formatNumber(result['totalTurnover']))
        self.output(u'總成交筆數：\t%s' % formatNumber(result['totalTradeCount']))

        self.output(u'日均盈虧：\t%s' % formatNumber(result['dailyNetPnl']))
        self.output(u'日均手續費：\t%s' % formatNumber(result['dailyCommission']))
        self.output(u'日均滑點：\t%s' % formatNumber(result['dailySlippage']))
        self.output(u'日均成交金額：\t%s' % formatNumber(result['dailyTurnover']))
        self.output(u'日均成交筆數：\t%s' % formatNumber(result['dailyTradeCount']))

        self.output(u'日均收益率：\t%s%%' % formatNumber(result['dailyReturn']))
        self.output(u'收益標準差：\t%s%%' % formatNumber(result['returnStd']))
        self.output(u'Sharpe Ratio：\t%s' % formatNumber(result['sharpeRatio']))

        # 繪圖
        fig = plt.figure(figsize=(10, 16))

        pBalance = plt.subplot(4, 1, 1)
        pBalance.set_title('Balance')
        df['balance'].plot(legend=True)

        pDrawdown = plt.subplot(4, 1, 2)
        pDrawdown.set_title('Drawdown')
        pDrawdown.fill_between(range(len(df)), df['drawdown'].values)

        pPnl = plt.subplot(4, 1, 3)
        pPnl.set_title('Daily Pnl')
        df['netPnl'].plot(kind='bar', legend=False, grid=False, xticks=[])

        pKDE = plt.subplot(4, 1, 4)
        pKDE.set_title('Daily Pnl Distribution')
        df['netPnl'].hist(bins=50)

        plt.show()


########################################################################
class TradingResult(object):
    """每筆交易的結果"""

    # ----------------------------------------------------------------------
    def __init__(self, entryPrice, entryDt, exitPrice,
                 exitDt, volume, rate, slippage, size):
        """Constructor"""
        self.entryPrice = entryPrice  # 開倉價格
        self.exitPrice = exitPrice  # 平倉價格

        self.entryDt = entryDt  # 開倉時間datetime
        self.exitDt = exitDt  # 平倉時間

        self.volume = volume  # 交易數量（+/-代表方向）

        self.turnover = (self.entryPrice + self.exitPrice) * size * abs(volume)  # 成交金額
        self.commission = self.turnover * rate  # 手續費成本
        self.slippage = slippage * 2 * size * abs(volume)  # 滑點成本
        self.pnl = ((self.exitPrice - self.entryPrice) * volume * size
                    - self.commission - self.slippage)  # 淨盈虧


########################################################################
class DailyResult(object):
    """每日交易的結果"""

    # ----------------------------------------------------------------------
    def __init__(self, date, closePrice):
        """Constructor"""
        self.date = date  # 日期
        self.closePrice = closePrice  # 當日收盤價
        self.previousClose = 0  # 昨日收盤價

        self.tradeList = []  # 成交列表
        self.tradeCount = 0  # 成交數量

        self.openPosition = 0  # 開盤時的持倉
        self.closePosition = 0  # 收盤時的持倉

        self.tradingPnl = 0  # 交易盈虧
        self.positionPnl = 0  # 持倉盈虧
        self.totalPnl = 0  # 總盈虧

        self.turnover = 0  # 成交量
        self.commission = 0  # 手續費
        self.slippage = 0  # 滑點
        self.netPnl = 0  # 淨盈虧

    # ----------------------------------------------------------------------
    def addTrade(self, trade):
        """添加交易"""
        self.tradeList.append(trade)

    # ----------------------------------------------------------------------
    def calculatePnl(self, openPosition=0, size=1, rate=0, slippage=0):
        """
        計算盈虧
        size: 合約乘數
        rate：手續費率
        slippage：滑點點數
        """
        # 持倉部分
        self.openPosition = openPosition
        self.positionPnl = self.openPosition * (self.closePrice - self.previousClose) * size
        self.closePosition = self.openPosition

        # 交易部分
        self.tradeCount = len(self.tradeList)

        for trade in self.tradeList:
            if trade.direction == DIRECTION_LONG:
                posChange = trade.volume
            else:
                posChange = -trade.volume

            self.tradingPnl += posChange * (self.closePrice - trade.price) * size
            self.closePosition += posChange
            self.turnover += trade.price * trade.volume * size
            self.commission += trade.price * trade.volume * size * rate
            self.slippage += trade.volume * size * slippage

        # 匯總
        self.totalPnl = self.tradingPnl + self.positionPnl
        self.netPnl = self.totalPnl - self.commission - self.slippage


########################################################################
class OptimizationSetting(object):
    """優化設置"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.paramDict = OrderedDict()

        self.optimizeTarget = ''  # 優化目標欄位

    # ----------------------------------------------------------------------
    def addParameter(self, name, start, end=None, step=None):
        """增加優化參數"""
        if end is None and step is None:
            self.paramDict[name] = [start]
            return

        if end < start:
            print(u'參數起始點必須不大於終止點')
            return

        if step <= 0:
            print(u'參數布進必須大於0')
            return

        l = []
        param = start

        while param <= end:
            l.append(param)
            param += step

        self.paramDict[name] = l

    # ----------------------------------------------------------------------
    def generateSetting(self):
        """生成優化參數組合"""
        # 參數名的列表
        nameList = self.paramDict.keys()
        paramList = self.paramDict.values()

        # 使用反覆運算工具生產參數對組合
        productList = list(product(*paramList))

        # 把參數對組合打包到一個個字典組成的清單中
        settingList = []
        for p in productList:
            d = dict(zip(nameList, p))
            settingList.append(d)

        return settingList

    # ----------------------------------------------------------------------
    def setOptimizeTarget(self, target):
        """設置優化目標欄位"""
        self.optimizeTarget = target


########################################################################
class HistoryDataServer(RpcServer):
    """歷史資料緩存伺服器"""

    # ----------------------------------------------------------------------
    def __init__(self, repAddress, pubAddress):
        """Constructor"""
        super(HistoryDataServer, self).__init__(repAddress, pubAddress)

        self.dbClient = pymongo.MongoClient(globalSetting['mongoHost'],
                                            globalSetting['mongoPort'])

        self.historyDict = {}

        self.register(self.loadHistoryData)

    # ----------------------------------------------------------------------
    def loadHistoryData(self, dbName, symbol, start, end):
        """"""
        # 首先檢查是否有緩存，如果有則直接返回
        history = self.historyDict.get((dbName, symbol, start, end), None)
        if history:
            print(u'找到記憶體緩存：%s %s %s %s' % (dbName, symbol, start, end))
            return history

        # 否則從資料庫載入
        collection = self.dbClient[dbName][symbol]

        if end:
            flt = {'datetime': {'$gte': start, '$lt': end}}
        else:
            flt = {'datetime': {'$gte': start}}

        cx = collection.find(flt).sort('datetime')
        history = [d for d in cx]

        self.historyDict[(dbName, symbol, start, end)] = history
        print(u'從資料庫載入：%s %s %s %s' % (dbName, symbol, start, end))
        return history


# ----------------------------------------------------------------------
def runHistoryDataServer():
    """"""
    repAddress = 'tcp://*:5555'
    pubAddress = 'tcp://*:7777'

    hds = HistoryDataServer(repAddress, pubAddress)
    hds.start()

    print(u'按任意鍵退出')
    hds.stop()
    raw_input()


# ----------------------------------------------------------------------
def formatNumber(n):
    """格式化數位到字串"""
    rn = round(n, 2)  # 保留兩位小數
    return format(rn, ',')  # 加上千分符


# ----------------------------------------------------------------------
def optimize(strategyClass, setting, targetName,
             mode, startDate, initDays, endDate,
             slippage, rate, size, priceTick,
             dbName, symbol):
    """多進程優化時跑在每個進程中運行的函數"""
    engine = BacktestingEngine()
    engine.setBacktestingMode(mode)
    engine.setStartDate(startDate, initDays)
    engine.setEndDate(endDate)
    engine.setSlippage(slippage)
    engine.setRate(rate)
    engine.setSize(size)
    engine.setPriceTick(priceTick)
    engine.setDatabase(dbName, symbol)

    engine.initStrategy(strategyClass, setting)
    engine.runBacktesting()

    df = engine.calculateDailyResult()
    df, d = engine.calculateDailyStatistics(df)
    try:
        targetValue = d[targetName]
    except KeyError:
        targetValue = 0
    return (str(setting), targetValue, d)


