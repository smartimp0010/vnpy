# -*- coding: utf-8 -*-

import wx, time
from win32api import *
from win32gui import *
from win32con import *
from ctypes import byref, POINTER, windll
from comtypes import IUnknown, GUID
from comtypes.client import GetModule, GetBestInterface, GetEvents

user32 = windll.user32
atl = windll.atl

# GetModule('shdocvw.dll')  # IWebBrowser2 and etc.
# from comtypes.gen import SHDocVw
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
# Hosting Window Creation
################################################################################
hInst = GetModuleHandle(None)

wc = WNDCLASS()
wc.hInstance = hInst
wc.lpszClassName = "AtlAxWinContainer"
wc.style = CS_VREDRAW | CS_HREDRAW;
wc.hCursor = LoadCursor(0, IDC_ARROW)
wc.hbrBackground = COLOR_WINDOW
wc.lpfnWndProc = {}
classAtom = RegisterClass(wc)

hwnd = CreateWindow(wc.lpszClassName,
                    wc.lpszClassName,
                    WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                    CW_USEDEFAULT,
                    CW_USEDEFAULT,
                    CW_USEDEFAULT,
                    CW_USEDEFAULT,
                    0, 0, hInst, None)
ShowWindow(hwnd, SW_SHOW)
UpdateWindow(hwnd)

# ActiveX Control Hosting
app=MyApp()
frame = wx.Frame(None,wx.ID_ANY,"Hello")
################################################################################
atl.AtlAxWinInit()
progID = 'YUANTAQUOTE.YuantaQuoteCtrl.1'
# hwnd2 = user32.CreateWindowExA(0, "AtlAxWin", progID,
#                                WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
#                                0, 0, 0, 0, hwnd, None, hInst, 0)

Iwindow = POINTER(IUnknown)()
Icontrol = POINTER(IUnknown)()
Ievent = POINTER(IUnknown)()

# res = atl.AtlAxGetControl(hwnd2, byref(Icontrol))
res = atl.AtlAxCreateControlEx(progID, frame.Handle, None, byref(Iwindow),byref(Icontrol),byref(GUID()),Ievent)
control = GetBestInterface(Icontrol)
# control.Navigate2("http://www.google.com/")


# Event Sink Connection
################################################################################
class EventSink(object):
    def DWebBrowserEvents2_DownloadComplete(self, *args):
        print "DownloadComplete", args


sink = EventSink()
connection = GetEvents(control, sink)
# print connection

################################################################################

#T port 80/443 , T+1 port 82/442 ,  reqType=1 T盤 , reqType=2  T+1盤
control.SetMktLogon('L223805612', 'talented0020', '203.66.93.84', '80', 1, 0)
# control.SetMktLogon(self.Account, self.Pwd, '203.66.93.84', '82', 2, 1)
# print ('login')



# Event Loop
################################################################################
from PyQt4.QtGui import *

app = QApplication([])
app.exec_()

