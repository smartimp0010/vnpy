# encoding: UTF-8

"""
展示如何執行策略回測。
"""
from __future__ import division
import pandas as pd

from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, TICK_DB_NAME

if __name__ == '__main__':
    from vnpy.trader.app.ctaStrategy.strategy.strategyOI import OIStrategy

    # plotting
    turn_on_plot = False

    # Sql (整合)
    data_from_sql = False
    data_from_csv = True

    winningRateList = []
    pnlList = []


    # 創建回測引擎
    engine = BacktestingEngine()

    # 設置引擎的回測模式為K線
    engine.setBacktestingMode(engine.HYBER_MODE)

    # 設置成交模擬器
    engine.setSimulatingMode(engine.EASY_MODE)

    # 設置成交標示方式
    engine.setPlotMode(engine.ORDER_MODE)

    # 設置print detail
    engine.setPrintDetailMode(engine.Simple_Mode)

    # 設置回測用的數據起始日期
    engine.setStartDate('20180101')

    # 設置產品相關參數
    engine.setSlippage(0)  # 股指1跳
    engine.setRate(0)  # 萬0.3
    engine.setSize(200)  # 股指合約大小
    engine.setPriceTick(1)  # 股指最小價格變動

    # 設置使用的歷史資料庫
    engine.setDatabase(TICK_DB_NAME, 'TXF01')

    # 讀取資料
    if data_from_sql:
        engine.loadHistoryDataSql()
    elif data_from_csv:
        engine.loadHistoryDataCsv()
    else:
        engine.loadHistoryData()

    # 在引擎中創建策略物件
    d = {}
    engine.initStrategy(OIStrategy, d)
    for i in range(4, 5, 1):
        for j in range(1, 2, 1):
            engine.init()
            engine.strategy.init()
            engine.strategy.shiftThreshold = i / 10
            engine.strategy.lagBook = j

            # 開始跑回測
            if data_from_sql:
                engine.runBacktestingSql()
            else:
                engine.runBacktesting()

            # 顯示回測結果
            engine.showBacktestingResult()

            winningRateList.append([i/10, j, engine.strategy.bingo/engine.strategy.round])
            pnlList.append([i/10, j, engine.d_result['capital']])

            if turn_on_plot:
                engine.plotResult()
                engine.plotResultWithTime()


    df1 = pd.DataFrame(winningRateList)
    df1.columns = ['shiftThreshold', 'lagBook', 'winningRate']
    df2 = pd.DataFrame(pnlList)
    df2.columns = ['shiftThreshold', 'lagBook', 'pnl']
    df1.to_csv('winningRate.csv', index = False, encoding='gbk')
    df2.to_csv('pnl.csv', index = False, encoding='gbk')



