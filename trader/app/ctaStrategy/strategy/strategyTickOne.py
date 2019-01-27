# encoding: UTF-8


from __future__ import division
from vnpy.trader.vtGateway import *
from datetime import datetime, time
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager,
                                                     TickArrayManager)

########################################################################
class TickOneStrategy(CtaTemplate):
    """基於Tick的交易策略"""
    className = 'TickOneStrategy'
    author = u'BillyZhang'

    # 策略參數
    fixedSize = 1 # 下單數量
    Ticksize = 1  # 緩存大小
    initDays = 0

    DAY_START = time(8, 45)  # 日盤啟動和停止時間
    DAY_END = time(13, 45)
    NIGHT_START = time(15, 00)  # 夜盤啟動和停止時間
    NIGHT_END = time(5, 00)

    # 策略變數
    posPrice = 0  # 持倉價格
    pos = 0       # 持倉數量


    # 參數列表，保存了參數的名稱
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'initDays',
                 'Ticksize',
                 'fixedSize'
                 ]

    # 變數清單，保存了變數的名稱
    varList = ['inited',
               'trading',
               'pos',
               'posPrice'
               ]

    # 同步清單，保存了需要保存到資料庫的變數名稱
    syncList = ['pos',
                'posPrice',
                'intraTradeHigh',
                'intraTradeLow']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TickOneStrategy, self).__init__(ctaEngine, setting)

        #創建Array佇列
        self.tickArray = TickArrayManager(self.Ticksize)

    # ----------------------------------------------------------------------
    def onminBarClose(self, bar):
        """"""

        # ----------------------------------------------------------------------

    def onInit(self):
        """初始化策略（必須由用戶繼承實現）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        #tick級別交易，不需要過往歷史資料
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """啟動策略（必須由用戶繼承實現）"""
        self.writeCtaLog(u'%s策略啟動' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必須由用戶繼承實現）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):

        """收到行情TICK推送（必須由用戶繼承實現）"""
        # currentTime = datetime.now().time()

        # if ((currentTime >= self.DAY_START and currentTime <= self.DAY_END) or
        #     (currentTime >= self.NIGHT_START and currentTime <= self.NIGHT_END)):
        TA = self.tickArray
        TA.updateTrade(tick)

        if not TA.inited:
            return
        # if self.pos == 0:
        if self.pos > 5:
            if TA.askBidVolumeFiveDif() > 0:  # 賣5檔量大於買5檔量
                self.short(tick.lastPrice, self.fixedSize, False)

        elif self.pos < -5:
            if TA.askBidVolumeFiveDif() < 0:
                self.buy(tick.lastPrice, self.fixedSize, False)
        else:
            if TA.askBidVolumeFiveDif() > 0:  # 賣5檔量大於買5檔量
                self.short(tick.lastPrice, self.fixedSize, False)
            elif TA.askBidVolumeFiveDif() < 0:
                self.buy(tick.lastPrice, self.fixedSize, False)


    # ----------------------------------------------------------------------

    def onBook(self, tick):
        TA = self.tickArray
        TA.updateBook(tick)


    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必須由用戶繼承實現）"""


    # ----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到X分鐘K線"""



    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委託變化推送（必須由用戶繼承實現）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):

        self.posPrice = trade.price
        # 同步資料到資料庫
        self.saveSyncData()
        # 發出狀態更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止單推送"""
        pass

