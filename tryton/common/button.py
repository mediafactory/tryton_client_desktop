#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk

from tryton.common import ICONFACTORY


class Button(gtk.Button):

    def __init__(self, attrs=None):
        self.attrs = attrs or {}
        label = attrs.get('string', '')
        if '_' not in label:
            label = '_' + label
        super(Button, self).__init__(label=label, stock=None,
            use_underline=True)
        self._set_icon(attrs.get('icon'))

    def _set_icon(self, stock):
        if not stock:
            self.set_image(gtk.Image())
            return
        ICONFACTORY.register_icon(stock)
        icon = gtk.Image()
        icon.set_from_stock(stock, gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.set_image(icon)

    def state_set(self, record):
        if record:
            states = record.expr_eval(self.attrs.get('states', {}),
                check_load=False)
        else:
            states = {}
        if states.get('invisible', False):
            self.hide()
        else:
            self.show()
        self.set_sensitive(not states.get('readonly', False))
        self._set_icon(states.get('icon', self.attrs.get('icon')))
        parent = record.parent if record else None
        while parent:
            if parent.modified:
                self.set_sensitive(False)
                break
            parent = parent.parent
