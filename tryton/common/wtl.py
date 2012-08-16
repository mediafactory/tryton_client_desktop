##        Copyright (c) 2003 Henk Punt

## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

#from windows import *
#from gdi import *
from ctypes import *
import win32gui
import weakref
from ctypes.wintypes import MSG

NULL = 0
DWORD = c_ulong
HANDLE = c_ulong
UINT = c_uint
BOOL = c_int
HWND = HANDLE
HINSTANCE = HANDLE
HICON = HANDLE
HDC = HANDLE
HCURSOR = HANDLE
HBRUSH = HANDLE
HMENU = HANDLE
HBITMAP = HANDLE
ULONG_PTR = DWORD
INT = c_int
LPCTSTR = c_char_p
LPTSTR = c_char_p
WORD = c_ushort
LPARAM = c_ulong
WPARAM = c_uint
LPVOID = c_voidp
LONG = c_ulong
BYTE = c_byte
TCHAR = c_char_p
DWORD_PTR = c_ulong #TODO what is this exactly?
INT_PTR = c_ulong  #TODO what is this exactly?
COLORREF = c_ulong

WndProc = WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)

GetMessage = windll.user32.GetMessageA
TranslateMessage = windll.user32.TranslateMessage
DispatchMessage = windll.user32.DispatchMessageA

def LOWORD(dword):
    return dword & 0x0000ffff

def HIWORD(dword):
    return dword >> 16

def GET_XY_LPARAM(lParam):
    x = LOWORD(lParam)
    if x > 32768:
        x = x - 65536
    y = HIWORD(lParam)
    return x, y 

hndlMap = weakref.WeakValueDictionary()

def globalWndProc(hWnd, nMsg, wParam, lParam):
    """The purpose of globalWndProc is to let each (python) window instance
    handle its own msgs, therefore is a mapping maintained from hWnd to window instance"""
    #if nMsg == WM_SIZE:
    #    print "WM_SIZE", hWnd, hndlMap.get(hWnd, None)
    #if nMsg == WM_NOTIFY:
    #    print "gwp: ", hWnd, nMsg, wParam, lParam, hndlMap.get(hWnd, None)
    

    handled = 0
    window = hndlMap.get(hWnd, None)
    if window:
        #let the window process its own msgs
        handled, result = window.WndProc(hWnd, nMsg, wParam, lParam)
        if not handled and window._class_: #its a subclassed window, try old window proc
            result = win32gui.CallWindowProc(window._old_wnd_proc_, hWnd, nMsg, wParam, lParam)
            handled = 1
        
    if not handled:
        return win32gui.DefWindowProc(hWnd, nMsg, wParam, lParam)
    else:
        return result

cGlobalWndProc = WndProc(globalWndProc)

def handle(obj):
    if not obj:
        return NULL
    elif hasattr(obj, 'handle'):
        return obj.handle
    else:
        return obj

def instanceFromHandle(handle):
    return hndlMap.get(handle, None)

def instanceOrHandle(handle):
    return hndlMap.get(handle, handle)

class Event(object):
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self.hWnd = hWnd
        self.nMsg = nMsg
        self.lParam = lParam
        self.wParam = wParam
        self.handled = 0
        
    def getSize(self):
        return LOWORD(self.lParam), HIWORD(self.lParam)

    size = property(getSize, None, None, "")

    def getPosition(self):
        return GET_XY_LPARAM(self.lParam)

    position = property(getPosition, None, None, "")

    def __str__(self):
        return "<event hWnd: %d, nMsg: %d, lParam: %d, wParam: %d>" % (self.hWnd, self.nMsg,
                                                                       self.lParam, self.wParam)
    
class MSG_MAP(object):
    def __init__(self, entries):
        self._msg_map_ = {}
        self._chained_ = []

        for entry in entries:
            entry.__install__(self)

    def Dispatch(self, receiver, hWnd, nMsg, wParam, lParam):
        handler = self._msg_map_.get(nMsg, None)
        if handler:
            event = Event(hWnd, nMsg, wParam, lParam)
            event.handled = 1
            result = handler(receiver, event)
            if result == None:
                return (event.handled, 0)
            else:
                return (event.handled, result)
        else:
            for msgMap in self._chained_:
                result = msgMap.Dispatch(receiver, hWnd, nMsg, wParam, lParam)
                if result:
                    handled, result = result
                    if handled:
                        return (handled, result)

        #nobody handled msg
        return (0, 0)

    def DispatchMSG(self, receiver, msg):
        return self.Dispatch(receiver, msg.hWnd, msg.message,
                             msg.wParam, msg.lParam)
        
class MSG_HANDLER(object):
    def __init__(self, msg, handler):
        self.msg, self.handler = msg, handler

    def __install__(self, msgMap):
        msgMap._msg_map_[self.msg] = self

    def __call__(self, receiver, event):
        return self.handler(receiver, event)

class CHAIN_MSG_MAP(object):
    def __init__(self, msgMap):
        self.msgMap = msgMap

    def __install__(self, msgMap):
        msgMap._chained_.append(self.msgMap)


#TODO allow the addition of more specific filters
class MessageLoop:
    def __init__(self):
        self.m_filters = {}

    def AddFilter(self, filter):
        self.m_filters[filter] = filter

    def RemoveFilter(self, filter):
        del self.m_filters[filter]
        
    def Run(self):
        msg = MSG()
        lpmsg = byref(msg)
        while GetMessage(lpmsg, 0, 0, 0):
            if not self.PreTranslateMessage(msg):
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
      
    def OneLoop(self):          
        msg = MSG()
        lpmsg = byref(msg)
        if GetMessage(lpmsg, 0, 0, 0):
            if not self.PreTranslateMessage(msg):
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
        return True
                    
    def PreTranslateMessage(self, msg):
        for filter in self.m_filters:
            if filter.PreTranslateMessage(msg):
                return 1
        return 0
    
theMessageLoop = MessageLoop()

def GetMessageLoop():
    return theMessageLoop

def Run():
    theMessageLoop.Run()
    #hWndMap should be empty at this point, container widgets
    #should auto-dispose of their children! (somehow)
    ##print hndlMap