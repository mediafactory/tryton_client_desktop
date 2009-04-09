#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gobject
import gtk
import gettext
from interface import WidgetInterface
from tryton.common import TRYTON_ICON, COLOR_SCHEMES
import tryton.common as common
from tryton.gui.window.view_form.screen import Screen
from tryton.gui.window.win_search import WinSearch
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.action import Action
from tryton.gui.window.view_form.widget_search.form import _LIMIT
import pango

_ = gettext.gettext


class Dialog(object):

    def __init__(self, model, obj_id=None, attrs=None, domain=None,
            context=None, window=None):
        if attrs is None:
            attrs = {}

        self.dia = gtk.Dialog(_('Link'), window,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.window = window
        if ('string' in attrs) and attrs['string']:
            self.dia.set_title(attrs['string'])
        self.dia.set_property('default-width', 760)
        self.dia.set_property('default-height', 500)
        self.dia.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dia.set_icon(TRYTON_ICON)
        self.dia.set_has_separator(False)

        self.accel_group = gtk.AccelGroup()
        self.dia.add_accel_group(self.accel_group)

        icon_cancel = gtk.STOCK_CLOSE
        if not obj_id:
            icon_cancel = gtk.STOCK_CANCEL
        self.but_cancel = self.dia.add_button(icon_cancel,
                gtk.RESPONSE_CANCEL)

        self.but_ok = self.dia.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.but_ok.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Return, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        self.dia.set_default_response(gtk.RESPONSE_OK)
        self.dia.show()

        self.screen = Screen(model, self.dia, domain=domain, context=context,
                view_type=['form'], views_preload=attrs.get('views', {}))
        if obj_id:
            self.screen.load([obj_id])
        else:
            self.screen.new()
        name = attrs.get('string', '')
        if name:
            name += ' - '
        name += self.screen.current_view.title
        self.dia.set_title(name)

        title = gtk.Label()
        title.set_use_markup(True)
        title.modify_font(pango.FontDescription("12"))
        title.set_label('<b>' + name + '</b>')
        title.set_padding(20, 3)
        title.set_alignment(0.0, 0.5)
        title.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        title.show()

        self.info_label = gtk.Label()
        self.info_label.set_padding(3, 3)
        self.info_label.set_alignment(1.0, 0.5)

        self.eb_info = gtk.EventBox()
        self.eb_info.add(self.info_label)
        self.eb_info.connect('button-release-event',
                lambda *a: self.message_info(''))

        vbox = gtk.VBox()
        vbox.pack_start(self.eb_info, expand=True, fill=True, padding=5)
        vbox.show()

        hbox = gtk.HBox()
        hbox.pack_start(title, expand=True, fill=True)
        hbox.pack_start(vbox, expand=False, fill=True, padding=20)
        hbox.show()

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame.add(hbox)
        frame.show()

        eb = gtk.EventBox()
        eb.add(frame)
        eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))
        eb.show()

        self.dia.vbox.pack_start(eb, expand=False, fill=True, padding=3)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_placement(gtk.CORNER_TOP_LEFT)
        scroll.set_shadow_type(gtk.SHADOW_NONE)
        scroll.show()
        self.dia.vbox.pack_start(scroll, expand=True, fill=True)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.show()
        scroll.add(viewport)

        self.screen.widget.show()
        viewport.add(self.screen.widget)

        i, j = self.screen.screen_container.size_get()
        viewport.set_size_request(i, j + 30)
        self.dia.show()
        self.screen.current_view.set_cursor()
        self.screen.display()

    def message_info(self, message, color='red'):
        if message:
            self.info_label.set_label(message)
            self.eb_info.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(
                COLOR_SCHEMES.get(color, 'white')))
            self.eb_info.show_all()
        else:
            self.info_label.set_label('')
            self.eb_info.hide()

    def run(self):
        while True:
            res = self.dia.run()
            if res == gtk.RESPONSE_OK:
                if self.screen.save_current():
                    return (True, (self.screen.current_model.id,
                        self.screen.current_model.rec_name()))
                else:
                    self.screen.display()
            else:
                break
        return (False, False)

    def destroy(self):
        self.window.present()
        self.screen.destroy()
        self.dia.destroy()

