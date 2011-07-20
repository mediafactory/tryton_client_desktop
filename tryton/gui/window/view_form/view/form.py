#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import operator
from functools import reduce
import gtk
import gettext
from tryton.common import message, TRYTON_ICON
import tryton.rpc as rpc
import tryton.common as common
from interface import ParserView
from tryton.config import CONFIG

_ = gettext.gettext


class ViewForm(ParserView):

    def __init__(self, window, screen, widget, children=None,
            buttons=None, notebooks=None, cursor_widget='',
            children_field=None):
        super(ViewForm, self).__init__(window, screen, widget, children,
                buttons, notebooks, cursor_widget, children_field)
        self.view_type = 'form'

        for button in self.buttons:
            button.form = self

        self.widgets = children
        for widgets in self.widgets.itervalues():
            for widget in widgets:
                widget.view = self

        vbox = gtk.VBox()
        vp = gtk.Viewport()
        vp.set_shadow_type(gtk.SHADOW_NONE)
        vp.add(self.widget)
        scroll = gtk.ScrolledWindow()
        scroll.add(vp)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_placement(gtk.CORNER_TOP_LEFT)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        viewport.add(scroll)
        if isinstance(self.screen.window, gtk.Dialog):
            width, height = self.widget.size_request()
            if self.screen.window:
                parent = self.screen.window.get_transient_for()
                if parent:
                    parent_width, parent_height = parent.get_size()
                    width = min(parent_width - 40, width)
                    height = min(parent_height - 80, height)
            vbox.set_size_request(width or -1, height or -1)
        vbox.pack_start(viewport, expand=True, fill=True)

        self.widget = vbox

    def __getitem__(self, name):
        return self.widgets[name][0]

    def destroy(self):
        for widget_name in self.widgets.keys():
            for widget in self.widgets[widget_name]:
                widget.destroy()
            del self.widgets[widget_name]
        self.widget.destroy()
        del self.widget
        del self.widgets
        del self.screen
        del self.buttons

    def cancel(self):
        for widgets in self.widgets.itervalues():
            for widget in widgets:
                widget.cancel()

    def set_value(self):
        record = self.screen.current_record
        if record:
            for name, widgets in self.widgets.iteritems():
                if name in record.group.fields:
                    field = record.group.fields[name]
                    for widget in widgets:
                        widget.set_value(record, field)

    def sel_ids_get(self):
        if self.screen.current_record:
            return [self.screen.current_record.id]
        return []

    def selected_records(self):
        if self.screen.current_record:
            return [self.screen.current_record]
        return []

    def reset(self):
        record = self.screen.current_record
        if record:
            for name, widgets in self.widgets.iteritems():
                field = record.group.fields.get(name)
                if field and 'valid' in field.get_state_attrs(record):
                    for widget in widgets:
                        field.get_state_attrs(record)['valid'] = True
                        widget.display(record, field)

    def signal_record_changed(self, *args):
        for widgets in self.widgets.itervalues():
            for widget in widgets:
                if hasattr(widget, 'screen'):
                    for view in widget.screen.views:
                        view.signal_record_changed(*args)

    def display(self):
        record = self.screen.current_record
        if record:
            # Force to set fields in record
            # Get first the lazy one to reduce number of requests
            fields = [(name, field.attrs.get('loading', 'eager'))
                    for name, field in record.group.fields.iteritems()]
            fields.sort(key=operator.itemgetter(1))
            for field, _ in fields:
                record[field].get(record, check_load=False)
        for name, widgets in self.widgets.iteritems():
            field = None
            if record:
                field = record.group.fields.get(name)
            if field:
                field.state_set(record)
            for widget in widgets:
                widget.display(record, field)
        for button in self.buttons:
            button.state_set(record)
        return True

    def set_cursor(self, new=False, reset_view=True):
        if reset_view:
            for notebook in self.notebooks:
                notebook.set_current_page(0)
            if self.cursor_widget in self.widgets:
                self.widgets[self.cursor_widget][0].grab_focus()
        record = self.screen.current_record
        position = reduce(lambda x, y: x + len(y), self.widgets, 0)
        focus_widget = None
        if record:
            for name, widgets in self.widgets.iteritems():
                for widget in widgets:
                    field = record.group.fields.get(name)
                    if not field:
                        continue
                    if not field.get_state_attrs(record).get('valid', True):
                        if widget.position > position:
                            continue
                        position = widget.position
                        focus_widget = widget
        if focus_widget:
            for notebook in self.notebooks:
                for i in range(notebook.get_n_pages()):
                    child = notebook.get_nth_page(i)
                    if focus_widget.widget.is_ancestor(child):
                        notebook.set_current_page(i)
            focus_widget.grab_focus()
