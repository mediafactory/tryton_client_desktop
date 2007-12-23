import base64
import gtk
import gettext
import os
from tryton.common import file_selection, message
from interface import WidgetInterface

_ = gettext.gettext


class Binary(WidgetInterface):
    "Binary"

    def __init__(self, window, parent, model, attrs=None):
        super(Binary, self).__init__(window, parent, model, attrs)

        self.widget = gtk.HBox(spacing=5)
        self.wid_text = gtk.Entry()
        self.wid_text.set_property('activates_default', True)
        self.widget.pack_start(self.wid_text, expand=True, fill=True)

        self.but_new = gtk.Button(stock='gtk-open')
        self.but_new.connect('clicked', self.sig_new)
        self.widget.pack_start(self.but_new, expand=False, fill=False)

        self.but_save_as = gtk.Button(stock='gtk-save-as')
        self.but_save_as.connect('clicked', self.sig_save_as)
        self.widget.pack_start(self.but_save_as, expand=False, fill=False)

        self.but_remove = gtk.Button(stock='gtk-clear')
        self.but_remove.connect('clicked', self.sig_remove)
        self.widget.pack_start(self.but_remove, expand=False, fill=False)

        self.model_field = None

    def _readonly_set(self, value):
        if value:
            self.but_new.hide()
            self.but_remove.hide()
        else:
            self.but_new.show()
            self.but_remove.show()

    def sig_new(self, widget=None):
        try:
            filename = file_selection(_('Open...'),
                    parent=self._window)
            if filename and self.model_field:
                self.model_field.set_client(self._view.model,
                        base64.encodestring(file(filename, 'rb').read()))
                fname = self.attrs.get('fname_widget', False)
                if fname:
                    self.parent.value = {fname:os.path.basename(filename)}
                self.display(self._view.model, self.model_field)
        except:
            message(_('Error reading the file'), self._window)

    def sig_save_as(self, widget=None):
        try:
            filename = file_selection(_('Save As...'),
                    parent=self._window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
            if filename and self.model_field:
                file_p = file(filename,'wb+')
                file_p.write(base64.decodestring(
                    self.model_field.get(self._view.model)))
                file_p.close()
        except:
            message(_('Error writing the file!'), self._window)

    def sig_remove(self, widget=None):
        if self.model_field:
            self.model_field.set_client(self._view.model, False)
            fname = self.attrs.get('fname_widget', False)
            if fname:
                self.parent.value = {fname:False}
        self.display(self._view.model, self.model_field)

    def display(self, model, model_field):
        super(Binary, self).display(model, model_field)
        if not model_field:
            self.wid_text.set_text('')
            return False
        self.model_field = model_field
        self.wid_text.set_text(self._size_get(model_field.get(model)))
        return True

    def _size_get(self, value):
        return value and ('%d ' + _('bytes')) % len(value) or ''

    def set_value(self, model, model_field):
        return

    def _color_widget(self):
        return self.wid_text
