# encoding: UTF-8

"""
本模块中主要包含：
1. 将MultiCharts导出的历史数据载入到MongoDB中用的函数
2. 将通达信导出的历史数据载入到MongoDB中的函数
3. 将交易开拓者导出的历史数据载入到MongoDB中的函数
4. 将OKEX下载的历史数据载入到MongoDB中的函数
"""
from __future__ import print_function

import csv
from datetime import datetime, timedelta
from time import time
from struct import unpack

import pymongo

from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData, VtTickData
from .ctaBase import SETTING_DB_NAME, TICK_DB_NAME, MINUTE_DB_NAME, DAILY_DB_NAME


#----------------------------------------------------------------------
def downloadEquityDailyBarts(self, symbol):
    """
    下载股票的日行情，symbol是股票代码
    """
    print(u'开始下载%s日行情' %symbol)
    
    # 查询数据库中已有数据的最后日期
    cl = self.dbClient[DAILY_DB_NAME][symbol]
    cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
    if cx.count():
        last = cx[0]
    else:
        last = ''
    # 开始下载数据
    import tushare as ts
    
    if last:
        start = last['date'][:4]+'-'+last['date'][4:6]+'-'+last['date'][6:]
        
    data = ts.get_k_data(symbol,start)
    
    if not data.empty:
        # 创建datetime索引
        self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                            unique=True)                
        
        for index, d in data.iterrows():
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            try:
                bar.open = d.get('open')
                bar.high = d.get('high')
                bar.low = d.get('low')
                bar.close = d.get('close')
                bar.date = d.get('date').replace('-', '')
                bar.time = ''
                bar.datetime = datetime.strptime(bar.date, '%Y%m%d')
                bar.volume = d.get('volume')
            except KeyError:
                print(d)
            
            flt = {'datetime': bar.datetime}
            self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
        
        print(u'%s下载完成' %symbol)
    else:
        print(u'找不到合约%s' %symbol)

#----------------------------------------------------------------------
def loadMcCsv(fileName, dbName, symbol):
    """将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))
    
    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort']) 
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   
    
    # 读取数据和插入到数据库
    with open(fileName, 'r') as f:
        reader = csv.DictReader(f)
        for d in reader:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            bar.open = float(d['Open'])
            bar.high = float(d['High'])
            bar.low = float(d['Low'])
            bar.close = float(d['Close'])
            bar.date = datetime.strptime(d['Date'], '%Y-%m-%d').strftime('%Y%m%d')
            bar.time = d['Time']
            bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
            bar.volume = d['TotalVolume']
    
            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
            print(bar.date, bar.time)
    
    print(u'插入完毕，耗时：%s' % (time()-start))

#----------------------------------------------------------------------
def loadTickCsv(fileName, dbName, symbol):
    """将Tick导出的csv格式的历史数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' % (fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    with open(fileName, 'r') as f:
        reader = csv.DictReader(f)
        for d in reader:
            Tick = VtTickData()
            Tick.vtSymbol = symbol
            Tick.symbol = symbol

            # Tick.open = float(d['Open'])
            # Tick.high = float(d['High'])
            # Tick.low = float(d['Low'])
            # Tick.close = float(d['Close'])

            Tick.lastPrice = float(d['Dp'])
            Tick.lastVolume = int(d['Dv'])

            Tick.askPrice1 = float(d['Sp1'])
            Tick.askPrice2 = float(d['Sp2'])
            Tick.askPrice3 = float(d['Sp3'])
            Tick.askPrice4 = float(d['Sp4'])
            Tick.askPrice5 = float(d['Sp5'])

            Tick.askVolume1 = int(d['Sv1'])
            Tick.askVolume2 = int(d['Sv2'])
            Tick.askVolume3 = int(d['Sv3'])
            Tick.askVolume4 = int(d['Sv4'])
            Tick.askVolume5 = int(d['Sv5'])

            Tick.bidPrice1 = float(d['Bp1'])
            Tick.bidPrice2 = float(d['Bp2'])
            Tick.bidPrice3 = float(d['Bp3'])
            Tick.bidPrice4 = float(d['Bp4'])
            Tick.bidPrice5 = float(d['Bp5'])

            Tick.bidVolume1 = int(d['Bv1'])
            Tick.bidVolume2 = int(d['Bv2'])
            Tick.bidVolume3 = int(d['Bv3'])
            Tick.bidVolume4 = int(d['Bv4'])
            Tick.bidVolume5 = int(d['Bv5'])


            Tick.date = datetime.strptime(d['Date'], '%Y/%m/%d').strftime('%Y%m%d')
            Tick.time = d['Time']
            Tick.datetime = datetime.strptime(Tick.date + ' ' + Tick.time, '%Y%m%d %H%M%S%f')
            Tick.volume = d['Tvolume']

            flt = {'datetime': Tick.datetime}
            collection.update_one(flt, {'$set': Tick.__dict__}, upsert=True)
            print(Tick.date, Tick.time)

    print(u'插入完毕，耗时：%s' % (time() - start))


