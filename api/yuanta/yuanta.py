# -*- coding: utf-8 -*-

import wx, time
import wx.lib.anchors as anchors
from ctypes import byref, POINTER, windll
from comtypes import IUnknown, GUID
from comtypes.client import GetModule,  GetBestInterface, GetEvents

user32 = windll.user32
atl = windll.atl

import queue as queue
q = queue.Queue ()

class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args: # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False

class Job:
    STOCK_LOGIN = 1
    STOCK_WATCH = 2
    def __init__ (self, do_type, do_value = 0):
        self.do_type = do_type
        self.do_value = do_value
        q.put (self)

def DoJob(Bot, x):
    for case in switch(x.do_type):
        if case(Job.STOCK_LOGIN):
            Bot.login ()
            break
        if case(Job.STOCK_WATCH):
            Bot.watch (x.do_value)
            break

class YuantaQuoteEvents(object):
    def __init__(self, parent):
        self.parent = parent

    def OnMktStatusChange (self, this, Status, Msg, ReqType):
        print ('OnMktStatusChange {},{},{}'.format (ReqType, Msg, Status))
        if Status == 2:
            Job(Job.STOCK_WATCH, ReqType)

    def OnRegError(self, this, symbol, updmode, ErrCode, ReqType):
        print ('OnRegError {},{},{},{}'.format (ReqType, ErrCode, symbol, updmode))

    def OnGetMktData(self, this, PriType, symbol, Qty, Pri, ReqType):
        print ('OnGetMktData')

    def OnGetMktQuote(self, this, symbol, DisClosure, Duration, ReqType):
        print ('OnGetMktQuote')

    def OnGetMktAll(self, this, symbol, RefPri, OpenPri, HighPri, LowPri, UpPri, DnPri, MatchTime, MatchPri, MatchQty, TolMatchQty,
        BestBuyQty, BestBuyPri, BestSellQty,BestSellPri, FDBPri, FDBQty, FDSPri, FDSQty, ReqType):
        #print ('OnGetMktAll\n')
        print ('{} {} c:{} o:{} h:{} l:{} v:{}'.format (ReqType, MatchTime,  MatchPri, OpenPri, HighPri, LowPri, TolMatchQty))

    def OnGetDelayClose(self, this, symbol, DelayClose, ReqType):
        print ('OnGetDelayClose')

    def OnGetBreakResume(self, this, symbol, BreakTime, ResumeTime, ReqType):
        print ('OnGetBreakResume')

    def OnGetTradeStatus(self, this, symbol, TradeStatus, ReqType):
        print ('OnGetTradeStatus')

    def OnTickRegError(self, this, strSymbol, lMode, lErrCode, ReqType):
        print ('OnTickRegError')

    def OnGetTickData(self, this, strSymbol, strTickSn, strMatchTime, strBuyPri, strSellPri, strMatchPri, strMatchQty, strTolMatQty,
        strMatchAmt, strTolMatAmt, ReqType):
        print ('OnGetTickData')

    def OnTickRangeDataError(self, this, strSymbol, lErrCode, ReqType):
        print ('OnTickRangeDataError')

    def OnGetTickRangeData(self, this, strSymbol, strStartTime, strEndTime, strTolMatQty, strTolMatAmt, ReqType):
        print ('OnGetTickRangeData')

    def OnGetTimePack(self, this, strTradeType, strTime, ReqType):
        print ('OnGetTimePack {},{}'.format (strTradeType, strTime))

    def OnGetDelayOpen(self, this, symbol, DelayOpen, ReqType):
        print ('OnGetDelayOpen')

    def OnGetFutStatus(self, this, symbol, FunctionCode, BreakTime, StartTime, ReopenTime, ReqType):
        print ('OnGetFutStatus')

    def OnGetLimitChange(self, this, symbol, FunctionCode, StatusTime, Level, ExpandType, ReqType):
        print ('OnGetLimitChange')

class YuantaQuoteWapper:
    def __init__(self, handle, bot):
        self.bot = bot

        Iwindow = POINTER(IUnknown)()
        Icontrol = POINTER(IUnknown)()
        Ievent = POINTER(IUnknown)()

        res = atl.AtlAxCreateControlEx("YUANTAQUOTE.YuantaQuoteCtrl.1", handle, None,
                                    byref(Iwindow),
                                    byref(Icontrol),
                                    byref(GUID()),
                                    Ievent)


        self.YuantaQuote = GetBestInterface(Icontrol)
        self.YuantaQuoteEvents = YuantaQuoteEvents(self)
        self.YuantaQuoteEventsConnect = GetEvents(self.YuantaQuote, self.YuantaQuoteEvents)

class StockBot:
    def __init__(self, botuid, account, pwd):
        self.Yuanta = YuantaQuoteWapper(botuid, self)
        self.Account = account
        self.Pwd = pwd

    def login (self):
        #T port 80/443 , T+1 port 82/442 ,  reqType=1 T盤 , reqType=2  T+1盤
        self.Yuanta.YuantaQuote.SetMktLogon(self.Account, self.Pwd, '203.66.93.84', '80', 1, 0)
        self.Yuanta.YuantaQuote.SetMktLogon(self.Account, self.Pwd, '203.66.93.84', '82', 2, 1)
        print ('login')

    def watch (self, ret_type):
        ret = self.Yuanta.YuantaQuote.AddMktReg ('1101', "4", ret_type, 0)
        print ("AddMktReg {}".format (ret))

class MyApp(wx.App):
    def MainLoop(self, run_func):

        # Create an event loop and make it active.  If you are
        # only going to temporarily have a nested event loop then
        # you should get a reference to the old one and set it as
        # the active event loop when you are done with this one...
        evtloop = wx.GUIEventLoop()
        old = wx.EventLoop.GetActive()
        wx.EventLoop.SetActive(evtloop)

        # This outer loop determines when to exit the application,
        # for this example we let the main frame reset this flag
        # when it closes.
        while self.keepGoing:
            # At this point in the outer loop you could do
            # whatever you implemented your own MainLoop for.  It
            # should be quick and non-blocking, otherwise your GUI
            # will freeze.

            # call_your_code_here()
            run_func ()
            while not q.empty():
                next_job = q.get()
                DoJob (Bot, next_job)

            # This inner loop will process any GUI events
            # until there are no more waiting.
            while evtloop.Pending():
                evtloop.Dispatch()

            # Send idle events to idle handlers.  You may want to
            # throttle this back a bit somehow so there is not too
            # much CPU time spent in the idle handlers.  For this
            # example, I'll just snooze a little...
            time.sleep(0.10)
            evtloop.ProcessIdle()

        wx.EventLoop.SetActive(old)

    def OnInit(self):
        self.keepGoing = True
        return True

def run_job():
    while not q.empty():
        next_job = q.get()
        DoJob (Bot, next_job)

if __name__ == "__main__":
    app=MyApp()
    frame = wx.Frame(None,wx.ID_ANY,"Hello")
    frame.Show (False)
    Bot = StockBot(frame.Handle, 'L223805612', 'talented0020')
    Job(Job.STOCK_LOGIN)
    app.MainLoop (run_job)
