import gobject
import gtk
import gettext
from interface import WidgetInterface
import tryton.common as common
from tryton.gui.window.view_form.screen import Screen
from tryton.gui.window.win_search import win_search
import tryton.rpc as rpc
from tryton.action import Action

_ = gettext.gettext


class Dialog(object):

    def __init__(self, model, obj_id=None, attrs=None, domain=None,
            context=None, window=None):
        if attrs is None:
            attrs = {}
        if domain is None:
            domain = []
        if context is None:
            context = {}

        self.dia = gtk.Dialog(_('Tryton - Link'), window,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.window = window
        if ('string' in attrs) and attrs['string']:
            self.dia.set_title(self.dia.get_title() + ' - ' + attrs['string'])
        self.dia.set_property('default-width', 760)
        self.dia.set_property('default-height', 500)
        self.dia.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dia.set_icon(common.TINYERP_ICON)

        self.accel_group = gtk.AccelGroup()
        self.dia.add_accel_group(self.accel_group)

        self.but_cancel = self.dia.add_button(gtk.STOCK_CANCEL,
                gtk.RESPONSE_CANCEL)
        self.but_cancel.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Escape, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        self.but_ok = self.dia.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.but_ok.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Return, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_placement(gtk.CORNER_TOP_LEFT)
        scroll.set_shadow_type(gtk.SHADOW_NONE)
        self.dia.vbox.pack_start(scroll, expand=True, fill=True)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        scroll.add(viewport)

        self.screen = Screen(model, domain=domain, context=context,
                window=self.dia, view_type=['form'])
        if obj_id:
            self.screen.load([obj_id])
        else:
            self.screen.new()
        viewport.add(self.screen.widget)
        i, j = self.screen.screen_container.size_get()
        viewport.set_size_request(i, j + 30)
        self.dia.show_all()
        self.screen.display()

    def run(self):
        while True:
            res = self.dia.run()
            if res == gtk.RESPONSE_OK:
                if self.screen.current_model.validate() \
                        and self.screen.save_current():
                    return (True, self.screen.current_model.name_get())
                else:
                    self.screen.display()
            else:
                break
        return (False, False)

    def destroy(self):
        self.window.present()
        self.dia.destroy()

class Many2One(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        if attrs is None:
            attrs = {}
        WidgetInterface.__init__(self, window, parent, model, attrs)

        self.widget = gtk.HBox(spacing=3)
        self.widget.set_property('sensitive', True)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())

        self.wid_text = gtk.Entry()
        self.wid_text.set_property('width-chars', 13)
        self.wid_text.connect('key_press_event', self.sig_key_press)
        self.wid_text.connect('button_press_event', self._menu_open)
        self.wid_text.connect_after('changed', self.sig_changed)
        self.wid_text.connect_after('activate', self.sig_activate)
        self.wid_text_focus_out_id = \
                self.wid_text.connect_after('focus-out-event',
                        self.sig_activate, True)
        self.widget.pack_start(self.wid_text, expand=True, fill=True)

        self.but_new = gtk.Button()
        img_new = gtk.Image()
        img_new.set_from_stock('gtk-new', gtk.ICON_SIZE_BUTTON)
        self.but_new.set_image(img_new)
        self.but_new.set_relief(gtk.RELIEF_NONE)
        self.but_new.connect('clicked', self.sig_new)
        self.but_new.set_alignment(0.5, 0.5)
        self.but_new.set_property('can-focus', False)
        self.widget.pack_start(self.but_new, expand=False, fill=False)

        self.but_open = gtk.Button()
        img_find = gtk.Image()
        img_find.set_from_stock('gtk-find', gtk.ICON_SIZE_BUTTON)
        img_open = gtk.Image()
        img_open.set_from_stock('gtk-open', gtk.ICON_SIZE_BUTTON)
        self.but_open.set_image(img_find)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        self.but_open.connect('clicked', self.sig_edit)
        self.but_open.set_alignment(0.5, 0.5)
        self.but_open.set_property('can-focus', False)
        self.widget.pack_start(self.but_open, padding=2, expand=False,
                fill=False)

        self.tooltips = gtk.Tooltips()
        self.tooltips.set_tip(self.but_new, _('Create a new resource'))
        self.tooltips.set_tip(self.but_open, _('Open a resource'))
        self.tooltips.enable()

        self.activate = True
        self._readonly = False
        self.model_type = attrs['relation']
        self._menu_loaded = False
        self._menu_entries = []
        self._menu_entries.append((None, None, None))
        self._menu_entries.append((_('Action'),
            lambda x: self.click_and_action('client_action_multi'),0))
        self._menu_entries.append((_('Report'),
            lambda x: self.click_and_action('client_print_multi'),0))


        self.completion = gtk.EntryCompletion()
        self.liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        if attrs.get('completion', False):
            ids = rpc.session.rpc_exec_auth('/object', 'execute',
                    self.attrs['relation'], 'name_search', '', [], 'ilike', {})
            if ids:
                self.load_completion(ids)

    def _focus_out(self):
        return WidgetInterface._focus_out(self)

    def _focus_in(self):
        return WidgetInterface._focus_in(self)

    def load_completion(self, ids):
        self.completion.set_match_func(self.match_func, None)
        self.completion.connect("match-selected", self.on_completion_match)
        self.wid_text.set_completion(self.completion)
        self.completion.set_model(self.liststore)
        self.completion.set_text_column(0)
        for i, word in enumerate(ids):
            if word[1][0] == '[':
                i = word[1].find(']')
                str1 = word[1][1:i]
                str2 = word[1][i+2:]
                self.liststore.append([("%s %s" % (str1, str2)), str2])
            else:
                self.liststore.append([word[1], word[1]])

    def match_func(self, completion, key_string, iter, data):
        model = self.completion.get_model()
        modelstr = model[iter][0].lower()
        return modelstr.startswith(key_string)

    def on_completion_match(self, completion, model, iter):
        name = model[iter][1]
        domain = self._view.modelfield.domain_get(self._view.model)
        context = self._view.modelfield.context_get(self._view.model)
        ids = rpc.session.rpc_exec_auth('/object', 'execute',
                self.attrs['relation'], 'name_search', name, domain, 'ilike',
                context)
        if len(ids)==1:
            self._view.modelfield.set_client(self._view.model, ids[0])
            self.display(self._view.model, self._view.modelfield)
            self.activate = True
        else:
            win = win_search(self.attrs['relation'], sel_multi=False,
                    ids = [x[0] for x in ids], context=context,
                    domain=domain, window=self._window)
            ids = win.go()
            if ids:
                name = rpc.session.rpc_exec_auth('/object', 'execute',
                        self.attrs['relation'], 'name_get', [ids[0]],
                        rpc.session.context)[0]
                self._view.modelfield.set_client(self._view.model, name)
        return True



    def _readonly_set(self, value):
        self._readonly = value
        self.wid_text.set_editable(not value)
        self.but_new.set_sensitive(not value)

    def _color_widget(self):
        return self.wid_text

    def _menu_sig_pref(self, obj):
        self._menu_sig_default_set()

    def _menu_sig_default(self, obj):
        rpc.session.rpc_exec_auth('/object', 'execute',
                self.attrs['model'], 'default_get', [self.attrs['name']])

    def sig_activate(self, widget, event=None, leave=False):
        self.activate = False
        value = self._view.modelfield.get(self._view.model)

        self.wid_text.disconnect(self.wid_text_focus_out_id)
        if value:
            if not leave:
                domain = self._view.modelfield.domain_get(self._view.model)
                dia = Dialog(self.attrs['relation'],
                        self._view.modelfield.get(self._view.model),
                        attrs=self.attrs, window=self._window, domain=domain)
                res, value = dia.run()
                if res:
                    self._view.modelfield.set_client(self._view.model, value,
                            force_change=True)
                dia.destroy()
        else:
            if not self._readonly and ( self.wid_text.get_text() or not leave):
                domain = self._view.modelfield.domain_get(self._view.model)
                context = self._view.modelfield.context_get(self._view.model)
                self.wid_text.grab_focus()

                ids = rpc.session.rpc_exec_auth('/object', 'execute',
                        self.attrs['relation'], 'name_search',
                        self.wid_text.get_text(), domain, 'ilike', context)
                if len(ids)==1:
                    self._view.modelfield.set_client(self._view.model, ids[0],
                            force_change=True)
                    self.wid_text_focus_out_id = \
                            self.wid_text.connect_after('focus-out-event',
                                    self.sig_activate, True)
                    self.display(self._view.model, self._view.modelfield)
                    self.activate = True
                    return True

                win = win_search(self.attrs['relation'], sel_multi=False,
                        ids = [x[0] for x in ids], context=context,
                        domain=domain, parent=self._window)
                ids = win.go()
                if ids:
                    name = rpc.session.rpc_exec_auth('/object', 'execute',
                            self.attrs['relation'], 'name_get', [ids[0]],
                            rpc.session.context)[0]
                    self._view.modelfield.set_client(self._view.model, name,
                            force_change=True)
        self.wid_text_focus_out_id = \
                self.wid_text.connect_after('focus-out-event',
                        self.sig_activate, True)
        self.display(self._view.model, self._view.modelfield)
        self.activate = True

    def sig_new(self, *args):
        self.wid_text.disconnect(self.wid_text_focus_out_id)
        domain = self._view.modelfield.domain_get(self._view.model)
        dia = Dialog(self.attrs['relation'], attrs=self.attrs,
                window=self._window, domain=domain)
        res, value = dia.run()
        if res:
            self._view.modelfield.set_client(self._view.model, value)
            self.display(self._view.model, self._view.modelfield)
        dia.destroy()
        self.wid_text_focus_out_id = \
                self.wid_text.connect_after('focus-out-event',
                        self.sig_activate, True)
    sig_edit = sig_activate

    def sig_key_press(self, widget, event, *args):
        if event.keyval == gtk.keysyms.F1:
            self.sig_new(widget, event)
        elif event.keyval==gtk.keysyms.F2:
            self.sig_activate(widget, event)
        elif event.keyval  == gtk.keysyms.Tab:
            if self._view.modelfield.get(self._view.model) or \
                    not self.wid_text.get_text():
                return False
            self.sig_activate(widget, event, leave=True)
            return True
        return False

    def sig_changed(self, *args):
        if self.activate:
            if self._view.modelfield.get(self._view.model):
                self._view.modelfield.set_client(self._view.model, False)
                self.display(self._view.model, self._view.modelfield)
        return False

    def set_value(self, model, model_field):
        pass # No update of the model, the model is updated in real time !

    def display(self, model, model_field):
        if not model_field:
            self.activate = False
            self.wid_text.set_text('')
            return False
        WidgetInterface.display(self, model, model_field)
        self.activate = False
        res = model_field.get_client(model)
        self.wid_text.set_text((res and str(res)) or '')
        img = gtk.Image()
        if res:
            img.set_from_stock('gtk-open', gtk.ICON_SIZE_BUTTON)
            self.but_open.set_image(img)
            self.tooltips.set_tip(self.but_open, _('Open a resource'))
        else:
            img.set_from_stock('gtk-find', gtk.ICON_SIZE_BUTTON)
            self.but_open.set_image(img)
            self.tooltips.set_tip(self.but_open, _('Search a resource'))
        self.activate = True

    def _menu_open(self, obj, event):
        if event.button == 3:
            value = self._view.modelfield.get(self._view.model)
            if not self._menu_loaded:
                resrelate = rpc.session.rpc_exec_auth('/object', 'execute',
                        'ir.values', 'get', 'action', 'client_action_relate',
                        [(self.model_type, False)], False, rpc.session.context)
                resrelate = [x[2] for x in resrelate]
                self._menu_entries.append((None, None, None))
                for i in resrelate:
                    i['string'] = i['name']
                    fct = lambda action: lambda x: self.click_and_relate(action)
                    self._menu_entries.append(('... ' + i['name'], fct(i), 0))
            self._menu_loaded = True

            menu = gtk.Menu()
            for stock_id, callback, sensitivity in self._menu_entries:
                if stock_id:
                    item = gtk.ImageMenuItem(stock_id)
                    if callback:
                        item.connect("activate", callback)
                    item.set_sensitive(bool(sensitivity or value))
                else:
                    item = gtk.SeparatorMenuItem()
                item.show()
                menu.append(item)
            menu.popup(None, None, None, event.button, event.time)
            return True
        return False

    def click_and_relate(self, action):
        data = {}
        context = {}
        act = action.copy()
        obj_id = self._view.modelfield.get(self._view.model)
        if not obj_id:
            common.message(_('You must select a record to use the relation !'))
            return False
        screen = Screen(self.attrs['relation'])
        screen.load([obj_id])
        act['domain'] = screen.current_model.expr_eval(act['domain'],
                check_load=False)
        act['context'] = str(screen.current_model.expr_eval(act['context'],
            check_load=False))
        return Action._exec_action(act, data, context)

    def click_and_action(self, atype):
        obj_id = self._view.modelfield.get(self._view.model)
        return Action.exec_keyword(atype, {'model': self.model_type,
            'id': obj_id or False, 'ids': [obj_id], 'report_type': 'pdf'})
