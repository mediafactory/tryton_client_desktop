#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import operator
import gtk
import gobject
import gettext
import math
from interface import WidgetInterface
from tryton.gui.window.win_search import WinSearch
from tryton.gui.window.win_form import WinForm
from tryton.gui.window.view_form.screen import Screen
from tryton.exceptions import TrytonServerError
import tryton.rpc as rpc
import tryton.common as common
from tryton.config import CONFIG

_ = gettext.gettext


class Reference(WidgetInterface):

    def __init__(self, field_name, model_name, attrs=None):
        super(Reference, self).__init__(field_name, model_name, attrs=attrs)

        self.widget = gtk.HBox(spacing=0)

        self.widget_combo = gtk.ComboBoxEntry()
        child = self.widget_combo.get_child()
        child.set_editable(False)
        child.connect('changed',
                self.sig_changed_combo)
        child.connect('key_press_event', self.sig_key_pressed)
        self.widget.pack_start(self.widget_combo, expand=False, fill=True)

        self.widget.pack_start(gtk.Label('-'), expand=False, fill=False)

        self.wid_text = gtk.Entry()
        self.wid_text.set_property('width-chars', 13)
        self.wid_text.connect('key_press_event', self.sig_key_press)
        self.wid_text.connect_after('changed', self.sig_changed)
        self.changed = True
        self.wid_text.connect_after('activate', self.sig_activate)
        self.wid_text.connect_after('focus-out-event', self.sig_focus_out,
                True)
        self.focus_out = True
        self.widget.pack_start(self.wid_text, expand=True, fill=True)

        self.but_open = gtk.Button()
        img_find = gtk.Image()
        img_find.set_from_stock('tryton-find', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_open = gtk.Image()
        img_open.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_open.set_image(img_find)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        self.but_open.connect('clicked', self.sig_activate)
        self.but_open.set_alignment(0.5, 0.5)
        self.widget.pack_start(self.but_open, padding=2, expand=False,
                fill=False)

        self.but_new = gtk.Button()
        img_new = gtk.Image()
        img_new.set_from_stock('tryton-new', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_new.set_image(img_new)
        self.but_new.set_relief(gtk.RELIEF_NONE)
        self.but_new.connect('clicked', self.sig_new)
        self.but_new.set_alignment(0.5, 0.5)
        self.widget.pack_start(self.but_new, expand=False, fill=False)

        self.widget.set_focus_chain([self.widget_combo, self.wid_text])

        tooltips = common.Tooltips()
        tooltips.set_tip(self.but_open, _('Search / Open a record'))
        tooltips.set_tip(self.but_new, _('Create a new record'))
        tooltips.enable()

        self._readonly = False
        self._selection = {}
        self._selection2 = {}
        selection = attrs.get('selection', [])
        if not isinstance(selection, (list, tuple)):
            try:
                selection = rpc.execute('model',
                        self.model_name, selection, rpc.CONTEXT)
            except TrytonServerError, exception:
                common.process_exception(exception)
                selection = []
        selection.sort(key=operator.itemgetter(1))
        if selection:
            pop = sorted((len(x) for x in selection), reverse=True)
            average = sum(pop) / len(pop)
            deviation = int(math.sqrt(sum((x - average)**2 for x in pop) /
                    len(pop)))
            width = max(next((x for x in pop if x < (deviation * 4)), 10), 10)
        else:
            width = 10
        child.set_width_chars(width)

        self.set_popdown(selection)

        self.last_key = (None, 0)
        self.key_catalog = {}

    def grab_focus(self):
        return self.widget_combo.grab_focus()

    def get_model(self):
        child = self.widget_combo.get_child()
        res = child.get_text()
        return self._selection.get(res, False)

    def set_popdown(self, selection):
        model = gtk.ListStore(gobject.TYPE_STRING)
        lst = []
        for (i, j) in selection:
            name = str(j)
            lst.append(name)
            self._selection[name] = i
            self._selection2[i] = name
        self.key_catalog = {}
        for name in lst:
            i = model.append()
            model.set(i, 0, name)
            if name:
                key = name[0].lower()
                self.key_catalog.setdefault(key, []).append(i)
        self.widget_combo.set_model(model)
        self.widget_combo.set_text_column(0)
        return lst

    def _readonly_set(self, value):
        self._readonly = value
        self.widget_combo.set_sensitive(not value)
        self.wid_text.set_editable(not value)
        self.but_new.set_sensitive(not value)
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.widget_combo, self.wid_text])

    def _color_widget(self):
        return self.wid_text

    def set_value(self, record, field):
        return

    def sig_activate(self, widget=None):
        self.sig_focus_out(widget, None)

    def sig_focus_out(self, widget, event, leave=False):
        if not self.focus_out:
            return
        child = self.widget_combo.get_child()
        self.changed = False
        value = self.field.get_client(self.record)

        self.focus_out = False
        if not value:
            model, (obj_id, name) = self.get_model() or '', (-1, '')
        else:
            try:
                model, (obj_id, name) = value
            except ValueError:
                self.focus_out = True
                return
        if model and obj_id >= 0:
            if not leave:
                screen = Screen(model, mode=['form'])
                screen.load([obj_id])
                def callback(result):
                    if result and screen.save_current():
                        value = (screen.current_record.id,
                                screen.current_record.rec_name())
                        self.field.set_client(self.record, (model, value),
                                force_change=True)
                    self.focus_out = True
                    self.changed = True
                    self.display(self.record, self.field)
                WinForm(screen, callback)
                return
        elif model:
            if not self._readonly and ( self.wid_text.get_text() or not leave):
                domain = self.field.domain_get(self.record)
                context = self.field.context_get(self.record)

                try:
                    if self.wid_text.get_text():
                        dom = [('rec_name', 'ilike',
                                '%' + self.wid_text.get_text() + '%'),
                                domain]
                    else:
                        dom = domain
                    ids = rpc.execute('model', model, 'search', dom, 0,
                            CONFIG['client.limit'], None, context)
                except TrytonServerError, exception:
                    self.focus_out = True
                    self.changed = True
                    common.process_exception(exception)
                    return
                if ids and len(ids) == 1:
                    self.field.set_client(self.record, (model, (ids[0], '')))
                    self.display(self.record, self.field)
                    self.focus_out = True
                    self.changed = True
                    return

                def callback(ids):
                    if ids:
                        self.field.set_client(self.record, (model, (ids[0], '')))
                    self.focus_out = True
                    self.changed = True
                    self.display(self.record, self.field)
                WinSearch(model, callback, sel_multi=False, ids=ids,
                        context=context, domain=domain)
                return
        else:
            self.field.set_client(self.record, ('', (name, name)))
        self.focus_out = True
        self.changed = True
        self.display(self.record, self.field)

    def sig_new(self, *args):
        model = self.get_model()
        if not model:
            return
        screen = Screen(model, mode=['form'])
        def callback(result):
            if result and screen.save_current():
                value = (screen.current_record.id,
                        screen.current_record.rec_name())
                self.field.set_client(self.record, (model, value))
        WinForm(screen, callback, new=True)

    def sig_key_press(self, widget, event):
        editable = self.wid_text.get_editable()
        if event.keyval == gtk.keysyms.F3 and editable:
            self.sig_new(widget, event)
            return True
        elif event.keyval == gtk.keysyms.F2:
            self.sig_focus_out(widget, event)
            return True
        elif event.keyval in (gtk.keysyms.Tab, gtk.keysyms.Return) and editable:
            if self.field.get(self.record) or \
                    not self.wid_text.get_text():
                return False
            self.sig_focus_out(widget, event, leave=True)
            return True
        return False

    def sig_changed_combo(self, *args):
        if not self.changed:
            return
        self.wid_text.set_text('')
        self.wid_text.set_position(0)
        self.field.set_client(self.record, (self.get_model(), (-1, '')))

    def sig_changed(self, *args):
        if not self.changed:
            return False
        val = self.field.get_client(self.record)
        if not val:
            model, (obj_id, name) = '', (-1, '')
        else:
            model, (obj_id, name) = val
        if self.get_model() and obj_id >= 0:
            self.field.set_client(self.record, (self.get_model(), (-1, '')))
            self.display(self.record, self.field)
        return False

    def display(self, record, field):
        child = self.widget_combo.get_child()
        self.changed = False
        if not field:
            child.set_text('')
            child.set_position(0)
            self.changed =True
            return False
        super(Reference, self).display(record, field)
        value = field.get_client(record)
        img = gtk.Image()
        if not value:
            model, (obj_id, name) = '', (-1, '')
        else:
            model, (obj_id, name) = value
        if model:
            child.set_text(self._selection2[model])
            child.set_position(len(self._selection2[model]))
            self.wid_text.set_text(name)
            self.wid_text.set_position(len(name))
            if obj_id >= 0:
                img.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
                self.but_open.set_image(img)
            else:
                img.set_from_stock('tryton-find', gtk.ICON_SIZE_SMALL_TOOLBAR)
                self.but_open.set_image(img)
        else:
            child.set_text('')
            child.set_position(0)
            self.wid_text.set_text(str(name))
            self.wid_text.set_position(len(str(name)))
            img.set_from_stock('tryton-find', gtk.ICON_SIZE_SMALL_TOOLBAR)
            self.but_open.set_image(img)
        self.changed = True

    def sig_key_pressed(self, *args):
        key = args[1].string.lower()
        if self.last_key[0] == key:
            self.last_key[1] += 1
        else:
            self.last_key = [ key, 1 ]
        if not self.key_catalog.has_key(key):
            return
        self.widget_combo.set_active_iter(
                self.key_catalog[key][self.last_key[1] \
                        % len(self.key_catalog[key])])
