#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk
import gettext
from tryton.common import TRYTON_ICON, COLOR_SCHEMES
from interface import WidgetInterface
from tryton.gui.window.view_form.screen import Screen
from tryton.gui.window.view_form.model.group import Group
from tryton.gui.window.win_search import WinSearch
from tryton.gui.window.win_form import WinForm
from tryton.gui.window.view_form.widget_search.form import _LIMIT
import tryton.common as common
import tryton.rpc as rpc
import pango

_ = gettext.gettext


class One2Many(WidgetInterface):

    def __init__(self, field_name, model_name, window, attrs=None):
        super(One2Many, self).__init__(field_name, model_name, window,
                attrs=attrs)

        self.widget = gtk.VBox(homogeneous=False, spacing=5)

        hbox = gtk.HBox(homogeneous=False, spacing=0)
        menubar = gtk.MenuBar()
        if hasattr(menubar, 'set_pack_direction') and \
                hasattr(menubar, 'set_child_pack_direction'):
            menubar.set_pack_direction(gtk.PACK_DIRECTION_LTR)
            menubar.set_child_pack_direction(gtk.PACK_DIRECTION_LTR)

        menuitem_title = gtk.ImageMenuItem(stock_id='tryton-preferences')

        menu_title = gtk.Menu()
        menuitem_set_to_default = gtk.MenuItem(_('Set to default value'), True)
        menuitem_set_to_default.connect('activate',
                lambda *x: self._menu_sig_default_get())
        menu_title.add(menuitem_set_to_default)
        menuitem_set_default = gtk.MenuItem(_('Set as default'), True)
        menuitem_set_default.connect('activate',
                lambda *x: self._menu_sig_default_set())
        menu_title.add(menuitem_set_default)
        menuitem_reset_default = gtk.MenuItem(_('Reset default'), True)
        menuitem_reset_default.connect('activate',
                lambda *x: self._menu_sig_default_set(reset=True))
        menu_title.add(menuitem_reset_default)
        menuitem_title.set_submenu(menu_title)

        menubar.add(menuitem_title)
        hbox.pack_start(menubar, expand=True, fill=True)

        tooltips = common.Tooltips()

        if attrs.get('add_remove'):

            self.wid_text = gtk.Entry()
            self.wid_text.set_property('width_chars', 13)
            self.wid_text.connect('activate', self._sig_activate)
            hbox.pack_start(self.wid_text, expand=True, fill=True)

            self.but_add = gtk.Button()
            tooltips.set_tip(self.but_add, _('Add'))
            self.but_add.connect('clicked', self._sig_add)
            img_add = gtk.Image()
            img_add.set_from_stock('tryton-list-add', gtk.ICON_SIZE_SMALL_TOOLBAR)
            img_add.set_alignment(0.5, 0.5)
            self.but_add.add(img_add)
            self.but_add.set_relief(gtk.RELIEF_NONE)
            hbox.pack_start(self.but_add, expand=False, fill=False)

            self.but_remove = gtk.Button()
            tooltips.set_tip(self.but_remove, _('Remove'))
            self.but_remove.connect('clicked', self._sig_remove, True)
            img_remove = gtk.Image()
            img_remove.set_from_stock('tryton-list-remove', gtk.ICON_SIZE_SMALL_TOOLBAR)
            img_remove.set_alignment(0.5, 0.5)
            self.but_remove.add(img_remove)
            self.but_remove.set_relief(gtk.RELIEF_NONE)
            hbox.pack_start(self.but_remove, expand=False, fill=False)

            hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        self.but_new = gtk.Button()
        tooltips.set_tip(self.but_new, _('Create a new record'))
        self.but_new.connect('clicked', self._sig_new)
        img_new = gtk.Image()
        img_new.set_from_stock('tryton-new', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_new.set_alignment(0.5, 0.5)
        self.but_new.add(img_new)
        self.but_new.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(self.but_new, expand=False, fill=False)

        self.but_open = gtk.Button()
        tooltips.set_tip(self.but_open, _('Edit selected record'))
        self.but_open.connect('clicked', self._sig_edit)
        img_open = gtk.Image()
        img_open.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_open.set_alignment(0.5, 0.5)
        self.but_open.add(img_open)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(self.but_open, expand=False, fill=False)

        self.but_del = gtk.Button()
        tooltips.set_tip(self.but_del, _('Delete selected record'))
        self.but_del.connect('clicked', self._sig_remove)
        img_del = gtk.Image()
        img_del.set_from_stock('tryton-delete', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_del.set_alignment(0.5, 0.5)
        self.but_del.add(img_del)
        self.but_del.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(self.but_del, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        but_pre = gtk.Button()
        tooltips.set_tip(but_pre, _('Previous'))
        but_pre.connect('clicked', self._sig_previous)
        img_pre = gtk.Image()
        img_pre.set_from_stock('tryton-go-previous', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_pre.set_alignment(0.5, 0.5)
        but_pre.add(img_pre)
        but_pre.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_pre, expand=False, fill=False)

        self.label = gtk.Label('(0,0)')
        hbox.pack_start(self.label, expand=False, fill=False)

        but_next = gtk.Button()
        tooltips.set_tip(but_next, _('Next'))
        but_next.connect('clicked', self._sig_next)
        img_next = gtk.Image()
        img_next.set_from_stock('tryton-go-next', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_next.set_alignment(0.5, 0.5)
        but_next.add(img_next)
        but_next.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_next, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        but_switch = gtk.Button()
        tooltips.set_tip(but_switch, _('Switch'))
        but_switch.connect('clicked', self.switch_view)
        img_switch = gtk.Image()
        img_switch.set_from_stock('tryton-fullscreen', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_switch.set_alignment(0.5, 0.5)
        but_switch.add(img_switch)
        but_switch.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_switch, expand=False, fill=False)

        if attrs.get('add_remove'):
            hbox.set_focus_chain([self.wid_text])
        else:
            hbox.set_focus_chain([])

        tooltips.enable()

        self.widget.pack_start(hbox, expand=False, fill=True)

        self.screen = Screen(attrs['relation'], self.window,
                view_type=attrs.get('mode', 'tree,form').split(','),
                views_preload=attrs.get('views', {}),
                row_activate=self._on_activate,
                exclude_field=attrs.get('relation_field', None))
        self.screen.signal_connect(self, 'record-message', self._sig_label)
        menuitem_title.get_child().set_text(attrs.get('string', ''))

        self.widget.pack_start(self.screen.widget, expand=True, fill=True)

        self.screen.widget.connect('key_press_event', self.on_keypress)
        if self.attrs.get('add_remove'):
            self.wid_text.connect('key_press_event', self.on_keypress)

    def grab_focus(self):
        return self.screen.widget.grab_focus()

    def on_keypress(self, widget, event):
        if (event.keyval == gtk.keysyms.F3) \
                and self.but_new.get_property('sensitive'):
            self._sig_new(widget)
            return False
        if event.keyval == gtk.keysyms.F2 \
                and widget == self.screen.widget:
            self._sig_edit(widget)
            return False
        if event.keyval in (gtk.keysyms.Delete, gtk.keysyms.KP_Delete) \
                and widget == self.screen.widget:
            self._sig_remove(widget)
            return False

    def destroy(self):
        self.screen.destroy()

    def _on_activate(self):
        self._sig_edit()

    def switch_view(self, widget):
        self.screen.switch_view()

    def _readonly_set(self, value):
        self.but_new.set_sensitive(not value)
        self.but_del.set_sensitive(not value)
        if self.attrs.get('add_remove'):
            self.wid_text.set_sensitive(not value)
            self.but_add.set_sensitive(not value)
            self.but_remove.set_sensitive(not value)

    def _sig_new(self, widget):
        self.view.set_value()
        ctx = {}
        ctx.update(self.record.expr_eval(self.attrs.get('context', {})))
        sequence = None
        if self.screen.current_view.view_type == 'tree':
            sequence = self.screen.current_view.widget_tree.sequence
        if (self.screen.current_view.view_type == 'form') \
                or self.screen.editable_get():
            self.screen.new(context=ctx)
            self.screen.current_view.widget.set_sensitive(True)
        else:
            readonly = False
            domain = []
            if self.field and self.record:
                readonly = self.field.get_state_attrs(self.record
                        ).get('readonly', False)
                domain = self.field.domain_get(self.record)
            win = WinForm(self.screen, self.window, new=True,
                    context=ctx)
            while True:
                if win.run():
                    win.new()
                else:
                    break
            win.destroy()
        if sequence:
            self.screen.group.set_sequence(field=sequence)

    def _sig_edit(self, widget=None):
        self.view.set_value()
        if self.screen.current_record:
            win = WinForm(self.screen, self.window)
            win.run()
            win.destroy()

    def _sig_next(self, widget):
        self.screen.display_next()

    def _sig_previous(self, widget):
        self.screen.display_prev()

    def _sig_remove(self, widget, remove=False):
        self.screen.remove(remove=remove)

    def _sig_activate(self, *args):
        self._sig_add()
        self.wid_text.grab_focus()

    def _sig_add(self, *args):
        self.view.set_value()
        domain = self.field.domain_get(self.record)
        context = rpc.CONTEXT.copy()
        context.update(self.field.context_get(self.record))
        domain = domain[:]
        domain.extend(self.record.expr_eval(self.attrs.get('add_remove'),
            context))
        removed_ids = self.field.get_removed_ids(self.record)

        try:
            if self.wid_text.get_text():
                dom = [('rec_name', 'ilike', '%' + self.wid_text.get_text() + '%'),
                    ['OR', domain, ('id', 'in', removed_ids)]]
            else:
                dom = ['OR', domain, ('id', 'in', removed_ids)]
            ids = rpc.execute('model', self.attrs['relation'],
                    'search', dom, 0, _LIMIT, None, context)
        except Exception, exception:
            common.process_exception(exception, self.window)
            return False
        if len(ids) != 1:
            win = WinSearch(self.attrs['relation'], sel_multi=True, ids=ids,
                    context=context, domain=domain, parent=self.window,
                    views_preload=self.attrs.get('views', {}))
            ids = win.run()

        res_id = None
        if ids:
            res_id = ids[0]
        self.screen.load(ids, modified=True)
        self.screen.display(res_id=res_id)
        if self.screen.current_view:
            self.screen.current_view.set_cursor()
        self.wid_text.set_text('')

    def _sig_label(self, screen, signal_data):
        name = '_'
        if signal_data[0] >= 0:
            name = str(signal_data[0] + 1)
        line = '(%s/%s)' % (name, signal_data[1])
        self.label.set_text(line)

    def display(self, record, field):
        if field is None:
            self.screen.current_record = None
            self.screen.display()
            return False
        super(One2Many, self).display(record, field)
        new_group = field.get_client(record)
        if id(self.screen.group) != id(new_group):
            self.screen.group = new_group
            if (self.screen.current_view.view_type == 'tree') \
                    and self.screen.editable_get():
                self.screen.current_record = None
            readonly = False
            domain = []
            if record:
                readonly = field.get_state_attrs(record).get('readonly', False)
                domain = field.domain_get(record)
            if self.screen.domain != domain:
                self.screen.domain = domain
            self.screen.group.readonly = readonly
        self.screen.display()
        return True

    def display_value(self):
        return '<' + self.attrs.get('string', '') + '>'

    def set_value(self, record, field):
        self.screen.current_view.set_value()
        if self.screen.is_modified():
            record.modified = True
            record.modified_fields.setdefault(field.name)
        return True
