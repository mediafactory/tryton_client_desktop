import gtk
from xml.parsers import expat
import sys
import gettext

_ = gettext.gettext


class _container(object):

    def __init__(self, max_width):
        self.cont = []
        self.max_width = max_width
        self.width = {}
        self.count = 0
        self.col = 0

    def new(self, col=8):
        self.col = col+1
        table = gtk.Table(1, col)
        table.set_homogeneous(False)
        table.set_col_spacings(3)
        table.set_row_spacings(0)
        table.set_border_width(1)
        self.cont.append( (table, 1, 0) )

    def get(self):
        return self.cont[-1][0]

    def pop(self):
        return self.cont.pop()[0]

    def newline(self):
        (table, i, j) = self.cont[-1]
        if i > 0:
            self.cont[-1] = (table, 1, j+1)
        table.resize(j + 1, self.col)

    def wid_add(self, widget, length=1, name=None, expand=False, ypadding=0):
        self.count += 1
        (table, i, j) = self.cont[-1]
        if length > self.col:
            length = self.col
        if length + i > self.col:
            self.newline()
            (table, i, j) = self.cont[-1]
        if name:
            vbox = gtk.VBox(homogeneous=False, spacing=1)
            label = gtk.Label(name)
            label.set_alignment(0.0, 0.5)
            vbox.pack_start(label, expand=False)
            vbox.pack_start(widget, expand=expand, fill=True)
            wid = vbox
        else:
            wid = widget
        yopt = False
        if expand:
            yopt = yopt | gtk.EXPAND |gtk.FILL
        table.attach(wid, i, i+length, j, j+1,
                yoptions=yopt, xoptions=gtk.FILL|gtk.EXPAND,
                ypadding=ypadding, xpadding=5)
        self.cont[-1] = (table, i+length, j)
        width = 750
        if widget:
            width = widget.size_request()[0]
        self.width[('%d.%d') % (i, j)] = width
        return wid


class Parse(object):

    def __init__(self, parent, fields, model=''):
        self.fields = fields
        self.parent = parent
        self.model = model
        self.col = 8
        self.focusable = None
        self.add_widget_end = []
        self.container = None
        self.button_param = gtk.Button()
        self.spin_limit = gtk.SpinButton(climb_rate=1, digits=0)
        self.spin_offset = gtk.SpinButton(climb_rate=1, digits=0)
        self.title = 'Form'
        self.notebooks = []
        self.dict_widget = {}
        self.hb_param = None

    def _psr_start(self, name, attrs):

        if name in ('form','tree'):
            self.title = attrs.get('string', self.title)
            self.container.new(self.col)
        elif name == 'field':
            if attrs['name'] in self.fields:
                val  = attrs.get('select', False) \
                        or self.fields[attrs['name']].get('select', False)
                if val:
                    if int(val) <= 1:
                        self.add_widget(attrs, val)
                    else:
                        self.add_widget_end.append((attrs, val))

    def add_widget(self, attrs, val):
        ftype = attrs.get('widget', self.fields[str(attrs['name'])]['type'])
        self.fields[str(attrs['name'])].update(attrs)
        self.fields[str(attrs['name'])]['model']=self.model
        if ftype not in WIDGETS_TYPE:
            return False
        widget_act = WIDGETS_TYPE[ftype][0](str(attrs['name']), self.parent,
                self.fields[attrs['name']])
        if 'string' in self.fields[str(attrs['name'])]:
            label = self.fields[str(attrs['name'])]['string']+' :'
        else:
            label = None
        size = WIDGETS_TYPE[ftype][1]
        if not self.focusable:
            self.focusable = widget_act.widget
        wid = self.container.wid_add(widget_act.widget, size, label,
                int(self.fields[str(attrs['name'])].get('expand',0)))
        if int(val) <= 1:
            wid.show()
        self.dict_widget[str(attrs['name'])] = (widget_act, wid, int(val))

    def add_parameters(self):
        hb_param = gtk.HBox(spacing=3)
        hb_param.pack_start(gtk.Label(_('Limit :')), expand=False, fill=False)

        self.spin_limit.set_numeric(False)
        self.spin_limit.set_adjustment(gtk.Adjustment(value=80, lower=1,
            upper=sys.maxint, step_incr=10, page_incr=100, page_size=100))
        self.spin_limit.set_property('visible', True)

        hb_param.pack_start(self.spin_limit, expand=False, fill=False)

        hb_param.pack_start(gtk.Label(_('Offset :')), expand=False, fill=False)

        self.spin_offset.set_numeric(False)
        self.spin_offset.set_adjustment(gtk.Adjustment(value=0, lower=0,
            upper=sys.maxint, step_incr=80, page_incr=100, page_size=100))

        hb_param.pack_start(self.spin_offset, expand=False, fill=False)

        return hb_param

    def _psr_end(self, name):
        pass

    def _psr_char(self, name):
        pass

    def parse(self, xml_data, max_width):
        psr = expat.ParserCreate()
        psr.StartElementHandler = self._psr_start
        psr.EndElementHandler = self._psr_end
        psr.CharacterDataHandler = self._psr_char
        self.container = _container(max_width)

        psr.Parse(xml_data)
        for i in self.add_widget_end:
            self.add_widget(*i)
        self.add_widget_end = []

        img = gtk.Image()
        img.set_from_stock('gtk-add', gtk.ICON_SIZE_BUTTON)
        self.button_param.set_image(img)
        self.button_param.set_relief(gtk.RELIEF_NONE)
        self.button_param.set_alignment(0.5, 0.5)
        table = self.container.get()
        table.attach(self.button_param, 0, 1, 0, 1,
                yoptions=gtk.FILL, xoptions=gtk.FILL, ypadding=2, xpadding=0)

        self.hb_param = self.container.wid_add(self.add_parameters(), length=8,
                name=_('Parameters :'))


        return (self.dict_widget, self.container.pop())