#----------------------------------------------------------------------
def loadTbCsv(fileName, dbName, symbol):
    """将TradeBlazer导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))
    
    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   
    
    # 读取数据和插入到数据库
    reader = csv.reader(file(fileName, 'r'))
    for d in reader:
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = float(d[1])
        bar.high = float(d[2])
        bar.low = float(d[3])
        bar.close = float(d[4])
        bar.date = datetime.strptime(d[0].split(' ')[0], '%Y/%m/%d').strftime('%Y%m%d')
        bar.time = d[0].split(' ')[1]+":00"
        bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        bar.volume = d[5]
        bar.openInterest = d[6]

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
        print(bar.date, bar.time)
    
    print(u'插入完毕，耗时：%s' % (time()-start))
    
 #----------------------------------------------------------------------
def loadTbPlusCsv(fileName, dbName, symbol):
    """将TB极速版导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol)) 

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)      

    # 读取数据和插入到数据库
    reader = csv.reader(file(fileName, 'r'))
    for d in reader:
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = float(d[2])
        bar.high = float(d[3])
        bar.low = float(d[4])
        bar.close = float(d[5])
        bar.date = str(d[0])
        
        tempstr=str(round(float(d[1])*10000)).split(".")[0].zfill(4)
        bar.time = tempstr[:2]+":"+tempstr[2:4]+":00"
        
        bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        bar.volume = d[6]
        bar.openInterest = d[7]
        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
        print(bar.date, bar.time)    

    print(u'插入完毕，耗时：%s' % (time()-start))

#----------------------------------------------------------------------
"""
使用中银国际证券通达信导出的1分钟K线数据为模版
格式：csv
样例：

时间                    开盘价   最高价  最低价   收盘价  成交量
2017/09/28-10:52	    3457	 3459	 3456	  3458	  466

注意事项：导出csv后手工删除表头和表尾
"""
def loadTdxCsv(fileName, dbName, symbol):
    """将通达信导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    start = time()
    date_correct = ""
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))
    
    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   
    
    # 读取数据和插入到数据库
    reader = csv.reader(file(fileName, 'r'))
    for d in reader:
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = float(d[1])
        bar.high = float(d[2])
        bar.low = float(d[3])
        bar.close = float(d[4])
        #通达信的夜盘时间按照新的一天计算，此处将其按照当天日期统计，方便后续查阅
        date_temp,time_temp = d[0].strip(' ').replace('\xef\xbb\xbf','').split('-',1)
        if time_temp == '15:00':
            date_correct = date_temp
        if time_temp[:2] == "21" or time_temp[:2] == "22" or time_temp[:2] == "23":
            date_temp = date_correct
            
        bar.date = datetime.strptime(date_temp, '%Y/%m/%d').strftime('%Y%m%d')
        bar.time = time_temp[:2]+':'+time_temp[3:5]+':00'
        bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        bar.volume = d[5]

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
    
    print(u'插入完毕，耗时：%s' % (time()-start))

#----------------------------------------------------------------------
"""
使用中银国际证券通达信导出的1分钟K线数据为模版
格式：lc1

注意事项：
"""   
def loadTdxLc1(fileName, dbName, symbol):
    """将通达信导出的lc1格式的历史分钟数据插入到Mongo数据库中"""
    start = time()

    print(u'开始读取通达信Lc1文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))
    
    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)  

    #读取二进制文件
    ofile=open(fileName,'rb')
    buf=ofile.read()
    ofile.close()
    
    num=len(buf)
    no=num/32
    b=0
    e=32  
    dl = []
    for i in xrange(no):
        a=unpack('hhfffffii',buf[b:e])
        b=b+32
        e=e+32
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = a[2]
        bar.high = a[3]
        bar.low = a[4]
        bar.close = a[5]
        bar.date = str(int(a[0]/2048)+2004)+str(int(a[0]%2048/100)).zfill(2)+str(a[0]%2048%100).zfill(2)
        bar.time = str(int(a[1]/60)).zfill(2)+':'+str(a[1]%60).zfill(2)+':00'
        bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        bar.volume = a[7]

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)
    
    print(u'插入完毕，耗时：%s' % (time()-start))

#----------------------------------------------------------------------
def loadOKEXCsv(fileName, dbName, symbol):
    """将OKEX导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    reader = csv.reader(open(fileName,"r"))
    for d in reader:
        if len(d[1]) > 10:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol

            bar.datetime = datetime.strptime(d[1], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y%m%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')

            bar.open = float(d[2])
            bar.high = float(d[3])
            bar.low = float(d[4])
            bar.close = float(d[5])

            bar.volume = float(d[6])
            bar.tobtcvolume = float(d[7])

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)
            print('%s \t %s' % (bar.date, bar.time))

    print(u'插入完毕，耗时：%s' % (time()-start))
    
