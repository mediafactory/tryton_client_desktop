import gtk
import gettext
import copy
import tryton.rpc as rpc
from tryton.action import Action
from tryton.gui.window.view_form.view.interface import ParserInterface
import tryton.common as common
from tryton.config import CONFIG, TRYTON_ICON

_ = gettext.gettext


class Button(object):

    def __init__(self, attrs=None):
        super(Button, self).__init__()
        self.attrs = attrs or {}
        self.widget = gtk.Button(label=attrs.get('string', _('Unknown')))
        if attrs.get('icon', False):
            try:
                stock = attrs['icon']
                icon = gtk.Image()
                icon.set_from_stock(stock, gtk.ICON_SIZE_BUTTON)
                self.widget.set_image(icon)
            except Exception:
                import logging
                log = logging.getLogger('common')
                log.warning(_('Wrong icon for the button!'))
        self.widget.show()
        self.widget.connect('clicked', self.button_clicked)
        self.form = None #fill later by ViewForm

    def button_clicked(self, widget):
        if not self.form:
            return
        model = self.form.screen.current_model
        self.form.set_value()
        if model.validate():
            obj_id = self.form.screen.save_current()
            if not self.attrs.get('confirm', False) or \
                    common.sur(self.attrs['confirm'], self.form.window):
                button_type = self.attrs.get('type', 'workflow')
                if button_type == 'workflow':
                    args = ('object', 'exec_workflow', self.form.screen.name,
                            self.attrs['name'], obj_id)
                    try:
                        rpc.execute(*args)
                    except Exception, exception:
                        rpc.process_exception(exception, self.form.window,
                                *args)
                elif button_type == 'object':
                    if not obj_id:
                        return
                    args = ('object', 'execute', self.form.screen.name,
                            self.attrs['name'], [obj_id], model.context_get())
                    try:
                        rpc.execute(*args)
                    except Exception, exception:
                        rpc.process_exception(exception, self.form.window,
                                *args)
                elif button_type == 'action':
                    action_id = None
                    args = ('object', 'execute', 'ir.action', 'get_action_id',
                            int(self.attrs['name']), rpc.CONTEXT)
                    try:
                        action_id = rpc.execute(*args)
                    except Exception, exception:
                        action_id = rpc.process_exception(exception, self.form.window,
                                *args)
                    if action_id:
                        Action.execute(action_id, {
                            'model': self.form.screen.name,
                            'id': obj_id or False,
                            'ids': obj_id and [obj_id] or [],
                            })
                else:
                    raise Exception('Unallowed button type')
                self.form.screen.reload()
        else:
            if self.form.screen.form:
                self.form.screen.form.message_state(
                        _('Invalid Form, correct red fields!'))
            self.form.screen.display()

    def state_set(self, values):
        state_changes = self.attrs.get('states', {})
        try:
            if isinstance(state_changes, basestring):
                state_changes = eval(state_changes)
            if 'invisible' in state_changes:
                if eval(state_changes['invisible'], values):
                    self.widget.hide()
                else:
                    self.widget.show()
            else:
                self.widget.show()
            if 'readonly' in state_changes:
                if eval(state_changes['readonly'], values):
                    self.widget.set_sensitive(False)
                else:
                    self.widget.set_sensitive(True)
            else:
                self.widget.set_sensitive(True)
        except:
            self.widget.show()
            self.widget.set_sensitive(True)

class Label(gtk.Label):

    def __init__(self, str=None, attrs=None):
        super(Label, self).__init__(str=str)
        self.attrs = attrs or {}

    def state_set(self, values):
        state_changes = self.attrs.get('states', {})
        try:
            if isinstance(state_changes, basestring):
                state_changes = eval(state_changes)
            if 'invisible' in state_changes:
                if eval(state_changes['invisible'], values):
                    self.hide()
                else:
                    self.show()
            else:
                self.show()
        except:
            self.show()


