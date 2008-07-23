#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gettext
from tryton.common import message, TRYTON_ICON
import tryton.rpc as rpc
from interface import ParserView
from tryton.action import Action
from tryton.config import CONFIG

_ = gettext.gettext


class ViewWidget(object):

    def __init__(self, parent, widget, widget_name):
        self.view_form = parent
        self.widget = widget
        self.widget._view = self
        self.widget_name = widget_name

    def display(self, model, values=None):
        if values is None:
            values = {'state': 'draft'}
        if not model:
            self.widget.display(model, False)
            return False
        modelfield = model.mgroup.mfields.get(self.widget_name, None)
        if modelfield:
            modelfield.state_set(model, values)
            self.widget.display(model, modelfield)
        elif isinstance(self.widget, Action):
            self.widget.display(model, False)

    def reset(self, model):
        modelfield = None
        values = rpc.CONTEXT.copy()
        values['state'] = 'draft'
        if model:
            modelfield = model.mgroup.mfields.get(self.widget_name, None)
            if modelfield and 'valid' in modelfield.get_state_attrs(model):
                modelfield.get_state_attrs(model)['valid'] = True
            for field in model.mgroup.fields:
                values[field] = model[field].get(model, check_load=False)
        self.display(model, values)

    def set_value(self, model):
        if self.widget_name in model.mgroup.mfields:
            self.widget.set_value(model, model.mgroup.mfields[self.widget_name])

    def _get_model(self):
        return self.view_form.screen.current_model

    model = property(_get_model)

    def _get_modelfield(self):
        if self.model:
            return self.model.mgroup.mfields[self.widget_name]

    modelfield = property(_get_modelfield)


class ViewForm(ParserView):

    def __init__(self, window, screen, widget, children=None,
            buttons=None, toolbar=None, notebooks=None, cursor_widget=''):
        super(ViewForm, self).__init__(window, screen, widget, children,
                buttons, toolbar, notebooks, cursor_widget)
        self.view_type = 'form'
        self.model_add_new = False

        for button in self.buttons:
            button.form = self

        self.widgets = dict([(name, ViewWidget(self, widget, name))
                             for name, widget in children.items()])

        if toolbar and not CONFIG['client.modepda']:
            vbox = gtk.VBox()
            vbox.pack_start(self.widget)

            hbox = gtk.HBox()
            vbox.pack_start(hbox, False, False)
            self.widget = vbox

            sep = False
            for icontype in ('print', 'action', 'relate'):
                if not toolbar[icontype]:
                    continue
                gtktoolbar = gtk.Toolbar()
                gtktoolbar.set_orientation(gtk.ORIENTATION_HORIZONTAL)
                gtktoolbar.set_style(gtk.TOOLBAR_BOTH)
                hbox.pack_start(gtktoolbar, True, True)

                for tool in toolbar[icontype]:
                    iconstock = {
                        'print': 'tryton-print',
                        'action': 'tryton-executable',
                        'relate': 'tryton-go-jump',
                    }.get(icontype)

                    tbutton = gtk.ToolButton(iconstock)
                    tbutton.set_use_underline(True)
                    tbutton.set_label(tool['name'])
                    gtktoolbar.insert(tbutton, -1)

                    tbutton.connect('clicked', self._action, tool, icontype)

    def _action(self, widget, action, atype):
        data = {}
        context = {}
        act = action.copy()
        if atype in ('print', 'action'):
            self.screen.save_current()
            obj_id = self.screen.current_model \
                    and self.screen.current_model.id
            if not (obj_id):
                if atype in ('print'):
                    message(_('You must save this record ' \
                        'to use the print button!'), self.window)
                if atype in ('action'):
                    message(_('You must save this record ' \
                        'to use the action button!'), self.window)
                return False
            self.screen.display()
        if atype == 'relate':
            obj_id = self.screen.current_model \
                    and self.screen.current_model.id
            if not (obj_id):
                message(_('You must select a record ' \
                        'to use the relate button !'), self.window)
                return False
            if 'domain' in act:
                act['domain'] = str(
                        self.screen.current_model.expr_eval(
                                act['domain'], check_load=False))
            if 'context' in act:
                act['context'] = str(
                        self.screen.current_model.expr_eval(
                            act['context'], check_load=False))
        data = {
            'model': self.screen.name,
            'id': obj_id,
            'ids': [obj_id],
        }
        value = Action._exec_action(act, data, context)
        if atype in ('print', 'action'):
            self.screen.reload()
        return value

    def __getitem__(self, name):
        return self.widgets[name]

    def destroy(self):
        for widget in self.widgets.keys():
            self.widgets[widget].widget.destroy()
            del self.widgets[widget]
        self.widget.destroy()
        del self.widget
        del self.widgets
        del self.screen
        del self.buttons

    def cancel(self):
        pass

    def set_value(self):
        model = self.screen.current_model
        if model:
            for widget in self.widgets.values():
                widget.set_value(model)

    def sel_ids_get(self):
        if self.screen.current_model:
            return [self.screen.current_model.id]
        return []

    def sel_models_get(self):
        if self.screen.current_model:
            return [self.screen.current_model]
        return []

    def reset(self):
        model = self.screen.current_model
        for name, widget in self.widgets.items():
            widget.reset(model)

    def signal_record_changed(self, *args):
        for widget in self.widgets.values():
            if hasattr(widget.widget, 'screen'):
                for view in widget.widget.screen.views:
                    view.signal_record_changed(*args)

    def display(self):
        model = self.screen.current_model
        values = rpc.CONTEXT.copy()
        values['state'] = 'draft'
        if model:
            for field in model.mgroup.fields:
                values[field] = model[field].get(model, check_load=False)
        for widget in self.widgets.values():
            widget.display(model, values)
        for button in self.buttons:
            button.state_set(values)
        return True

    def set_cursor(self, new=False):
        for notebook in self.notebooks:
            notebook.set_current_page(0)
        if self.cursor_widget in self.widgets:
            self.widgets[self.cursor_widget].widget.grab_focus()
        model = self.screen.current_model
        position = len(self.widgets)
        focus_widget = None
        if model:
            for widget in self.widgets.values():
                modelfield = model.mgroup.mfields.get(widget.widget_name, None)
                if not modelfield:
                    continue
                if not modelfield.get_state_attrs(model).get('valid', True):
                    if widget.widget.position >= position:
                        continue
                    position = widget.widget.position
                    focus_widget = widget
        if focus_widget:
            for notebook in self.notebooks:
                for i in range(notebook.get_n_pages()):
                    child = notebook.get_nth_page(i)
                    if focus_widget.widget.widget.is_ancestor(child):
                        notebook.set_current_page(i)
            focus_widget.widget.grab_focus()
