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
class VOIStrategy(CtaTemplate):
    """基於Tick的交易策略"""
    className = 'VOIStrategy'

    # 策略參數
    fixedSize = 1 # 下單數量
    Ticksize = 3  # 緩存大小
    initDays = 0
    onbook = 0
    N1 = 4
    N2 = 1
    Sigma1 = 15
    Sigma2 = 10
    Sigma3 = 30
    Weight1 = 0.3
    Weight2 = 0.3
    Weight3 = 0.4
    SWide = 0
    shiftThreshold = 0

    # DAY_START = time(8, 45)  # 日盤啟動和停止時間
    # DAY_END = time(13, 45)
    # NIGHT_START = time(15, 00)  # 夜盤啟動和停止時間
    # NIGHT_END = time(5, 00)

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
                 'fixedSize',
                 'N1',
                 'N2',
                 'Sigma1',
                 'Sigma2',
                 'Sigma3',
                 'Weight1',
                 'Weight2',
                 'Weight3',
                 'SWide'
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
        super(VOIStrategy, self).__init__(ctaEngine, setting)

        # 創建Array佇列
        self.tickArray = TickArrayManager(self.Ticksize, self.N1, self.N2)

    # ----------------------------------------------------------------------
    def onminBarClose(self, bar):
        """"""

        # ----------------------------------------------------------------------

    def onInit(self):
        """初始化策略（必須由用戶繼承實現）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        # tick級別交易，不需要過往歷史資料
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

        TA = self.tickArray
        TA.updateTrade(tick)
        TA.updateinnerTrade(tick)

    # ----------------------------------------------------------------------
    def onBook(self, tick):
        self.onbook += 1
        print("onBook:" + str(self.onbook ))
        TA = self.tickArray
        TA.updateBook(tick)
        TA.maBuySell()
        TA.VOIIndex()

        if not TA.inited:
            return

        shift = TA.CDFShift(self.Sigma1, self.Sigma2, self.Sigma3, self.Weight1, self.Weight2, self.Weight3)
        print("shift:" + str(shift))

        if shift:
            if self.pos <= 0 and shift > self.shiftThreshold:
                self.buy(tick.bidPrice1 + shift, self.fixedSize, False)
            elif self.pos >= 0 and shift < -self.shiftThreshold:
                self.short(tick.askPrice1 + shift, self.fixedSize, False)
        print("self.pos:" + str(self.pos))
        TA.resetInnerTrade()
        print("---------------------------------------------")
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

