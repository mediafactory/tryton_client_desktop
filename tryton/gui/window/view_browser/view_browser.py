#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
'View browser'

import gtk
from tryton.common.browser import Webkit, IE
import xml.dom.minidom
from tryton.config import CONFIG
from tryton.common import RPCExecute, RPCException
import re

class ViewBrowser(object):
    'View browser'

    def __init__(self, parent, arch, context=None):
        self.context = context
        self.arch = arch
        self.parentObj = parent
        values = []
        
        xml_dom = xml.dom.minidom.parseString(arch)

        self.widget = gtk.VBox()

        if CONFIG['browser.type'] == 'webkit':
            self.webview = Webkit()
            self.webview.webview.connect("document-load-finished", self.on_document_load_finished)
            self.widget.add(self.webview)
            
        else:
            self.webview = IE()
            self.webview.browserTitleChanged += self.on_title_changed
            self.widget.add(self.webview)

        self.widget.show_all()
        
        url = xml_dom.documentElement.attributes.get('url')
        if url:
            url = url.value
            
            tag_re = re.compile('(%s.*?%s)' % (re.escape('{{'), re.escape('}}')))
            for bit in tag_re.split(url):
                if bit:
                    if bit.startswith('{{'):
                        values.append(bit[2:-2].strip())
                        
            if len(values) > 0:
                try:
                    self.values = RPCExecute('common', '', 'config', values)
                except RPCException:
                    raise
                
                for bit in tag_re.split(url):
                    if bit:
                        if bit.startswith('{{'):
                            url = url.replace(bit, self.values[bit[2:-2].strip()])
                
        else:
            url = 'about:blank'
        self.webview.open(url)

    def widget_get(self):
        return self.widget
    
    def on_document_load_finished(self, view, frame, data=None):
        if frame.props.title:
            self.parentObj.title.set_label('<b>' + frame.props.title + '</b>')            
            
    def on_title_changed(self, title):
        if title:
            self.parentObj.title.set_label('<b>' + title + '</b>')