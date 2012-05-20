from tryton.gui.window import Window
from tryton.version import VERSION
try:
    import webkit
except:
    webkit = None
    
try:
    import win32con
    
    from ctypes import *
    from ctypes.wintypes import *
    from comtypes import IUnknown
    from comtypes.automation import IDispatch, VARIANT
    from comtypes.client import wrap
    
    kernel32 = windll.kernel32
    user32 = windll.user32
    atl = windll.atl                  # If this fails, you need atl.dll
except:
    win32con = None
    
from urlparse import urlparse
import webbrowser
import gtk

# TODO: limit access to websites
# TODO: keepalive to server
# TODO: make actions callable (better through tryton.action.main.executeAction?)
# TODO: security setting, if tryton:// allowed => origin = safe sites?
# TODO: set UserAgent

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
        self.webview.settings = self.get_settings()
        self.webview.settings.props.user_agent += ' tryton/%s' % VERSION
        #self.webview.set_border_width(0)
        #self.scrolledwindow.set_border_width(0)
        #self.webview.settings.set_property('enable-default-context-menu', False)
        self.add(self.webview)

        self.webview.connect("navigation-requested", self.on_navigation_requested)
        
    def on_navigation_requested(self, view, frame, req, data=None):
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

class IE(gtk.DrawingArea):
    def __init__(self, *args, **kwargs):
        if not win32con:
            raise Exception('some windows librarys not found or boundled with tryton')

        super(IE, self).__init__(*args, **kwargs)            
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
            user32.CreateWindowExA(0, "AtlAxWin", "http://www.pygtk.org",
                            win32con.WS_VISIBLE | win32con.WS_CHILD |
                            win32con.WS_HSCROLL | win32con.WS_VSCROLL,
                            0, 0, 100, 100, parentHwnd, None, hInstance, 0)
        
        # Get the IWebBrowser2 interface for the IE control.
        pBrowserUnk = POINTER(IUnknown)()
        atl.AtlAxGetControl(self.atlAxWinHwnd, byref(pBrowserUnk))
        # the wrap call querys for the default interface
        self.pBrowser = wrap(pBrowserUnk)
        
        # Create a Gtk window that refers to the native AtlAxWin window.
        self.gtkAtlAxWin = gtk.gdk.window_foreign_new(long(self.atlAxWinHwnd))

    def on_container_size(self, widget, sizeAlloc):
        self.gtkAtlAxWin.move_resize(0, 0, sizeAlloc.width, sizeAlloc.height)

    def on_container_focus(self, widget, data):
        # Pass the focus to IE.  First get the HWND of the IE control; this
        # is a bit of a hack but I couldn't make IWebBrowser2._get_HWND work.
        rect = RECT()
        user32.GetWindowRect(self.atlAxWinHwnd, byref(rect))
        ieHwnd = user32.WindowFromPoint(POINT(rect.left, rect.top))
        user32.SetFocus(ieHwnd)
        
    def open(self, url):
        v = byref(VARIANT())
        self.pBrowser.Navigate(url, v, v, v, v)