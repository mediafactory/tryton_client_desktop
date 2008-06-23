#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
from interface import WidgetInterface

class CheckBox(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(CheckBox, self).__init__(window, parent, model, attrs)
        self.widget = gtk.CheckButton()
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.connect_after('toggled', self.sig_activate)

    def _readonly_set(self, value):
        super(CheckBox, self)._readonly_set(value)
        self.widget.set_sensitive(not value)

    def set_value(self, model, model_field):
        model_field.set_client(model, int(self.widget.get_active()))

    def display(self, model, model_field):
        super(CheckBox, self).display(model, model_field)
        if not model_field:
            self.widget.set_active(False)
            return False
        self.widget.set_active(bool(model_field.get(model)))