class VBox(gtk.VBox):

    def __init__(self, homogeneous=False, spacing=0, attrs=None):
        super(VBox, self).__init__(homogeneous, spacing)
        self.attrs = attrs or {}

    def state_set(self, values):
        state_changes = self.attrs.get('states', {})
        try:
            if isinstance(state_changes, basestring):
                state_changes = eval(state_changes)
            if 'invisible' in state_changes:
                if eval(state_changes['invisible'], values):
                    self.hide()
                else:
                    self.show()
            else:
                self.show()
        except:
            self.show()

class Image(gtk.Image):

    def __init__(self, attrs=None):
        super(Image, self).__init__()
        self.attrs = attrs or {}

    def state_set(self, values):
        state_changes = self.attrs.get('states', {})
        try:
            if isinstance(state_changes, basestring):
                state_changes = eval(state_changes)
            if 'invisible' in state_changes:
                if eval(state_changes['invisible'], values):
                    self.hide()
                else:
                    self.show()
            else:
                self.show()
        except:
            self.show()


class _container(object):
    def __init__(self, tooltips):
        self.cont = []
        self.col = []
        self.tooltips = tooltips
        self.trans_box = []

    def new(self, col=4):
        table = gtk.Table(1, col)
        table.set_homogeneous(False)
        table.set_col_spacings(3)
        table.set_row_spacings(0)
        table.set_border_width(1)
        self.cont.append( (table, 0, 0) )
        self.col.append( col )

    def get(self):
        return self.cont[-1][0]

    def pop(self):
        table = self.cont.pop()[0]
        self.col.pop()
        return table

    def newline(self):
        (table, width, height) = self.cont[-1]
        if width > 0:
            self.cont[-1] = (table, 0, height + 1)
        table.resize(height + 1, self.col[-1])

    def wid_add(self, widget, name='', expand=False, ypadding=2, rowspan=1,
            colspan=1, translate=False, fname=None, help_tip=False, fill=False,
            xexpand=True, xfill=True):
        (table, width, height) = self.cont[-1]
        if colspan > self.col[-1]:
            colspan = self.col[-1]
        if colspan + width > self.col[-1]:
            self.newline()
            (table, width, height) = self.cont[-1]
        yopt = False
        if expand:
            yopt = yopt | gtk.EXPAND
        if fill:
            yopt = yopt | gtk.FILL
        xopt = False
        if xexpand:
            xopt = xopt | gtk.EXPAND
        if xfill:
            xopt = xopt | gtk.FILL
        widget = widget
        if help_tip:
            self.tooltips.set_tip(widget, help_tip)
            self.tooltips.enable()
        if translate and hasattr(widget, 'pack_start'):
            button = gtk.Button()
            img = gtk.Image()
            img.set_from_stock('gtk-preferences', gtk.ICON_SIZE_BUTTON)
            button.set_image(img)
            button.set_relief(gtk.RELIEF_NONE)
            self.trans_box.append((button, name, fname, widget.get_children()[0]))
            widget.pack_start(button, fill=False, expand=False)
        widget.show_all()
        table.attach(widget, width, width + colspan,
                height, height + rowspan,
                yoptions=yopt, ypadding=ypadding,
                xoptions=xopt, xpadding=0)
        self.cont[-1] = (table, width + colspan, height)
        wid_list = table.get_children()
        wid_list.reverse()
        table.set_focus_chain(wid_list)

    def empty_add(self, colspan=1):
        (table, width, height) = self.cont[-1]
        if colspan > self.col[-1]:
            colspan = self.col[-1]
        if colspan + width > self.col[-1]:
            self.newline()
            (table, width, height) = self.cont[-1]
        self.cont[-1] = (table, width + colspan, height)