class Form(object):

    def __init__(self, xml, fields, model=None, parent=None, domain=None,
            call=None):
        if domain is None:
            domain = []
        parser = Parse(parent, fields, model=model)
        self.parent = parent
        self.fields = fields
        self.model = model
        self.parser = parser
        self.call = call
        #get the size of the window and the limite / decalage Hbox element
        width = 640
        if self.parent:
            width = self.parent.size_request()[0]
        (self.widgets, self.widget) = parser.parse(xml, width)
        self.widget.show_all()
        self.hb_param = parser.hb_param
        self.button_param = parser.button_param
        self.button_param.connect('clicked', self.toggle)
        self.spin_limit = parser.spin_limit
        self.spin_limit.connect('value-changed', self.limit_changed)
        self.spin_limit.set_activates_default(True)
        self.spin_offset = parser.spin_offset
        self.spin_offset.set_activates_default(True)
        self.focusable = parser.focusable
        self.id = 0
        self.name = parser.title
        self._hide = True
        self.hide()
        for i in domain:
            if i[0] in self.widgets:
                if i[1] == '=':
                    self.widgets[i[0]][0]._readonly_set(True)
        for i in self.widgets.values():
            i[0].sig_activate(self.sig_activate)
        self.spin_limit.connect_after('activate', self.sig_activate)
        self.spin_offset.connect_after('activate', self.sig_activate)

    def clear(self):
        self.id = 0
        for i in self.widgets.values():
            i[0].clear()

    def show(self):
        for i, widget, value in  self.widgets.values():
            if value >= 2:
                widget.show()
        self.hb_param.show()
        self._hide = False

    def hide(self):
        for i, widget, value in  self.widgets.values():
            if value >= 2:
                widget.hide()
        self.hb_param.hide()
        self._hide = True

    def toggle(self, widget):
        img = gtk.Image()
        if self._hide:
            self.show()
            img.set_from_stock('gtk-remove', gtk.ICON_SIZE_BUTTON)
            widget.set_image(img)
        else:
            self.hide()
            img.set_from_stock('gtk-add', gtk.ICON_SIZE_BUTTON)
            widget.set_image(img)

    def limit_changed(self, widget):
        self.spin_offset.set_increments(step=self.spin_limit.get_value(),
                page=100)

    def set_limit(self, value):
        return self.spin_limit.set_value(value)

    def get_limit(self):
        return self.spin_limit.get_value()

    def get_offset(self):
        return self.spin_offset.get_value()

    def sig_activate(self, *args):
        if self.call:
            obj, fct = self.call
            fct(obj)

    def _value_get(self):
        res = []
        for i in self.widgets:
            res += self.widgets[i][0].value
        return res

    def _value_set(self, value):
        for i in value:
            if i in self.widgets:
                self.widgets[i][0].value = value[i]

    value = property(_value_get, _value_set, None,
            _('The content of the form or excpetion if not valid'))

import calendar
import float
import integer
import selection
import char
import checkbox
import reference

WIDGETS_TYPE = {
    'date': (calendar.Calendar, 2),
    'datetime': (calendar.Calendar, 2),
    'float': (float.Float, 2),
    'integer': (integer.Integer, 2),
    'selection': (selection.Selection, 2),
    'many2one_selection': (selection.Selection, 2),
    'char': (char.Char, 2),
    'boolean': (checkbox.CheckBox, 2),
    'reference': (reference.Reference, 2),
    'text': (char.Char, 2),
    'email': (char.Char, 2),
    'url': (char.Char, 2),
    'many2one': (char.Char, 2),
    'one2many': (char.Char, 2),
    'one2many_form': (char.Char, 2),
    'one2many_list': (char.Char, 2),
    'many2many_edit': (char.Char, 2),
    'many2many': (char.Char, 2),
    'callto': (char.Char, 2),
    'sip': (char.Char, 2),
}