class Many2One(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        if attrs is None:
            attrs = {}
        WidgetInterface.__init__(self, window, parent, model, attrs)

        self.widget = gtk.HBox(spacing=0)
        self.widget.set_property('sensitive', True)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())

        self.wid_text = gtk.Entry()
        self.wid_text.set_property('width-chars', 13)
        self.wid_text.set_property('activates_default', True)
        self.wid_text.connect_after('key_press_event', self.sig_key_press)
        self.wid_text.connect('populate-popup', self._populate_popup)
        self.wid_text.connect_after('changed', self.sig_changed)
        self.changed = True
        self.wid_text.connect_after('activate', self.sig_activate)
        self.wid_text.connect_after('focus-out-event',
                        self.sig_activate)
        self.focus_out = True
        self.widget.pack_start(self.wid_text, expand=True, fill=True)

        self.but_open = gtk.Button()
        img_find = gtk.Image()
        img_find.set_from_stock('tryton-find', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_open.set_image(img_find)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        self.but_open.connect('clicked', self.sig_edit)
        self.but_open.set_alignment(0.5, 0.5)
        self.widget.pack_start(self.but_open, expand=False, fill=False)

        self.but_new = gtk.Button()
        img_new = gtk.Image()
        img_new.set_from_stock('tryton-new', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_new.set_image(img_new)
        self.but_new.set_relief(gtk.RELIEF_NONE)
        self.but_new.connect('clicked', self.sig_new)
        self.but_new.set_alignment(0.5, 0.5)
        self.widget.pack_start(self.but_new, expand=False, fill=False)

        self.widget.set_focus_chain([self.wid_text])

        self.tooltips = common.Tooltips()
        self.tooltips.set_tip(self.but_new, _('Create a new record'))
        self.tooltips.set_tip(self.but_open, _('Open a record'))
        self.tooltips.enable()

        self._readonly = False
        self.model_type = attrs['relation']

        self.completion = gtk.EntryCompletion()
        self.liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        if attrs.get('completion', False):
            try:
                result = rpc.execute('model', self.attrs['relation'],
                        'search_read', [], 0, None, None, rpc.CONTEXT,
                        ['rec_name'])
                names = [(x['id'], x['rec_name']) for x in result]
            except Exception, exception:
                common.process_exception(exception, self._window)
                names = []
            if names:
                self.load_completion(names)

    def grab_focus(self):
        return self.wid_text.grab_focus()

    def _focus_out(self):
        return WidgetInterface._focus_out(self)

    def _focus_in(self):
        return WidgetInterface._focus_in(self)

    def load_completion(self, names):
        self.completion.set_match_func(self.match_func, None)
        self.completion.connect("match-selected", self.on_completion_match)
        self.wid_text.set_completion(self.completion)
        self.completion.set_model(self.liststore)
        self.completion.set_text_column(1)
        for object_id, name in names:
            self.liststore.append([object_id, name])

    def match_func(self, completion, key_string, iter, data):
        model = self.completion.get_model()
        modelstr = model[iter][1].lower()
        return modelstr.startswith(key_string)

    def on_completion_match(self, completion, model, iter):
        self._view.modelfield.set_client(self._view.model, int(model[iter][0]))
        self.display(self._view.model, self._view.modelfield)
        return True

    def _readonly_set(self, value):
        self._readonly = value
        self.wid_text.set_editable(not value)
        self.but_new.set_sensitive(not value)
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.wid_text])

    def _color_widget(self):
        return self.wid_text

    def sig_activate(self, widget, event=None, key_press=False):
        if not self.focus_out:
            return
        if not self._view.modelfield:
            return
        self.changed = False
        value = self._view.modelfield.get(self._view.model)

        self.focus_out = False
        if not value:
            if not self._readonly and (self.wid_text.get_text() or \
                    (self._view.modelfield.get_state_attrs(
                        self._view.model)['required']) and key_press):
                domain = self._view.modelfield.domain_get(self._view.model)
                context = rpc.CONTEXT.copy()
                context.update(self._view.modelfield.context_get(self._view.model))
                self.wid_text.grab_focus()

                try:
                    ids = rpc.execute('model', self.attrs['relation'],
                            'search',
                            [('rec_name', 'ilike', self.wid_text.get_text()),
                                domain],
                            0, _LIMIT, None, context)
                except Exception, exception:
                    self.focus_out = True
                    common.process_exception(exception, self._window)
                    self.changed = True
                    return False
                if len(ids)==1:
                    self._view.modelfield.set_client(self._view.model, ids[0],
                            force_change=True)
                    self.focus_out = True
                    self.display(self._view.model, self._view.modelfield)
                    return True

                win = WinSearch(self.attrs['relation'], sel_multi=False,
                        ids=ids, context=context, domain=domain,
                        parent=self._window,
                        views_preload=self.attrs.get('views', {}))
                ids = win.run()
                if ids:
                    self._view.modelfield.set_client(self._view.model, ids[0],
                            force_change=True)
                    self.focus_out = True
                    self.display(self._view.model, self._view.modelfield)
                    return True
                else:
                    self.focus_out = True
                    self.display(self._view.model, self._view.modelfield)
                    return False
        self.focus_out = True
        self.display(self._view.model, self._view.modelfield)
        self.changed = True
        return True

    def sig_new(self, *args):
        self.focus_out = False
        domain = self._view.modelfield.domain_get(self._view.model)
        context = self._view.modelfield.context_get(self._view.model)
        dia = Dialog(self.attrs['relation'], attrs=self.attrs,
                window=self._window, domain=domain, context=context)
        res, value = dia.run()
        if res:
            self._view.modelfield.set_client(self._view.model, value)
            self.display(self._view.model, self._view.modelfield)
        dia.destroy()
        self.focus_out = True

    def sig_edit(self, widget):
        self.changed = False
        value = self._view.modelfield.get(self._view.model)
        self.focus_out = False
        if value:
            domain = self._view.modelfield.domain_get(self._view.model)
            context = self._view.modelfield.context_get(self._view.model)
            dia = Dialog(self.attrs['relation'],
                    self._view.modelfield.get(self._view.model),
                    attrs=self.attrs, window=self._window, domain=domain,
                    context=context)
            res, value = dia.run()
            if res:
                self._view.modelfield.set_client(self._view.model, value,
                        force_change=True)
            dia.destroy()
        else:
            if not self._readonly:
                domain = self._view.modelfield.domain_get(self._view.model)
                context = rpc.CONTEXT.copy()
                context.update(self._view.modelfield.context_get(self._view.model))
                self.wid_text.grab_focus()

                try:
                    ids = rpc.execute('model', self.attrs['relation'],
                            'search',
                            [('rec_name', 'ilike', self.wid_text.get_text()),
                                domain],
                            0, _LIMIT, None, context)
                except Exception, exception:
                    self.focus_out = True
                    common.process_exception(exception, self._window)
                    self.changed = True
                    return False
                if ids and len(ids)==1:
                    self._view.modelfield.set_client(self._view.model, ids[0],
                            force_change=True)
                    self.focus_out = True
                    self.display(self._view.model, self._view.modelfield)
                    return True

                win = WinSearch(self.attrs['relation'], sel_multi=False,
                        ids=ids, context=context,
                        domain=domain, parent=self._window,
                        views_preload=self.attrs.get('views', {}))
                ids = win.run()
                if ids:
                    self._view.modelfield.set_client(self._view.model, ids[0],
                            force_change=True)
        self.focus_out = True
        self.display(self._view.model, self._view.modelfield)
        self.changed = True

    def sig_key_press(self, widget, event, *args):
        editable = self.wid_text.get_editable()
        if event.keyval == gtk.keysyms.F3 and editable:
            self.sig_new(widget, event)
            return True
        elif event.keyval == gtk.keysyms.F2:
            self.sig_edit(widget)
            return True
        elif event.keyval in (gtk.keysyms.Tab, gtk.keysyms.Return) and editable:
            return not self.sig_activate(widget, event, key_press=True)
        return False

    def sig_changed(self, *args):
        if not self.changed:
            return False
        if self._view.modelfield.get(self._view.model):
            self._view.modelfield.set_client(self._view.model, False)
            self.display(self._view.model, self._view.modelfield)
        return False

    def set_value(self, model, model_field):
        pass # No update of the model, the model is updated in real time !

    def display(self, model, model_field):
        self.changed = False
        if not model_field:
            self.wid_text.set_text('')
            self.changed = True
            return False
        WidgetInterface.display(self, model, model_field)
        res = model_field.get_client(model)
        self.wid_text.set_text((res and str(res)) or '')
        img = gtk.Image()
        if res:
            img.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
            self.but_open.set_image(img)
            self.tooltips.set_tip(self.but_open, _('Open a record'))
        else:
            img.set_from_stock('tryton-find', gtk.ICON_SIZE_SMALL_TOOLBAR)
            self.but_open.set_image(img)
            self.tooltips.set_tip(self.but_open, _('Search a record'))
        self.changed = True

    def _populate_popup(self, widget, menu):
        value = self._view.modelfield.get(self._view.model)
        ir_action_keyword = RPCProxy('ir.action.keyword')
        relates = ir_action_keyword.get_keyword('form_relate',
                (self.model_type, 0), rpc.CONTEXT)
        menu_entries = []
        menu_entries.append((None, None, None))
        menu_entries += self._menu_entries
        menu_entries.append((None, None, None))
        menu_entries.append((_('Actions'),
            lambda x: self.click_and_action('form_action'),0))
        menu_entries.append((_('Reports'),
            lambda x: self.click_and_action('form_print'),0))
        menu_entries.append((None, None, None))
        for relate in relates:
            relate['string'] = relate['name']
            fct = lambda action: lambda x: self.click_and_relate(action)
            menu_entries.append(
                    ('... ' + relate['name'], fct(relate), 0))

        for stock_id, callback, sensitivity in menu_entries:
            if stock_id:
                item = gtk.ImageMenuItem(stock_id)
                if callback:
                    item.connect("activate", callback)
                item.set_sensitive(bool(sensitivity or value))
            else:
                item = gtk.SeparatorMenuItem()
            item.show()
            menu.append(item)
        return True

    def click_and_relate(self, action):
        data = {}
        context = {}
        act = action.copy()
        obj_id = self._view.modelfield.get(self._view.model)
        if not obj_id:
            common.message(_('You must select a record to use the relation!'),
                    self._window)
            return False
        screen = Screen(self.attrs['relation'], self._window)
        screen.load([obj_id])
        act['domain'] = screen.current_model.expr_eval(act.get('domain', []),
                check_load=False)
        act['context'] = str(screen.current_model.expr_eval(
            act.get('context', {}), check_load=False))
        data['model'] = self.model_type
        data['id'] = obj_id
        data['ids'] = [obj_id]
        return Action._exec_action(act, self._window, data, context)

    def click_and_action(self, atype):
        obj_id = self._view.modelfield.get(self._view.model)
        return Action.exec_keyword(atype, self._window, {
            'model': self.model_type,
            'id': obj_id or False,
            'ids': [obj_id],
            }, alwaysask=True)
