# encoding: UTF-8

import time
from logging import INFO

from vnpy.trader.vtConstant import (EMPTY_STRING, EMPTY_UNICODE,
                                    EMPTY_FLOAT, EMPTY_INT)


########################################################################
class VtBaseData(object):
    """回呼函數推送資料的基礎類，其他資料類繼承於此"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.gatewayName = EMPTY_STRING  # Gateway名稱
        self.rawData = None  # 原始資料


########################################################################
class VtTickData(VtBaseData):
    """Tick行情資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTickData, self).__init__()
        # 代碼相關
        self.symbol = EMPTY_STRING  # 合約代碼
        self.exchange = EMPTY_STRING  # 交易所代碼
        self.vtSymbol = EMPTY_STRING  # 合約在vt系統中的唯一代碼，通常是 合約代碼.交易所代碼

        # 成交資料
        self.lastPrice = EMPTY_FLOAT  # 最新成交價
        self.lastVolume = EMPTY_INT  # 最新成交量
        self.volume = EMPTY_INT  # 今天總成交量

        self.time = EMPTY_STRING  # 時間 11:20:56.5
        self.date = EMPTY_STRING  # 日期 20151009
        self.datetime = None  # python的datetime時間對象

        # 五檔行情
        self.bidPrice1 = EMPTY_FLOAT
        self.bidPrice2 = EMPTY_FLOAT
        self.bidPrice3 = EMPTY_FLOAT
        self.bidPrice4 = EMPTY_FLOAT
        self.bidPrice5 = EMPTY_FLOAT

        self.askPrice1 = EMPTY_FLOAT
        self.askPrice2 = EMPTY_FLOAT
        self.askPrice3 = EMPTY_FLOAT
        self.askPrice4 = EMPTY_FLOAT
        self.askPrice5 = EMPTY_FLOAT

        self.bidVolume1 = EMPTY_INT
        self.bidVolume2 = EMPTY_INT
        self.bidVolume3 = EMPTY_INT
        self.bidVolume4 = EMPTY_INT
        self.bidVolume5 = EMPTY_INT

        self.askVolume1 = EMPTY_INT
        self.askVolume2 = EMPTY_INT
        self.askVolume3 = EMPTY_INT
        self.askVolume4 = EMPTY_INT
        self.askVolume5 = EMPTY_INT


########################################################################
class VtBarData(VtBaseData):
    """K線數據"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtBarData, self).__init__()

        self.vtSymbol = EMPTY_STRING  # vt系統代碼
        self.symbol = EMPTY_STRING  # 代碼
        self.exchange = EMPTY_STRING  # 交易所

        self.open = EMPTY_FLOAT  # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT

        self.date = EMPTY_STRING  # bar開始的時間，日期
        self.time = EMPTY_STRING  # 時間
        self.datetime = None  # python的datetime時間對象

        self.volume = EMPTY_INT  # 成交量
        self.openInterest = EMPTY_INT  # 持倉量


########################################################################
class VtTradeData(VtBaseData):
    """成交資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTradeData, self).__init__()

        # 代碼編號相關
        self.symbol = EMPTY_STRING  # 合約代碼
        self.exchange = EMPTY_STRING  # 交易所代碼
        self.vtSymbol = EMPTY_STRING  # 合約在vt系統中的唯一代碼，通常是 合約代碼.交易所代碼

        self.tradeID = EMPTY_STRING  # 成交編號
        self.vtTradeID = EMPTY_STRING  # 成交在vt系統中的唯一編號，通常是 Gateway名.成交編號

        self.orderID = EMPTY_STRING  # 訂單編號
        self.vtOrderID = EMPTY_STRING  # 訂單在vt系統中的唯一編號，通常是 Gateway名.訂單編號

        # 成交相關
        self.direction = EMPTY_UNICODE  # 成交方向
        self.offset = EMPTY_UNICODE  # 成交開平倉
        self.price = EMPTY_FLOAT  # 成交價格
        self.volume = EMPTY_INT  # 成交數量
        self.tradeTime = EMPTY_STRING  # 成交時間


########################################################################
class VtOrderData(VtBaseData):
    """訂單資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtOrderData, self).__init__()

        # 代碼編號相關
        self.symbol = EMPTY_STRING  # 合約代碼
        self.exchange = EMPTY_STRING  # 交易所代碼
        self.vtSymbol = EMPTY_STRING  # 合約在vt系統中的唯一代碼，通常是 合約代碼.交易所代碼

        self.orderID = EMPTY_STRING  # 訂單編號
        self.vtOrderID = EMPTY_STRING  # 訂單在vt系統中的唯一編號，通常是 Gateway名.訂單編號

        # 報單相關
        self.direction = EMPTY_UNICODE  # 報單方向
        self.offset = EMPTY_UNICODE  # 報單開平倉
        self.price = EMPTY_FLOAT  # 報單價格
        self.totalVolume = EMPTY_INT  # 報單總數量
        self.tradedVolume = EMPTY_INT  # 報單成交數量
        self.status = EMPTY_UNICODE  # 報單狀態

        self.orderTime = EMPTY_STRING  # 發單時間
        self.cancelTime = EMPTY_STRING  # 撤單時間

        # CTP/LTS相關
        self.frontID = EMPTY_INT  # 前置機編號
        self.sessionID = EMPTY_INT  # 連接編號

        # 研究相關
        self.bookNumber = EMPTY_INT
########################################################################
class VtPositionData(VtBaseData):
    """持倉數據類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtPositionData, self).__init__()

        # 代碼編號相關
        self.symbol = EMPTY_STRING  # 合約代碼
        self.exchange = EMPTY_STRING  # 交易所代碼
        self.vtSymbol = EMPTY_STRING  # 合約在vt系統中的唯一代碼，合約代碼.交易所代碼

        # 持倉相關
        self.direction = EMPTY_STRING  # 持倉方向
        self.position = EMPTY_INT  # 持倉量
        self.frozen = EMPTY_INT  # 凍結數量
        self.price = EMPTY_FLOAT  # 持倉均價
        self.vtPositionName = EMPTY_STRING  # 持倉在vt系統中的唯一代碼，通常是vtSymbol.方向
        self.ydPosition = EMPTY_INT  # 昨持倉
        self.positionProfit = EMPTY_FLOAT  # 持倉盈虧


