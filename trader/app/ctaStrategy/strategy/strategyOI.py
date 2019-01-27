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
# class InputAttributes:
#
#     @classmethod
#     def LoadAttributesFromFile(cls):
#         # TODO
#         pass
#
# InputAttributes.LoadAttributesFromFile()


class OIStrategy(CtaTemplate):
    """基於Tick的交易策略"""
    className = 'OIStrategy'

    # 策略參數
    #InputAttribute.fixedSize
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
    lagBook = 0
    round = 0
    bingo = 0
    # DAY_START = time(8, 45)  # 日盤啟動和停止時間
    # DAY_END = time(13, 45)
    # NIGHT_START = time(15, 00)  # 夜盤啟動和停止時間
    # NIGHT_END = time(5, 00)

    # 策略變數
    posPrice = 0  # 持倉價格
    pos = 0       # 持倉數量

    offSetList = []
    shift = None

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
        super(OIStrategy, self).__init__(ctaEngine, setting)

        # 創建Array佇列
        self.tickArray = TickArrayManager(self.Ticksize, self.N1, self.N2)

        # self.shiftThreshold = None
        # self.lagBook = None
    # ----------------------------------------------------------------------
    def init(self):

        self.offSetList = []
        self.onbook = 0
        self.shift = None
        self.round = 0
        self.bingo = 0
        self.posPrice = 0
        self.pos = 0
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
        TA.updaeinnerTrade(tick)

    # ----------------------------------------------------------------------
    def onBook(self, tick):

        self.onbook += 1
        # print("onBook:" + str(self.onbook))
        # self.LoadCalculator(TickArrayManager)
        TA = self.tickArray
        # self.UpdateBookForAllCalculator()
        TA.updateBook(tick)
        TA.maBuySell()
        TA.VOIIndex()

        if not TA.inited:
            return

        self.shift = TA.CDFShift(self.Sigma1, self.Sigma2, self.Sigma3, self.Weight1, self.Weight2, self.Weight3)
        # if self.pos > 0:
        #     print("pos:" + str(self.pos))

        if self.shift:
            if self.shift > self.shiftThreshold:
                # print(self.shift)
                # print("shiftthreshold:" + str(self.shiftThreshold))
                # print("shift:" + str(self.shift))

                self.buy(tick.bidPrice1 + self.shift, self.fixedSize, False)
                self.offSetList.append([self.onbook, 0, tick.bidPrice1 + self.shift])
            elif self.shift < -self.shiftThreshold:
                # print("shift:" + str(self.shift))

                self.short(tick.askPrice1 + self.shift, self.fixedSize, False)
                self.offSetList.append([self.onbook, 1, tick.askPrice1 + self.shift])
        for i in range(len(self.offSetList)):
            if self.offSetList[i][0] + self.lagBook == self.onbook:
                self.round += 1
                if self.offSetList[i][1] == 0:
                    # print("offSet tick.bidPrice1:" + str(tick.bidPrice1))
                    self.short(tick.bidPrice1, self.fixedSize, False)
                    if self.offSetList[i][2] <= tick.bidPrice1:
                        self.bingo += 1
                else:
                    # print("offSet tick.askPrice1:" + str(tick.askPrice1))
                    self.buy(tick.askPrice1, self.fixedSize, False)
                    if self.offSetList[i][2] >= tick.askPrice1:
                        self.bingo += 1

                    # self.offSetList.remove(self.offSetList[i])
        TA.resetInnerTrade()
        # print("---------------------------------------------")

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