class ParserForm(ParserInterface):

    def parse(self, model, root_node, fields, notebook=None, paned=None,
            tooltips=None):
        dict_widget = {}
        button_list = []
        notebook_list = []
        attrs = common.node_attributes(root_node)
        on_write = attrs.get('on_write', '')
        if not tooltips:
            tooltips = gtk.Tooltips()
        container = _container(tooltips)
        container.new(col=int(attrs.get('col', 4)))
        cursor_widget = attrs.get('cursor')

        if not self.title:
            self.title = attrs.get('string', 'Unknown')

        for node in root_node.childNodes:
            if not node.nodeType == node.ELEMENT_NODE:
                continue
            attrs = common.node_attributes(node)
            if not cursor_widget:
                cursor_widget = attrs.get('name')
            if node.localName == 'image':
                icon = Image(attrs)
                button_list.append(icon)
                icon.set_from_stock(attrs['name'], gtk.ICON_SIZE_DIALOG)
                container.wid_add(icon, colspan=int(attrs.get('colspan', 1)),
                        expand=int(attrs.get('expand',0)), ypadding=10,
                        help_tip=attrs.get('help', False),
                        fill=int(attrs.get('fill', 0)))
            elif node.localName == 'separator':
                text = attrs.get('string', '')
                if 'string' in attrs or 'name' in attrs:
                    if not text:
                        if 'name' in attrs and attrs['name'] in fields:
                            if 'states' in fields[attrs['name']]:
                                attrs['states'] = \
                                        fields[attrs['name']]['states']
                            text = fields[attrs['name']]['string']
                vbox = VBox(attrs=attrs)
                button_list.append(vbox)
                if text:
                    label = gtk.Label(text)
                    label.set_use_markup(True)
                    label.set_alignment(float(attrs.get('align', 0.0)), 0.5)
                    vbox.pack_start(label)
                vbox.pack_start(gtk.HSeparator())
                container.wid_add(vbox, colspan=int(attrs.get('colspan', 1)),
                        expand=int(attrs.get('expand', 0)),
                        ypadding=10, help_tip=attrs.get('help', False),
                        fill=int(attrs.get('fill', 0)))
            elif node.localName == 'label':
                text = attrs.get('string', '')
                if not text:
                    if 'name' in attrs and attrs['name'] in fields:
                        if 'states' in fields[attrs['name']]:
                            attrs['states'] = fields[attrs['name']]['states']
                        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
                            text = _(':') + fields[attrs['name']]['string']
                        else:
                            text = fields[attrs['name']]['string'] + _(':')
                        if 'align' not in attrs:
                            attrs['align'] = 1.0
                    else:
                        for node in node.childNodes:
                            if node.nodeType == node.TEXT_NODE:
                                text += node.data
                            else:
                                text += node.toxml()
                if not text:
                    container.empty_add(int(attrs.get('colspan', 1)))
                    continue
                label = Label(text, attrs)
                button_list.append(label)
                label.set_use_markup(True)
                if 'align' in attrs:
                    label.set_alignment(float(attrs['align'] or 0.0), 0.5)
                label.set_angle(int(attrs.get('angle', 0)))
                expand = False
                if 'expand' in attrs:
                    expand = bool(eval(attrs['expand']))
                fill = False
                if 'fill' in attrs:
                    fill = bool(eval(attrs['fill']))
                xexpand = False
                if 'xexpand' in attrs:
                    xexpand = bool(eval(attrs['xexpand']))
                xfill = True
                if 'xfill' in attrs:
                    xfill = bool(eval(attrs['xfill']))
                container.wid_add(label,
                        colspan=int(attrs.get('colspan', 1)),
                        expand=expand, help_tip=attrs.get('help', False),
                        fill=fill, xexpand=xexpand, xfill=xfill)

            elif node.localName == 'newline':
                container.newline()

            elif node.localName == 'button':
                button = Button(attrs)
                button_list.append(button)
                container.wid_add(button.widget,
                        colspan=int(attrs.get('colspan', 1)),
                        help_tip=attrs.get('help', False))

            elif node.localName == 'notebook':
                notebook = gtk.Notebook()
                notebook_list.append(notebook)
                if attrs and 'tabpos' in attrs:
                    pos = {'up':gtk.POS_TOP,
                        'down':gtk.POS_BOTTOM,
                        'left':gtk.POS_LEFT,
                        'right':gtk.POS_RIGHT
                    }[attrs['tabpos']]
                else:
                    if CONFIG['client.form_tab'] == 'top':
                        pos = gtk.POS_TOP
                    elif CONFIG['client.form_tab'] == 'left':
                        pos = gtk.POS_LEFT
                    elif CONFIG['client.form_tab'] == 'right':
                        pos = gtk.POS_RIGHT
                    elif CONFIG['client.form_tab'] == 'bottom':
                        pos = gtk.POS_BOTTOM
                notebook.set_tab_pos(pos)
                notebook.set_border_width(3)
                container.wid_add(notebook, colspan=attrs.get('colspan', 4),
                        expand=True, fill=True)
                widget, widgets, buttons, on_write, notebook_list2, cursor_widget2 = \
                        self.parse(model, node, fields, notebook,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)

            elif node.localName == 'page':
                if attrs and 'angle' in attrs:
                    angle = int(attrs['angle'])
                else:
                    angle = int(CONFIG['client.form_tab_orientation'])
                label = gtk.Label(attrs.get('string','No String Attr.'))
                label.set_angle(angle)
                widget, widgets, buttons, on_write, notebook_list2, cursor_widget2 = \
                        self.parse(model, node, fields, notebook,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)
                notebook.append_page(widget, label)

            elif node.localName == 'field':
                name = str(attrs['name'])
                del attrs['name']
                if name not in fields:
                    container.empty_add(int(attrs.get('colspan', 1)))
                    continue
                ftype = attrs.get('widget', fields[name]['type'])
                fields[name].update(attrs)
                fields[name]['model'] = model
                if not ftype in WIDGETS_TYPE:
                    container.empty_add(int(attrs.get('colspan', 1)))
                    continue

                fields[name]['name'] = name
                if 'saves' in attrs:
                    fields[name]['saves'] = attrs['saves']
                widget_act = WIDGETS_TYPE[ftype][0](self.window, self.parent,
                        model, fields[name])
                dict_widget[name] = widget_act
                size = int(attrs.get('colspan', WIDGETS_TYPE[ftype][1]))
                expand = WIDGETS_TYPE[ftype][2]
                if 'expand' in attrs:
                    expand = bool(eval(attrs['expand']))
                fill = WIDGETS_TYPE[ftype][3]
                if 'fill' in attrs:
                    fill = bool(eval(attrs['fill']))
                xexpand = True
                if 'xexpand' in attrs:
                    xexpand = bool(eval(attrs['xexpand']))
                xfill = True
                if 'xfill' in attrs:
                    xfill = bool(eval(attrs['xfill']))
                hlp = fields[name].get('help', attrs.get('help', False))
                if attrs.get('height', False) or attrs.get('width', False):
                    widget_act.widget.set_size_request(
                            int(attrs.get('width', -1)),
                            int(attrs.get('height', -1)))
                container.wid_add(widget_act.widget, fields[name]['string'],
                        expand, translate=fields[name].get('translate', False),
                        colspan=size, fname=name, help_tip=hlp, fill=fill,
                        xexpand=xexpand, xfill=xfill)

            elif node.localName == 'group':
                widget, widgets, buttons, on_write, notebook_list2, cursor_widget2 = \
                        self.parse(model, node, fields, tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                dict_widget.update(widgets)
                button_list += buttons
                if attrs.get('string', None):
                    frame = gtk.Frame(attrs['string'])
                    frame.add(widget)
                else:
                    frame = widget
                container.wid_add(frame, colspan=int(attrs.get('colspan', 1)),
                        expand=int(attrs.get('expand', 0)),
                        rowspan=int(attrs.get('rowspan', 1)), ypadding=0,
                        fill=int(attrs.get('fill', 1)))
            elif node.localName == 'hpaned':
                hpaned = gtk.HPaned()
                container.wid_add(hpaned, colspan=int(attrs.get('colspan', 4)),
                        expand=True, fill=True)
                widget, widgets, buttons, on_write, notebook_list2, cursor_widget2 = \
                        self.parse(model, node, fields, paned=hpaned,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)
                if 'position' in attrs:
                    hpaned.set_position(int(attrs['position']))
            elif node.localName == 'vpaned':
                vpaned = gtk.VPaned()
                container.wid_add(vpaned, colspan=int(attrs.get('colspan', 4)),
                        expand=True, fill=True)
                widget, widgets, buttons, on_write, notebook_list, cursor_widget2 = \
                        self.parse(model, node, fields, paned=vpaned,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)
                if 'position' in attrs:
                    vpaned.set_position(int(attrs['position']))
            elif node.localName == 'child1':
                widget, widgets, buttons, on_write, notebook_list2, cursor_widget2 = \
                        self.parse(model, node, fields, paned=paned,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)
                paned.pack1(widget, resize=True, shrink=True)
            elif node.localName == 'child2':
                widget, widgets, buttons, on_write, notebook_list, cursor_widget2 = \
                        self.parse(model, node, fields, paned=paned,
                                tooltips=tooltips)
                if not cursor_widget:
                    cursor_widget = cursor_widget2
                notebook_list.extend(notebook_list2)
                button_list += buttons
                dict_widget.update(widgets)
                paned.pack2(widget, resize=True, shrink=True)
        for (button, src, name, widget) in container.trans_box:
            button.connect('clicked', self.translate, model, name,
                    src, widget)
        return container.pop(), dict_widget, button_list, on_write, \
                notebook_list, cursor_widget

    def translate(self, widget, model, name, src, widget_entry):
        obj_id = self.screen.current_model.id
        if not obj_id:
            common.message(
                    _('You need to save the record before adding translations!'),
                    parent=self.window)
            return False

        obj_id = self.screen.current_model.save(force_reload=False)
        try:
            lang_ids = rpc.execute('object', 'execute', 'ir.lang',
                    'search', [('translatable','=','1')])
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return False

        if not lang_ids:
            common.message(_('No other language available!'),
                    parent=self.window)
            return False
        try:
            langs = rpc.execute('object', 'execute', 'ir.lang',
                    'read', lang_ids, ['code', 'name'])
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return False

        code = rpc.CONTEXT.get('language', 'en_US')

        #change 'en' to false for context
        def adapt_context(val):
            if val == 'en_US':
                return False
            else:
                return val

        #widget accessor functions
        def value_get(widget):
            if type(widget) == type(gtk.Entry()):
                return widget.get_text()
            elif type(widget.child) == type(gtk.TextView()):
                buf = widget.child.get_buffer()
                iter_start = buf.get_start_iter()
                iter_end = buf.get_end_iter()
                return buf.get_text(iter_start, iter_end, False)
            else:
                return None

        def value_set(widget, value):
            if type(widget) == type(gtk.Entry()):
                widget.set_text(value)
            elif type(widget.child) == type(gtk.TextView()):
                if value == False:
                    value = ''
                buf = widget.child.get_buffer()
                buf.delete(buf.get_start_iter(), buf.get_end_iter())
                iter_start = buf.get_start_iter()
                buf.insert(iter_start, value)

        def widget_duplicate(widget):
            if type(widget) == type(gtk.Entry()):
                entry = gtk.Entry()
                entry.set_property('activates_default', True)
                entry.set_max_length(widget.get_max_length())
                entry.set_width_chars(widget.get_width_chars())
                return entry, gtk.FILL
            elif type(widget.child) == type(gtk.TextView()):
                textview = gtk.TextView()
                textview.set_wrap_mode(gtk.WRAP_WORD)
                scrolledwindow = gtk.ScrolledWindow()
                scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                        gtk.POLICY_ALWAYS)
                scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
                scrolledwindow.set_size_request(-1, 80)
                scrolledwindow.add(textview)
                textview.set_accepts_tab(False)
                return scrolledwindow, gtk.FILL | gtk.EXPAND
            else:
                return None, False


        win = gtk.Dialog(_('Add Translation'), self.window,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        win.vbox.set_spacing(5)
        win.set_property('default-width', 600)
        win.set_property('default-height', 400)
        win.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        win.set_icon(TRYTON_ICON)

        accel_group = gtk.AccelGroup()
        win.add_accel_group(accel_group)

        but_cancel = win.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        but_cancel.add_accelerator('clicked', accel_group, gtk.keysyms.Escape,
                gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        but_ok = win.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        but_ok.add_accelerator('clicked', accel_group, gtk.keysyms.Return,
                gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        vbox = gtk.VBox(spacing=5)

        entries_list = []
        table = gtk.Table(len(langs), 2)
        table.set_homogeneous(False)
        table.set_col_spacings(3)
        table.set_row_spacings(0)
        table.set_border_width(1)
        i = 0
        for lang in langs:
            context = copy.copy(rpc.CONTEXT)
            context['language'] = adapt_context(lang['code'])
            try:
                val = rpc.execute('/object', 'execute', model,
                        'read', [obj_id], [name], context)
            except Exception, exception:
                rpc.process_exception(exception, self.window)
                return False
            val = val[0]
            if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
                label = gtk.Label(_(':') + lang['name'])
            else:
                label = gtk.Label(lang['name'] + _(':'))
            label.set_alignment(1.0, 0.5)
            (entry, yoptions) = widget_duplicate(widget_entry)

            hbox = gtk.HBox(homogeneous=False)
            if code == lang['code']:
                value_set(entry, value_get(widget_entry))
            else:
                value_set(entry, val[name])

            entries_list.append((val['id'], lang['code'], entry))
            table.attach(label, 0, 1, i, i+1, yoptions=False, xoptions=gtk.FILL,
                    ypadding=2, xpadding=5)
            table.attach(entry, 1, 2, i, i+1, yoptions=yoptions,
                    ypadding=2, xpadding=5)
            i += 1

        vbox.pack_start(table)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.add(vbox)
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        scrolledwindow.add(viewport)
        win.vbox.add(scrolledwindow)
        win.show_all()

        data = []
        response = win.run()
        if response == gtk.RESPONSE_OK:
            to_save = [(x[0], x[1], value_get(x[2])) for x in entries_list]
            while to_save != []:
                new_val = {}
                new_val['id'], new_val['code'], new_val['value'] = \
                        to_save.pop()
                #update form field
                if new_val['code'] == code:
                    value_set(widget_entry, new_val['value'])
                context = copy.copy(rpc.CONTEXT)
                context['language'] = adapt_context(new_val['code'])
                args = ('object', 'execute', model, 'write', [obj_id],
                        {str(name):  new_val['value']}, context)
                try:
                    rpc.execute(*args)
                except Exception, exception:
                    rpc.process_exception(exception, self.window, *args)
        if response == gtk.RESPONSE_CANCEL:
            self.window.present()
            win.destroy()
            return
        self.screen.current_model.reload()
        self.window.present()
        win.destroy()
        return True

from calendar import Calendar, DateTime
from float import Float
from integer import Integer
from selection import Selection
from char import Char, Sha
from float_time import FloatTime
from checkbox import CheckBox
from reference import Reference
from binary import Binary
from textbox import TextBox
from one2many import One2Many
from many2many import Many2Many
from many2one import Many2One
from url import Email, URL, CallTo, SIP
from image import Image as Image2


WIDGETS_TYPE = {
    'date': (Calendar, 1, False, False),
    'datetime': (DateTime, 1, False, False),
    'float': (Float, 1, False, False),
    'numeric': (Float, 1, False, False),
    'integer': (Integer, 1, False, False),
    'selection': (Selection, 1, False, False),
    'char': (Char, 1, False, False),
    'sha': (Sha, 1, False, False),
    'float_time': (FloatTime, 1, False, False),
    'boolean': (CheckBox, 1, False, False),
    'reference': (Reference, 1, False, False),
    'binary': (Binary, 1, False, False),
    'text': (TextBox, 1, True, True),
    'one2many': (One2Many, 1, True, True),
    'many2many': (Many2Many, 1, True, True),
    'many2one': (Many2One, 1, False, False),
    'email' : (Email, 1, False, False),
    'url' : (URL, 1, False, False),
    'callto' : (CallTo, 1, False, False),
    'sip' : (SIP, 1, False, False),
    'image' : (Image2, 1, False, False),
}
