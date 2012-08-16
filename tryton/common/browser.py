from tryton.common import RPCExecute, RPCException
from tryton.gui.window import Window
from tryton.version import VERSION
try:
    import webkit
except:
    webkit = None
    
try:
    import win32con
    import mshtmlevents
    
    from ctypes import *
    from ctypes.wintypes import *
    from comtypes import IUnknown
    from comtypes.automation import IDispatch, VARIANT
    from comtypes.client import wrap, GetModule
    from comtypes import IUnknown, GUID, COMMETHOD
    import sys
    if not hasattr(sys, 'frozen'):
        GetModule('atl.dll')
        GetModule('shdocvw.dll')
    from comtypes.gen import SHDocVw
    
    kernel32 = windll.kernel32
    user32 = windll.user32
    atl = windll.atl                  # If this fails, you need atl.dll
    import wtl
    GetParent = windll.user32.GetParent

    SID_SShellBrowser = GUID("{000214E2-0000-0000-C000-000000000046}")
    
    class IOleWindow(IUnknown):
        _case_insensitive_ = True
        u'IOleWindow Interface'
        _iid_ = GUID('{00000114-0000-0000-C000-000000000046}')
        _idlflags_ = []
    
        _methods_ = [
            COMMETHOD([], HRESULT, 'GetWindow',
                      ( ['in'], POINTER(c_void_p), 'pHwnd' ))
            ]
    
    class IOleInPlaceActiveObject(IOleWindow):
        _iid_ = GUID("{00000117-0000-0000-C000-000000000046}")
        _idlflags_ = []
        _methods_ = IOleWindow._methods_ + [
            COMMETHOD([], HRESULT, 'TranslateAccelerator',
                      ( ['in'], POINTER(MSG), 'pMsg' ))
            ]
    
except:
    win32con = None
    
from urlparse import urlparse
import webbrowser
import gtk
import pygtk
pygtk.require("2.0")

# TODO: limit access to websites
# TODO: make actions callable (better through tryton.action.main.executeAction?)
# TODO: security setting, if tryton:// allowed => origin = safe sites?
# TODO: set UserAgent in IE => only via registry...
# TODO: Focus GTK IE

class Webkit(gtk.ScrolledWindow):
    safeDomains = []
    
    def __init__(self):
        if not webkit:
            raise Exception('webkit library not found or boundled with tryton')
        
        super(Webkit, self).__init__()
        self.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.set_size_request(-1, 80)
        
        self.webview = webkit.WebView()
        self.webview.settings = self.webview.get_settings()
        self.webview.settings.props.user_agent += ' tryton/%s' % VERSION
        #self.webview.set_border_width(0)
        #self.webview.settings.set_property('enable-default-context-menu', False)
        self.add(self.webview)

        self.webview.connect("navigation-requested", self.on_navigation_requested)
        
    def on_navigation_requested(self, view, frame, req, data=None):
        try:
            RPCExecute('common', '', 'ping', '', False)
        except RPCException:
            raise

        # tryton actions implemented via URI protocoll, as only qtWebkit supports addToJavaScriptWindowObject
        uri = urlparse(req.get_uri())
        if uri.scheme == 'tryton':
            if uri.netloc == 'model':
                # browser => view_id = [291], model = '', res_id = None, domain = [], context = {}, mode = ['browser'], name = 'Google', limit => 0, auto_refresh = 0, search_value => [], icon => ''
                # party.party => view_ids = [119,120], model = 'party.party', res_id = None, domain = [], context => {}, mode = ['tree', 'form'], name = 'Parteien', limit = 0, auto_refresh = 0, search_value = [], icon = ''
                view_ids = []
                mode = []
                name = 'Parteien'
                
                model = uri.path[1:]
                
                Window.create(view_ids, model, mode=mode, name=name)
            
            return True
        

        if len(self.safeDomains) > 0:
            # FIXME: get safeDomains from server (regEx?) and open Browser if not safe...
            webbrowser.open_new_tab(req.get_uri())
            return True
        return False
    
    def open(self, url):
        self.webview.open(url)

class Event:
    def __init__(self):
        self.handlers = set()

    def handle(self, handler):
        self.handlers.add(handler)
        return self

    def unhandle(self, handler):
        try:
            self.handlers.remove(handler)
        except:
            raise ValueError("Handler is not handling this event, so cannot unhandle it.")
        return self

    def fire(self, *args, **kargs):
        for handler in self.handlers:
            handler(*args, **kargs)

    def getHandlerCount(self):
        return len(self.handlers)

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__  = getHandlerCount
        
