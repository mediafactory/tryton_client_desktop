#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk
from interface import WidgetInterface, TranslateMixin
from tryton.config import CONFIG

try:
    import gtkspell
except ImportError:
    gtkspell = None


class TextBox(WidgetInterface, TranslateMixin):

    def __init__(self, field_name, model_name, attrs=None):
        super(TextBox, self).__init__(field_name, model_name, attrs=attrs)

        self.widget = gtk.VBox()
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.scrolledwindow.set_size_request(-1, 80)

        self.textview = gtk.TextView()
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        #TODO better tab solution
        self.textview.set_accepts_tab(False)
        self.textview.connect('focus-in-event', lambda x, y: self._focus_in())
        self.textview.connect('focus-out-event',
            lambda x, y: self._focus_out())
        self.textview.connect('key-press-event', self.send_modified)
        self.scrolledwindow.add(self.textview)
        self.scrolledwindow.show_all()

        hbox = gtk.HBox()
        hbox.pack_start(self.scrolledwindow)
        self.widget.pack_end(hbox)
        self.lang = None

        self.button = None
        if attrs.get('translate'):
            self.button = self.translate_button()
            hbox.pack_start(self.button, False, False)

    def translate_widget(self):
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
            gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        scrolledwindow.set_size_request(-1, 80)

        textview = gtk.TextView()
        textview.set_wrap_mode(gtk.WRAP_WORD)
        textview.set_accepts_tab(False)

        scrolledwindow.add(textview)
        return scrolledwindow

    @staticmethod
    def translate_widget_set(widget, value):
        textview = widget.get_child()
        buf = textview.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        buf.insert(buf.get_start_iter(), value or '')

    @staticmethod
    def translate_widget_get(widget):
        textview = widget.get_child()
        buf = textview.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    @staticmethod
    def translate_widget_set_readonly(widget, value):
        textview = widget.get_child()
        textview.set_editable(not value)
        textview.props.sensitive = not value

    def grab_focus(self):
        return self.textview.grab_focus()

    def _readonly_set(self, value):
        super(TextBox, self)._readonly_set(value)
        self.textview.set_editable(not value)
        if self.button:
            self.button.set_sensitive(not value)
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.textview])
        if gtkspell:
            spell = None
            try:
                spell = gtkspell.get_from_text_view(self.textview)
            except Exception:
                pass

            if not value and self.attrs.get('spell') \
                    and CONFIG['client.spellcheck'] \
                    and self.record:
                language = self.record.expr_eval(self.attrs['spell'])
                try:
                    if not spell:
                        spell = gtkspell.Spell(self.textview)
                    if self.lang != language:
                        try:
                            spell.set_language(language)
                        except Exception:
                            spell.detach()
                            del spell
                        self.lang = language
                except Exception:
                    pass
            elif spell:
                spell.detach()
                del spell

    def _color_widget(self):
        return self.textview

    @property
    def modified(self):
        if self.record and self.field:
            return self.field.get_client(self.record) != self.get_value()
        return False

    def get_value(self):
        buf = self.textview.get_buffer()
        iter_start = buf.get_start_iter()
        iter_end = buf.get_end_iter()
        return buf.get_text(iter_start, iter_end, False)

    def set_value(self, record, field):
        field.set_client(record, self.get_value())

    def display(self, record, field):
        super(TextBox, self).display(record, field)
        value = field and field.get(record)
        if not value:
            value = ''
        buf = self.textview.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        iter_start = buf.get_start_iter()
        buf.insert(iter_start, value)

        if gtkspell:
            spell = None
            try:
                spell = gtkspell.get_from_text_view(self.textview)
            except Exception:
                pass

            if self.attrs.get('spell') and CONFIG['client.spellcheck'] \
                    and self.record:
                language = self.record.expr_eval(self.attrs['spell'])
                try:
                    if not spell:
                        spell = gtkspell.Spell(self.textview)
                    if self.lang != language:
                        try:
                            spell.set_language(language)
                        except Exception:
                            spell.detach()
                            del spell
                        self.lang = language
                except Exception:
                    pass
            elif spell:
                spell.detach()
                del spell