########################################################################
class VtAccountData(VtBaseData):
    """帳戶資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtAccountData, self).__init__()

        # 帳號代碼相關
        self.accountID = EMPTY_STRING  # 帳戶代碼
        self.vtAccountID = EMPTY_STRING  # 帳戶在vt中的唯一代碼，通常是 Gateway名.帳戶代碼

        # 數值相關
        self.preBalance = EMPTY_FLOAT  # 昨日帳戶結算淨值
        self.balance = EMPTY_FLOAT  # 帳戶淨值
        self.available = EMPTY_FLOAT  # 可用資金
        self.commission = EMPTY_FLOAT  # 今日手續費
        self.margin = EMPTY_FLOAT  # 保證金佔用
        self.closeProfit = EMPTY_FLOAT  # 平倉盈虧
        self.positionProfit = EMPTY_FLOAT  # 持倉盈虧


########################################################################
class VtErrorData(VtBaseData):
    """錯誤資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtErrorData, self).__init__()

        self.errorID = EMPTY_STRING  # 錯誤代碼
        self.errorMsg = EMPTY_UNICODE  # 錯誤資訊
        self.additionalInfo = EMPTY_UNICODE  # 補充資訊

        self.errorTime = time.strftime('%X', time.localtime())  # 錯誤生成時間


########################################################################
class VtLogData(VtBaseData):
    """日誌資料類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtLogData, self).__init__()

        self.logTime = time.strftime('%X', time.localtime())  # 日誌生成時間
        self.logContent = EMPTY_UNICODE  # 日誌資訊
        self.logLevel = INFO  # 日誌級別


########################################################################
class VtContractData(VtBaseData):
    """合約詳細資訊類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtContractData, self).__init__()

        self.symbol = EMPTY_STRING  # 代碼
        self.exchange = EMPTY_STRING  # 交易所代碼
        self.vtSymbol = EMPTY_STRING  # 合約在vt系統中的唯一代碼，通常是 合約代碼.交易所代碼
        self.name = EMPTY_UNICODE  # 合約中文名

        self.productClass = EMPTY_UNICODE  # 合約類型
        self.size = EMPTY_INT  # 合約大小
        self.priceTick = EMPTY_FLOAT  # 合約最小價格TICK

        # 期權相關
        self.strikePrice = EMPTY_FLOAT  # 期權行權價
        self.underlyingSymbol = EMPTY_STRING  # 標的物合約代碼
        self.optionType = EMPTY_UNICODE  # 期權類型
        self.expiryDate = EMPTY_STRING  # 到期日


########################################################################
class VtSubscribeReq(object):
    """訂閱行情時傳入的對象類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代碼
        self.exchange = EMPTY_STRING  # 交易所

        # 以下為IB相關
        self.productClass = EMPTY_UNICODE  # 合約類型
        self.currency = EMPTY_STRING  # 合約貨幣
        self.expiry = EMPTY_STRING  # 到期日
        self.strikePrice = EMPTY_FLOAT  # 行權價
        self.optionType = EMPTY_UNICODE  # 期權類型


########################################################################
class VtOrderReq(object):
    """發單時傳入的對象類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代碼
        self.exchange = EMPTY_STRING  # 交易所
        self.vtSymbol = EMPTY_STRING  # VT合約代碼
        self.price = EMPTY_FLOAT  # 價格
        self.volume = EMPTY_INT  # 數量

        self.priceType = EMPTY_STRING  # 價格類型
        self.direction = EMPTY_STRING  # 買賣
        self.offset = EMPTY_STRING  # 開平

        # 以下為IB相關
        self.productClass = EMPTY_UNICODE  # 合約類型
        self.currency = EMPTY_STRING  # 合約貨幣
        self.expiry = EMPTY_STRING  # 到期日
        self.strikePrice = EMPTY_FLOAT  # 行權價
        self.optionType = EMPTY_UNICODE  # 期權類型
        self.lastTradeDateOrContractMonth = EMPTY_STRING  # 合約月,IB專用
        self.multiplier = EMPTY_STRING  # 乘數,IB專用


########################################################################
class VtCancelOrderReq(object):
    """撤單時傳入的對象類"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代碼
        self.exchange = EMPTY_STRING  # 交易所
        self.vtSymbol = EMPTY_STRING  # VT合約代碼

        # 以下欄位主要和CTP、LTS類介面相關
        self.orderID = EMPTY_STRING  # 報單號
        self.frontID = EMPTY_STRING  # 前置機號
        self.sessionID = EMPTY_STRING  # 會話號


########################################################################
class VtSingleton(type):
    """
    單例，應用方式:靜態變數 __metaclass__ = Singleton
    """

    _instances = {}

    # ----------------------------------------------------------------------
    def __call__(cls, *args, **kwargs):
        """調用"""
        if cls not in cls._instances:
            cls._instances[cls] = super(VtSingleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]