class IE(gtk.DrawingArea):
    __gsignals__ = { "expose-event": "override" }

    def __init__(self, *args, **kwargs):
        self.workaround_ignore_first_doc_complete = False
        self.ie_initialised = False
        self.already_initialised = False
        self.window_handler = None
        self.node_handlers = {}
        self.startURL = None
        self.browserTitleChanged = Event()
        self.safeDomains = []
        
        if not win32con:
            raise Exception('some windows librarys not found or boundled with tryton')
        super(IE, self).__init__(*args, **kwargs)
        
    def __del__(self):
        self.cleanup(self)
        atl.AtlAxWinTerm()
        
    # Handle the expose-event by drawing
    def do_expose_event(self, event):
        if self.ie_initialised:
            return
        
        self.ie_initialised = True
        # Make the container accept the focus and pass it to the control;
        # this makes the Tab key pass focus to IE correctly.
        self.set_property("can-focus", True)
        self.connect("focus", self.on_container_focus)
        
        # Resize the AtlAxWin window with its container.
        self.connect("size-allocate", self.on_container_size)

        atl.AtlAxWinInit()
        hInstance = kernel32.GetModuleHandleA(None)
        parentHwnd = self.window.handle
        self.atlAxWinHwnd = \
            user32.CreateWindowExA(0, "AtlAxWin", "about:blank",
                            win32con.WS_VISIBLE | win32con.WS_CHILD |
                            win32con.WS_HSCROLL | win32con.WS_VSCROLL,
                            0, 0, 100, 100, parentHwnd, None, hInstance, 0)
        
        # Get the IWebBrowser2 interface for the IE control.
        pBrowserUnk = POINTER(IUnknown)()
        atl.AtlAxGetControl(self.atlAxWinHwnd, byref(pBrowserUnk))
        # the wrap call querys for the default interface
        self.pBrowser = wrap(pBrowserUnk)
        self.pBrowser.AddRef()
        
        self.conn = mshtmlevents.GetEvents(self.pBrowser, sink=self,
                        interface=SHDocVw.DWebBrowserEvents2)
        
        # Create a Gtk window that refers to the native AtlAxWin window.
        self.gtkAtlAxWin = gtk.gdk.window_foreign_new(long(self.atlAxWinHwnd))

        self.gtkAtlAxWin.maximize()
        
        #global msg loop filter needed, see PreTranslateMessage
        wtl.GetMessageLoop().AddFilter(self)
        self.cleanup = wtl.GetMessageLoop().RemoveFilter
        
        if self.startURL:
            v = byref(VARIANT())
            self.pBrowser.Navigate(self.startURL, v, v, v, v)

    #filter needed to make 'del' and other accel keys work
    #within IE control. @see http://www.microsoft.com/mind/0499/faq/faq0499.asp
    def PreTranslateMessage(self, msg):
        #here any keyboard message from the app passes:
        if msg.message >= win32con.WM_KEYFIRST and  msg.message <= win32con.WM_KEYLAST:
            #now we see if the control which sends these msgs is a child of
            #this axwindow (for instance input control embedded in html page)
            parent = msg.hWnd
            while parent:
                parent = GetParent(int(parent))
                if self.window and parent == self.window.handle:
                    #yes its a child of mine
                    app = self.pBrowser.Application
                    ao = app.QueryInterface(IOleInPlaceActiveObject)
                    if ao.TranslateAccelerator(byref(msg)) == 0:
                        #translation has happened
                        return 1

    def TitleChange(self, this, *args):
        self.browserTitleChanged(args[0])
        #print "OnTitleChange", args

    def Visible(self, this, *args):
        #print "OnVisible", args
        pass

    def BeforeNavigate(self, this, *args):
        #print "BeforeNavigate", args
        pass

    def NavigateComplete(self, this, *args):
        #print "NavigateComplete", this, args
        return

    # some DWebBrowserEvents2
    def BeforeNavigate2(self, this, *args):
        #print "BeforeNavigate2", args
        try:
            RPCExecute('common', '', 'ping', '', False)
        except RPCException:
            raise

        uri = urlparse(cast(args[1]._.c_void_p, POINTER(VARIANT))[0].value)
        if uri.scheme == 'tryton':
            if uri.netloc == 'model':
                # browser => view_id = [291], model = '', res_id = None, domain = [], context = {}, mode = ['browser'], name = 'Google', limit => 0, auto_refresh = 0, search_value => [], icon => ''
                # party.party => view_ids = [119,120], model = 'party.party', res_id = None, domain = [], context => {}, mode = ['tree', 'form'], name = 'Parteien', limit = 0, auto_refresh = 0, search_value = [], icon = ''
                view_ids = []
                mode = []
                name = 'Parteien'
                
                model = uri.path[1:]
                
                Window.create(view_ids, model, mode=mode, name=name)
            cast(args[6]._.c_void_p, POINTER(VARIANT_BOOL))[0] = True        

        if len(self.safeDomains) > 0:
            # FIXME: get safeDomains from server (regEx?) and open Browser if not safe...
            webbrowser.open_new_tab(req.get_uri())
            p = cast(args[6]._.c_void_p, POINTER(VARIANT))[0].value
            p.value = True

    def NavigateComplete2(self, this, *args):
        #print "NavigateComplete2", args
        pass

    def DocumentComplete(self, this, *args):
        #print "DocumentComplete", args
        if self.workaround_ignore_first_doc_complete == False:
            # ignore first about:blank.  *sigh*...
            # TODO: work out how to parse *args byref VARIANT
            # in order to get at the URI.
            self.workaround_ignore_first_doc_complete = True
            return
            
        self._loaded()

    def NewWindow2(self, this, *args):
        print "NewWindow2", args
        return
        v = cast(args[1]._.c_void_p, POINTER(VARIANT))[0]
        v.value = True

    def NewWindow3(self, this, *args):
        print "NewWindow3", args
        return
        v = cast(args[1]._.c_void_p, POINTER(VARIANT))[0]
        v.value = True

    def on_container_size(self, widget, sizeAlloc):
        #self.gtkAtlAxWin.move_resize(0, 0, sizeAlloc.width, sizeAlloc.height)
        self.gtkAtlAxWin.maximize()

    def on_container_focus(self, widget, data):
        # Pass the focus to IE.  First get the HWND of the IE control; this
        # is a bit of a hack but I couldn't make IWebBrowser2._get_HWND work.
        rect = RECT()
        user32.GetWindowRect(self.atlAxWinHwnd, byref(rect))
        ieHwnd = user32.WindowFromPoint(POINT(rect.left, rect.top))
        user32.SetFocus(ieHwnd)
        
    def open(self, url):
        if not hasattr(self, 'pBrowser'):
            self.startURL = url
        else:
            v = byref(VARIANT())
            self.pBrowser.Navigate(url, v, v, v, v)

    def addEventListener(self, node, event_name, event_fn):
        
        rcvr = mshtmlevents._DispEventReceiver()
        rcvr.dispmap = {0: event_fn}

        rcvr.sender = node
        ifc = rcvr.QueryInterface(IDispatch)
        v = VARIANT(ifc)
        setattr(node, "on"+event_name, v)
        return ifc

        rcvr = mshtmlevents.GetDispEventReceiver(MSHTML.HTMLElementEvents2, event_fn, "on%s" % event_name)
        rcvr.sender = node
        ifc = rcvr.QueryInterface(IDispatch)
        node.attachEvent("on%s" % event_name, ifc)
        return ifc

    def mash_attrib(self, attrib_name):
        return attrib_name

    def _addWindowEventListener(self, event_name, event_fn):
        
        #print "_addWindowEventListener", event_name, event_fn
        #rcvr = mshtmlevents.GetDispEventReceiver(MSHTML.HTMLWindowEvents,
        #                   event_fn, "on%s" % event_name)
        #print rcvr
        #rcvr.sender = self.getDomWindow()
        #print rcvr.sender
        #ifc = rcvr.QueryInterface(IDispatch)
        #print ifc
        #v = VARIANT(ifc)
        #print v
        #setattr(self.getDomWindow(), "on%s" % event_name, v)
        #return ifc

        wnd = self.pBrowser.Document.parentWindow
        if self.window_handler is None:
            self.window_handler = EventHandler(self)
            self.window_conn = mshtmlevents.GetEvents(wnd,
                                        sink=self.window_handler,
                                    interface=MSHTML.HTMLWindowEvents2)
        self.window_handler.addEventListener(event_name, event_fn)
        return event_name # hmmm...

    def _loaded(self):
        #print "loaded"

        if self.already_initialised:
            return
        self.already_initialised = True