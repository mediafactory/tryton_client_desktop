"""
browser
"""
import gtk
from tryton.common.browser import Webkit, IE
from interface import WidgetInterface
from tryton.config import CONFIG

class Browser(WidgetInterface):
    lastURL = ''
    
    def __init__(self, field_name, model_name, attrs=None):
        super(Browser, self).__init__(field_name, model_name, attrs=attrs)

        self.widget = gtk.VBox()
        
        if CONFIG['browser.type'] == 'webkit':
            self.webview = Webkit()
            self.widget.add(self.webview)
            
        else:
            self.webview = IE()
            self.widget.add(self.webview)
            
        self.widget.show_all()
        
    def grab_focus(self):
        return self.webview.grab_focus()

    def display(self, record, field):
        super(Browser, self).display(record, field)
        thisURL = ''
        
        if record:
            thisURL = record.value.get(field.name)
        if not thisURL:
            thisURL = 'about:blank'
        
        if thisURL and thisURL != self.lastURL:
            self.lastURL = thisURL
            self.webview.open(thisURL)