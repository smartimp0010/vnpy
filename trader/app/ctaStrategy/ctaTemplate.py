# encoding: UTF-8

'''
本檔包含了CTA引擎中的策略開發用範本，開發策略時需要繼承CtaTemplate類。
'''

import numpy as np
import talib

from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData, VtTickData
import math
from .ctaBase import *
import scipy.stats as stats

########################################################################
class CtaTemplate(object):
    """CTA策略範本"""

    # 策略類的名稱和作者
    className = 'CtaTemplate'
    author = EMPTY_UNICODE

    # MongoDB資料庫的名稱，K線資料庫預設為1分鐘
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME

    # 策略的基本參數
    name = EMPTY_UNICODE  # 策略實例名稱
    vtSymbol = EMPTY_STRING  # 交易的合約vt系統代碼
    productClass = EMPTY_STRING  # 產品類型（只有IB介面需要）
    currency = EMPTY_STRING  # 貨幣（只有IB介面需要）

    # 策略的基本變數，由引擎管理
    inited = False  # 是否進行了初始化
    trading = False  # 是否啟動交易，由引擎管理
    pos = 0  # 持倉情況

    # 參數列表，保存了參數的名稱
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']

    # 變數清單，保存了變數的名稱
    varList = ['inited',
               'trading',
               'pos']

    # 同步清單，保存了需要保存到資料庫的變數名稱
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        # 設置策略的參數
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStart(self):
        """啟動策略（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委託變化推送（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """收到停止單推送（必須由用戶繼承實現）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def buy(self, price, volume, stop=False):
        """買開"""
        return self.sendOrder(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell(self, price, volume, stop=False):
        """賣平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, stop)

        # ----------------------------------------------------------------------

    def short(self, price, volume, stop=False):
        """賣開"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, stop)

        # ----------------------------------------------------------------------

    def cover(self, price, volume, stop=False):
        """買平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, stop)

    # ----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, stop=False):
        """發送委託"""
        if self.trading:
            # 如果stop為True，則意味著發本地停止單
            if stop:
                vtOrderIDList = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderIDList = self.ctaEngine.sendOrder(self.vtSymbol, orderType, price, volume, self)
            return vtOrderIDList
        else:
            # 交易停止時發單返回空字串
            return []

    # ----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤單"""
        # 如果發單號為空字串，則不進行後續操作
        if not vtOrderID:
            return

        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤單"""
        self.ctaEngine.cancelAll(self.name)

    # ----------------------------------------------------------------------
    def insertTick(self, tick):
        """向資料庫中插入tick資料"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)

    # ----------------------------------------------------------------------
    def insertBar(self, bar):
        """向資料庫中插入bar資料"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)

    # ----------------------------------------------------------------------
    def loadTick(self, days):
        """讀取tick數據"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def loadBar(self, days):
        """讀取bar數據"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """記錄CTA日誌"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    # ----------------------------------------------------------------------
    def putEvent(self):
        """發出策略狀態變化事件"""
        self.ctaEngine.putStrategyEvent(self.name)  # ctaBacktesting.py

    # ----------------------------------------------------------------------
    def getEngineType(self):
        """查詢當前運行的環境"""
        return self.ctaEngine.engineType

    # ----------------------------------------------------------------------
    def saveSyncData(self):
        """保存同步資料到資料庫"""
        if self.trading:
            self.ctaEngine.saveSyncData(self)

    # ----------------------------------------------------------------------
    def getPriceTick(self):
        """查詢最小價格變動"""
        return self.ctaEngine.getPriceTick(self)


########################################################################
class TargetPosTemplate(CtaTemplate):
    """
    允許直接通過修改目標持倉來實現交易的策略範本

    開發策略時，無需再調用buy/sell/cover/short這些具體的委託指令，
    只需在策略邏輯運行完成後調用setTargetPos設置目標持倉，底層演算法
    會自動完成相關交易，適合不擅長管理交易掛撤單細節的用戶。

    使用該範本開發策略時，請在以下回檔方法中先調用母類的方法：
    onTick
    onBar
    onOrder

    假設策略名為TestStrategy，請在onTick回檔中加上：
    super(TestStrategy, self).onTick(tick)

    其他方法類同。
    """

    className = 'TargetPosTemplate'
    author = u'量衍投資'

    # 目標持倉範本的基本變數
    tickAdd = 1  # 委託時相對基準價格的超價
    lastTick = None  # 最新tick資料
    lastBar = None  # 最新bar資料
    targetPos = EMPTY_INT  # 目標持倉
    orderList = []  # 委託號列表

    # 變數清單，保存了變數的名稱
    varList = ['inited',
               'trading',
               'pos',
               'targetPos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TargetPosTemplate, self).__init__(ctaEngine, setting)

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情推送"""
        self.lastTick = tick

        # 實盤模式下，啟動交易後，需要根據tick的即時推送執行自動開平倉操作
        if self.trading:
            self.trade()

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到K線推送"""
        self.lastBar = bar

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委託推送"""
        if order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED:
            if order.vtOrderID in self.orderList:
                self.orderList.remove(order.vtOrderID)

    # ----------------------------------------------------------------------
    def setTargetPos(self, targetPos):
        """設置目標倉位元"""
        self.targetPos = targetPos

        self.trade()

    # ----------------------------------------------------------------------
    def trade(self):
        """執行交易"""
        # 先撤銷之前的委託
        self.cancelAll()

        # 如果目標倉位元和實際倉位一致，則不進行任何操作
        posChange = self.targetPos - self.pos
        if not posChange:
            return

        # 確定委託基準價格，有tick資料時優先使用，否則使用bar
        longPrice = 0
        shortPrice = 0

        if self.lastTick:
            if posChange > 0:
                longPrice = self.lastTick.askPrice1 + self.tickAdd
                if self.lastTick.upperLimit:
                    longPrice = min(longPrice, self.lastTick.upperLimit)  # 漲停價檢查
            else:
                shortPrice = self.lastTick.bidPrice1 - self.tickAdd
                if self.lastTick.lowerLimit:
                    shortPrice = max(shortPrice, self.lastTick.lowerLimit)  # 跌停價檢查
        else:
            if posChange > 0:
                longPrice = self.lastBar.close + self.tickAdd
            else:
                shortPrice = self.lastBar.close - self.tickAdd

        # 回測模式下，採用合併平倉和反向開倉委託的方式
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            if posChange > 0:
                l = self.buy(longPrice, abs(posChange))
            else:
                l = self.short(shortPrice, abs(posChange))
            self.orderList.extend(l)

        # 實盤模式下，首先確保之前的委託都已經結束（全成、撤銷）
        # 然後先發平倉委託，等待成交後，再發送新的開倉委託
        else:
            # 檢查之前委託都已結束
            if self.orderList:
                return

            # 買入
            if posChange > 0:
                # 若當前有空頭持倉
                if self.pos < 0:
                    # 若買入量小於空頭持倉，則直接平空買入量
                    if posChange < abs(self.pos):
                        l = self.cover(longPrice, posChange)
                    # 否則先平所有的空頭倉位
                    else:
                        l = self.cover(longPrice, abs(self.pos))
                # 若沒有空頭持倉，則執行開倉操作
                else:
                    l = self.buy(longPrice, abs(posChange))
            # 賣出和以上相反
            else:
                if self.pos > 0:
                    if abs(posChange) < self.pos:
                        l = self.sell(shortPrice, abs(posChange))
                    else:
                        l = self.sell(shortPrice, abs(self.pos))
                else:
                    l = self.short(shortPrice, abs(posChange))
            self.orderList.extend(l)


########################################################################
class BarGenerator(object):
    """
    K線合成器，支持：
    1. 基於Tick合成1分鐘K線
    2. 基於1分鐘K線合成X分鐘K線（X可以是2、3、5、10、15、30   ）
    """

    # ----------------------------------------------------------------------
    def __init__(self, onBar, xmin=0, onXminBar=None):
        """Constructor"""
        self.bar = None  # 1分鐘K線對象
        self.onBar = onBar  # 1分鐘K線回呼函數

        self.xminBar = None  # X分鐘K線對象
        self.xmin = xmin  # X的值
        self.onXminBar = onXminBar  # X分鐘K線的回呼函數

        self.lastTick = None  # 上一TICK緩存對象

    # ----------------------------------------------------------------------
    def updateTick(self, tick):
        """TICK更新"""
        newMinute = False  # 默認不是新的一分鐘

        # 尚未創建對象
        if not self.bar:
            self.bar = VtBarData()
            newMinute = True
        # 新的一分鐘
        elif self.bar.datetime.minute != tick.datetime.minute:
            # 生成上一分鐘K線的時間戳記
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 將秒和微秒設為0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')

            # 推送已經結束的上一分鐘K線
            self.onBar(self.bar)

            # 創建新的K線物件
            self.bar = VtBarData()
            newMinute = True

        # 初始化新一分鐘的K線資料
        if newMinute:
            self.bar.vtSymbol = tick.vtSymbol
            self.bar.symbol = tick.symbol
            self.bar.exchange = tick.exchange

            self.bar.open = tick.lastPrice
            self.bar.high = tick.lastPrice
            self.bar.low = tick.lastPrice
        # 累加更新老一分鐘的K線資料
        else:
            self.bar.high = max(self.bar.high, tick.lastPrice)
            self.bar.low = min(self.bar.low, tick.lastPrice)

        # 通用更新部分
        self.bar.close = tick.lastPrice
        self.bar.datetime = tick.datetime
        self.bar.openInterest = tick.openInterest

        if self.lastTick:
            volumeChange = tick.volume - self.lastTick.volume  # 當前K線內的成交量
            self.bar.volume += max(volumeChange, 0)  # 避免夜盤開盤lastTick.volume為昨日收盤資料，導致成交量變化為負的情況

        # 緩存Tick
        self.lastTick = tick

    # ----------------------------------------------------------------------
    def updateBar(self, bar):
        """1分鐘K線更新"""
        # 尚未創建對象
        if not self.xminBar:
            self.xminBar = VtBarData()

            self.xminBar.vtSymbol = bar.vtSymbol
            self.xminBar.symbol = bar.symbol
            self.xminBar.exchange = bar.exchange

            self.xminBar.open = bar.open
            self.xminBar.high = bar.high
            self.xminBar.low = bar.low

            self.xminBar.datetime = bar.datetime  # 以第一根分鐘K線的開始時間戳記作為X分鐘線的時間戳記
        # 累加老K線
        else:
            self.xminBar.high = max(self.xminBar.high, bar.high)
            self.xminBar.low = min(self.xminBar.low, bar.low)

        # 通用部分
        self.xminBar.close = bar.close
        self.xminBar.openInterest = bar.openInterest
        self.xminBar.volume += int(bar.volume)

        # X分鐘已經走完
        if not (bar.datetime.minute + 1) % self.xmin:  # 可以用X整除
            # 生成上一X分鐘K線的時間戳記
            self.xminBar.datetime = self.xminBar.datetime.replace(second=0, microsecond=0)  # 將秒和微秒設為0
            self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
            self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S.%f')

            # 推送
            self.onXminBar(self.xminBar)

            # 清空老K線緩存對象
            self.xminBar = None

    # ----------------------------------------------------------------------
    def generate(self):
        """手動強制立即完成K線合成"""
        self.onBar(self.bar)
        self.bar = None


########################################################################
class ArrayManager(object):
    """
    K線序列管理工具，負責：
    1. K線時間序列的維護
    2. 常用技術指標的計算
    """

    # ----------------------------------------------------------------------
    def __init__(self, size=100):
        """Constructor"""
        self.count = 0  # 緩存計數
        self.size = size  # 緩存大小
        self.inited = False  # True if count>=size

        self.openArray = np.zeros(size)  # OHLC
        self.highArray = np.zeros(size)
        self.lowArray = np.zeros(size)
        self.closeArray = np.zeros(size)
        self.volumeArray = np.zeros(size)

    # ----------------------------------------------------------------------
    def updateBar(self, bar):
        """更新K線"""
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True

        self.openArray[0:self.size - 1] = self.openArray[1:self.size]
        self.highArray[0:self.size - 1] = self.highArray[1:self.size]
        self.lowArray[0:self.size - 1] = self.lowArray[1:self.size]
        self.closeArray[0:self.size - 1] = self.closeArray[1:self.size]
        self.volumeArray[0:self.size - 1] = self.volumeArray[1:self.size]

        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume

    # ----------------------------------------------------------------------
    @property
    def open(self):
        """獲取開盤價序列"""
        return self.openArray

    # ----------------------------------------------------------------------
    @property
    def high(self):
        """獲取最高價序列"""
        return self.highArray

    # ----------------------------------------------------------------------
    @property
    def low(self):
        """獲取最低價序列"""
        return self.lowArray

    # ----------------------------------------------------------------------
    @property
    def close(self):
        """獲取收盤價序列"""
        return self.closeArray

    # ----------------------------------------------------------------------
    @property
    def volume(self):
        """獲取成交量序列"""
        return self.volumeArray

    # ----------------------------------------------------------------------
    def sma(self, n, array=False):
        """簡單均線"""
        result = talib.SMA(self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def std(self, n, array=False):
        """標準差"""
        result = talib.STDDEV(self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def cci(self, n, array=False):
        """CCI指標"""
        result = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def atr(self, n, array=False):
        """ATR指標"""
        result = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def rsi(self, n, array=False):
        """RSI指標"""
        result = talib.RSI(self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def macd(self, fastPeriod, slowPeriod, signalPeriod, array=False):
        """MACD指標"""
        macd, signal, hist = talib.MACD(self.close, fastPeriod,
                                        slowPeriod, signalPeriod)
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]

    # ----------------------------------------------------------------------
    def adx(self, n, array=False):
        """ADX指標"""
        result = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]

    # ----------------------------------------------------------------------
    def boll(self, n, dev, array=False):
        """布林通道"""
        mid = self.sma(n, array)
        std = self.std(n, array)

        up = mid + std * dev
        down = mid - std * dev

        return up, down

        # ----------------------------------------------------------------------

    def keltner(self, n, dev, array=False):
        """肯特納通道"""
        mid = self.sma(n, array)
        atr = self.atr(n, array)

        up = mid + atr * dev
        down = mid - atr * dev

        return up, down

    # ----------------------------------------------------------------------
    def donchian(self, n, array=False):
        """唐奇安通道"""
        up = talib.MAX(self.high, n)
        down = talib.MIN(self.low, n)

        if array:
            return up, down
        return up[-1], down[-1]


class TickArrayManager(object):
    """
    Tick序列管理工具，負責：
    1. Tick時間序列的維護
    2. 常用技術指標的計算
    """

    # ----------------------------------------------------------------------
    def __init__(self, size, N1, N2):
        """Constructor"""
        self.bookCount = 0  # 緩存計數
        self.tradeCount = 0
        self.innerCount = 0
        self.voiCount = 0
        self.size = size  # 緩存大小
        self.inited = False  # True if count>=size

        self.N1 = N1
        self.N2 = N2

        self.upOverPrice = 0
        self.downOverPrice = 0

        self.innerBuyVolume = 0
        self.innerBuyCount = 0
        self.innerSellVolume = 0
        self.innerSellCount = 0

        self.TicklastPriceArray = np.zeros(size)
        self.TicklastVolumeArray = np.zeros(size)
        self.TickaskVolume1Array = np.zeros(size)
        self.TickaskVolume2Array = np.zeros(size)
        self.TickaskVolume3Array = np.zeros(size)
        self.TickaskVolume4Array = np.zeros(size)
        self.TickaskVolume5Array = np.zeros(size)

        self.TickbidVolume1Array = np.zeros(size)
        self.TickbidVolume2Array = np.zeros(size)
        self.TickbidVolume3Array = np.zeros(size)
        self.TickbidVolume4Array = np.zeros(size)
        self.TickbidVolume5Array = np.zeros(size)

        self.TickaskPrice1Array = np.zeros(size)
        self.TickaskPrice2Array = np.zeros(size)
        self.TickaskPrice3Array = np.zeros(size)
        self.TickaskPrice4Array = np.zeros(size)
        self.TickaskPrice5Array = np.zeros(size)

        self.TickbidPrice1Array = np.zeros(size)
        self.TickbidPrice2Array = np.zeros(size)
        self.TickbidPrice3Array = np.zeros(size)
        self.TickbidPrice4Array = np.zeros(size)
        self.TickbidPrice5Array = np.zeros(size)

        self.TickvolumeArray = np.zeros(size)



        self.diffBuySellVolArray = np.zeros(N1)
        self.diffBuySellCountArray = np.zeros(N2)
        self.diffBuySellVol = 0
        self.diffBuySellCount = 0
        self.VOI = 0

    # ----------------------------------------------------------------------
    def updateBook(self, tick):
        """更新tick Array"""

        self.bookCount += 1

        # if not self.inited and self.count >= self.size:
        # if self.bookCount >= self.size:

        self.inited = True

        self.TickaskVolume1Array[0:self.size - 1] = self.TickaskVolume1Array[1:self.size]
        # self.TickaskVolume2Array[0:self.size - 1] = self.TickaskVolume2Array[1:self.size]
        # self.TickaskVolume3Array[0:self.size - 1] = self.TickaskVolume3Array[1:self.size]
        # self.TickaskVolume4Array[0:self.size - 1] = self.TickaskVolume4Array[1:self.size]
        # self.TickaskVolume5Array[0:self.size - 1] = self.TickaskVolume5Array[1:self.size]

        self.TickbidVolume1Array[0:self.size - 1] = self.TickbidVolume1Array[1:self.size]
        # self.TickbidVolume2Array[0:self.size - 1] = self.TickbidVolume2Array[1:self.size]
        # self.TickbidVolume3Array[0:self.size - 1] = self.TickbidVolume3Array[1:self.size]
        # self.TickbidVolume4Array[0:self.size - 1] = self.TickbidVolume4Array[1:self.size]
        # self.TickbidVolume5Array[0:self.size - 1] = self.TickbidVolume5Array[1:self.size]

        self.TickaskPrice1Array[0:self.size - 1] = self.TickaskPrice1Array[1:self.size]
        # self.TickaskPrice2Array[0:self.size - 1] = self.TickaskPrice2Array[1:self.size]
        # self.TickaskPrice3Array[0:self.size - 1] = self.TickaskPrice3Array[1:self.size]
        # self.TickaskPrice4Array[0:self.size - 1] = self.TickaskPrice4Array[1:self.size]
        # self.TickaskPrice5Array[0:self.size - 1] = self.TickaskPrice5Array[1:self.size]

        self.TickbidPrice1Array[0:self.size - 1] = self.TickbidPrice1Array[1:self.size]
        # self.TickbidPrice2Array[0:self.size - 1] = self.TickbidPrice2Array[1:self.size]
        # self.TickbidPrice3Array[0:self.size - 1] = self.TickbidPrice3Array[1:self.size]
        # self.TickbidPrice4Array[0:self.size - 1] = self.TickbidPrice4Array[1:self.size]
        # self.TickbidPrice5Array[0:self.size - 1] = self.TickbidPrice5Array[1:self.size]

        self.TickaskVolume1Array[-1] = tick.askVolume1
        # self.TickaskVolume2Array[-1] = tick.askVolume2
        # self.TickaskVolume3Array[-1] = tick.askVolume3
        # self.TickaskVolume4Array[-1] = tick.askVolume4
        # self.TickaskVolume5Array[-1] = tick.askVolume5

        self.TickbidVolume1Array[-1] = tick.bidVolume1
        # self.TickbidVolume2Array[-1] = tick.bidVolume2
        # self.TickbidVolume3Array[-1] = tick.bidVolume3
        # self.TickbidVolume4Array[-1] = tick.bidVolume4
        # self.TickbidVolume5Array[-1] = tick.bidVolume5

        self.TickaskPrice1Array[-1] = tick.askPrice1
        # self.TickaskPrice2Array[-1] = tick.askPrice2
        # self.TickaskPrice3Array[-1] = tick.askPrice3
        # self.TickaskPrice4Array[-1] = tick.askPrice4
        # self.TickaskPrice5Array[-1] = tick.askPrice5

        self.TickbidPrice1Array[-1] = tick.bidPrice1
        # self.TickbidPrice2Array[-1] = tick.bidPrice2
        # self.TickbidPrice3Array[-1] = tick.bidPrice3
        # self.TickbidPrice4Array[-1] = tick.bidPrice4
        # self.TickbidPrice5Array[-1] = tick.bidPrice5

    # ----------------------------------------------------------------------
    def updateTrade(self, tick):
        """更新tick Array"""
        self.tradeCount += 1

        # if not self.inited and self.count >= self.size:
        # if self.tradeCount >= self.size:

        self.inited = True

        self.TicklastPriceArray[0:self.size - 1] = self.TicklastPriceArray[1:self.size]
        self.TicklastVolumeArray[0:self.size - 1] = self.TicklastVolumeArray[1:self.size]
        # self.TickvolumeArray[0:self.size - 1] = self.TickvolumeArray[1:self.size]

        self.TicklastPriceArray[-1] = tick.lastPrice
        self.TicklastVolumeArray[-1] = tick.lastVolume
        # self.TickvolumeArray[-1] = tick.volume

    # ----------------------------------------------------------------------
    def updateinnerTrade(self, tick):
        self.innerCount += 1
        # print("self.innerCount:" + str(self.innerCount))
        # # if not self.inited and self.count >= self.size:
        # if self.innerCount >= self.size:
        # if not self.inited:
        self.inited = True

        # self.diffBuySellVolArray[0:self.size - 1] = self.diffBuySellVolArray[1:self.size]
        # self.diffBuySellCountArray[0:self.size - 1] = self.diffBuySellCountArray[1:self.size]

        if self.TickbidPrice1Array[-1] > 0: # 濾掉資料前幾筆尚未有080進來的狀況
            if tick.lastPrice >= self.TickaskPrice1Array[-1]:
                if tick.lastPrice > self.TickaskPrice1Array[-1]:
                    self.upOverPrice = 1
                self.innerBuyVolume += tick.lastVolume
                self.innerBuyCount += 1

            elif tick.lastPrice <= self.TickbidPrice1Array[-1]:
                if tick.lastPrice < self.TickbidPrice1Array[-1]:
                    self.downOverPrice = 1
                self.innerSellVolume += tick.lastVolume
                self.innerSellCount += 1

            # print("self.innerBuyVolume:" + str(self.innerBuyVolume))
            # print("self.innerBuyCount:" + str(self.innerBuyCount))
            # print("self.innerSellVolume:" + str(self.innerSellVolume))
            # print("self.innerSellCount:" + str(self.innerSellCount))

            # self.diffBuySellVolArray = self.diffBuySellVolArray + [0]
            # self.diffBuySellCountArray = self.diffBuySellCountArray + [0]

            self.diffBuySellVol = self.innerBuyVolume - self.innerSellVolume
            self.diffBuySellCount = self.innerBuyCount - self.innerSellCount


    # ----------------------------------------------------------------------
    def maBuySell(self):
        # self.macount += 1
        #
        # if self.innerCount >= self.size:

        self.diffBuySellVolArray[0:self.N1 - 1] = self.diffBuySellVolArray[1:self.N1]
        self.diffBuySellCountArray[0:self.N2 - 1] = self.diffBuySellCountArray[1:self.N2]
        self.diffBuySellVolArray[-1] = self.diffBuySellVol
        self.diffBuySellCountArray[-1] = self.diffBuySellCount

    # ----------------------------------------------------------------------
    def resetInnerTrade(self):

        self.innerCount = 0
        self.innerBuyVolume = 0
        self.innerBuyCount = 0
        self.innerSellVolume = 0
        self.innerSellCount = 0
        self.upOverPrice = 0
        self.downOverPrice = 0
        self.diffBuySellVol = 0
        self.diffBuySellCount = 0


    # ----------------------------------------------------------------------
    def VOIIndex(self):
        self.voiCount += 1

        if self.voiCount >= 2: # 第一筆080無法比較，因此濾掉
            if self.upOverPrice + self.downOverPrice >= 1: # 穿價
                if self.TickbidPrice1Array[-1] < self.TickbidPrice1Array[-2]:
                    diffBuyVol = 0
                else:
                    diffBuyVol = self.TickbidVolume1Array[-1]

                if self.TickaskPrice1Array[-1] > self.TickaskPrice1Array[-2]:
                    diffSellVol = 0
                else:
                    diffSellVol = self.TickaskVolume1Array[-1]
            else:
                if self.TickbidPrice1Array[-1] < self.TickbidPrice1Array[-2]:
                    diffBuyVol = 0
                elif self.TickbidPrice1Array[-1] == self.TickbidPrice1Array[-2]:
                    diffBuyVol = self.TickbidVolume1Array[-1] - self.TickbidVolume1Array[-2]
                else:
                    diffBuyVol = self.TickbidVolume1Array[-1]

                if self.TickaskPrice1Array[-1] > self.TickaskPrice1Array[-2]:
                    diffSellVol = 0
                elif self.TickaskPrice1Array[-1] == self.TickaskPrice1Array[-2]:
                    diffSellVol = self.TickaskVolume1Array[-1] - self.TickaskVolume1Array[-2]
                else:
                    diffSellVol = self.TickaskVolume1Array[-1]

            self.VOI = diffBuyVol - diffSellVol

    # ----------------------------------------------------------------------
    def CDFShift(self, scale1, scale2, scale3, weight1, weight2, weight3):
        if self.bookCount > max(self.N1, self.N2):
            CDF1 = (1 / (1 + math.exp(-(np.mean(self.diffBuySellVolArray) - 0) / scale1)) - 0.5)*2
            CDF2 = (1 / (1 + math.exp(-(np.mean(self.diffBuySellCountArray) - 0) / scale2)) - 0.5)*2
            CDF3 = (1 / (1 + math.exp(-(np.mean(self.VOI) - 0) / scale3)) - 0.5)*2

            shift = CDF1 *weight1 + CDF2 *weight2 + CDF3 *weight3
            # if shift >= 0.3:
            #     print("MAdiffBuySellVol:" + str(np.mean(self.diffBuySellVolArray)))
            #     print("MAdiffBuySellCount:" + str(np.mean(self.diffBuySellCountArray)))
            #     print("VOI:" + str(self.VOI))
            #     print("CDF1:" + str(CDF1))
            #     print("CDF2:" + str(CDF2))
            #     print("CDF3:" + str(CDF3))
                # print("shift:" + str(shift))

            return shift

    # ----------------------------------------------------------------------
    def askBidVolumeDif(self):

        return (self.TickaskVolume1Array.sum() - self.TickbidVolume1Array.sum())

    # ----------------------------------------------------------------------
    def askBidVolumeFiveDif(self):
        return (self.TickaskVolume1Array[-1] +
                self.TickaskVolume2Array[-1] +
                self.TickaskVolume3Array[-1] +
                self.TickaskVolume4Array[-1] +
                self.TickaskVolume5Array[-1] +
                - self.TickbidVolume1Array[-1]
                - self.TickbidVolume2Array[-1]
                - self.TickbidVolume3Array[-1]
                - self.TickbidVolume4Array[-1]
                - self.TickbidVolume5Array[-1])

########################################################################
class CtaSignal(object):
    """
    CTA策略信號，負責純粹的信號生成（目標倉位元），不參與具體交易管理
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.signalPos = 0  # 信號倉位元

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K線推送"""
        pass

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick推送"""
        pass

    # ----------------------------------------------------------------------
    def setSignalPos(self, pos):
        """設置信號倉位元"""
        self.signalPos = pos

    # ----------------------------------------------------------------------
    def getSignalPos(self):
        """獲取信號倉位元"""
        return self.signalPos







