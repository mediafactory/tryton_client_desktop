#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gobject
import gtk
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
import locale
from interface import ParserView
from tryton.action import Action
from tryton.common import message
import gettext
import tryton.common as common
from tryton.config import CONFIG

_ = gettext.gettext


class AdaptModelGroup(gtk.GenericTreeModel):

    def __init__(self, model_group):
        super(AdaptModelGroup, self).__init__()
        self.model_group = model_group
        self.models = model_group.models
        self.last_sort = None
        self.sort_asc = True
        self.set_property('leak_references', False)

    def added(self, modellist, position):
        if modellist is self.models:
            model = self.models[position]
            self.row_inserted(self.on_get_path(model),
                    self.get_iter(self.on_get_path(model)))

    def cancel(self):
        pass

    def removed(self, lst, position):
        self.row_deleted(position)
        self.invalidate_iters()

    def append(self, model):
        self.model_group.model_add(model)

    def prepend(self, model):
        self.model_group.model_add(model, 0)

    def remove(self, iter):
        idx = self.get_path(iter)[0]
        self.model_group.model_remove(self.models[idx])
        self.invalidate_iters()

    def move(self, path, position):
        idx = path[0]
        self.model_group.model_move(self.models[idx], position)

    def sort(self, ids):
        ids2pos = {}
        pos = 0
        new_order = []
        for model in self.models:
            ids2pos[model.id] = pos
            new_order.append(pos)
            pos += 1
        pos = 0
        for obj_id in ids:
            try:
                old_pos = ids2pos[obj_id]
                if old_pos != pos:
                    new_order[old_pos] = pos
                pos += 1
            except:
                continue
        self.models.sort(lambda x, y: \
                cmp(new_order[ids2pos[x.id]], new_order[ids2pos[y.id]]))
        prev = None
        for model in self.models:
            if prev:
                prev.next[id(self.models)] = model
            prev = model
        if prev:
            prev.next[id(self.models)] = None
        self.rows_reordered(None, None, new_order)

    def __len__(self):
        return len(self.models)

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return 1

    def on_get_column_type(self, index):
        return gobject.TYPE_PYOBJECT

    def on_get_path(self, iter):
        return self.models.index(iter)

    def on_get_iter(self, path):
        if isinstance(path, tuple):
            path = path[0]
        if self.models:
            if path < len(self.models):
                return self.models[path]
            else:
                return None
        else:
            return None

    def on_get_value(self, node, column):
        assert column == 0
        return node

    def on_iter_next(self, node):
        try:
            return node.next[id(self.models)]
        except IndexError:
            return None

    def on_iter_has_child(self, node):
        return False

    def on_iter_children(self, node):
        return None

    def on_iter_n_children(self, node):
        if node is None:
            return len(self.models)
        return 0

    def on_iter_nth_child(self, node, nth):
        if node is None and self.models:
            return self.on_get_iter(0)
        return None

    def on_iter_parent(self, node):
        return None


class ViewList(ParserView):

    def __init__(self, window, screen, widget, children=None, buttons=None,
            toolbar=None, notebooks=None, cursor_widget=None):
        super(ViewList, self).__init__(window, screen, widget, children,
                buttons, toolbar, notebooks, cursor_widget)
        self.store = None
        self.view_type = 'tree'
        self.model_add_new = True
        self.widget = gtk.VBox()
        self.widget_tree = widget
        scroll = gtk.ScrolledWindow()
        scroll.add(self.widget_tree)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget.pack_start(scroll, expand=True, fill=True)
        self.widget_tree.screen = screen
        self.reload = False
        self.children = children

        if children:
            hbox = gtk.HBox()
            self.widget.pack_start(hbox, expand=False, fill=False, padding=2)
            keys = children.keys()
            keys.sort()
            for i in keys:
                hbox2 = gtk.HBox()
                hbox2.pack_start(children[i][1], expand=True, fill=False)
                hbox2.pack_start(children[i][2], expand=True, fill=False)
                hbox.pack_start(hbox2, expand=False, fill=False, padding=12)
            hbox.show_all()

        self.display()

        self.widget_tree.connect('button-press-event', self.__button_press)
        self.widget_tree.connect_after('row-activated', self.__sig_switch)
        selection = self.widget_tree.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.__select_changed)

        if self.widget_tree.sequence:
            self.widget_tree.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                    [('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),],
                    gtk.gdk.ACTION_MOVE)
            self.widget_tree.drag_source_set(gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                    [('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),],
                    gtk.gdk.ACTION_MOVE)
            self.widget_tree.enable_model_drag_dest(
                    [('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),],
                    gtk.gdk.ACTION_MOVE)

            self.widget_tree.connect('drag-drop', self.drag_drop)
            self.widget_tree.connect("drag-data-get", self.drag_data_get)
            self.widget_tree.connect('drag-data-received', self.drag_data_received)
            self.widget_tree.connect('drag-data-delete', self.drag_data_delete)

        self.widget_tree.connect('key_press_event', self.on_keypres)

    def on_keypres(self, widget, event):
        if event.keyval == gtk.keysyms.c and event.state & gtk.gdk.CONTROL_MASK:
            self.on_copy()
            return False

    def on_copy(self):
        clipboard = self.widget_tree.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
        targets = [
            ('STRING', 0, 0),
            ('TEXT', 0, 1),
            ('COMPOUND_TEXT', 0, 2),
            ('UTF8_STRING', 0, 3)
        ]
        clipboard.set_with_data(targets, self.copy_get_func,
                self.copy_clear_func, self.widget_tree.get_selection())

    def copy_foreach(self, treemodel, path,iter, data):
        model = treemodel.get_value(iter, 0)
        values = []
        for col in self.widget_tree.get_columns():
            if not col.get_visible():
                continue
            cell = self.widget_tree.cells[col.name]
            values.append('"' + str(cell.get_textual_value(model)) + '"')
        data.append('\t'.join(values))
        return

    def copy_get_func(self, clipboard, selectiondata, info, selection):
        data = []
        selection.selected_foreach(self.copy_foreach, data)
        clipboard.set_text('\n'.join(data))
        del data
        return

    def copy_clear_func(self, clipboard, selection):
        del selection
        return

    def drag_drop(self, treeview, context, x, y, time):
        treeview.emit_stop_by_name('drag-drop')
        treeview.drag_get_data(context, context.targets[-1], time)
        return True

    def drag_data_get(self, treeview, context, selection, target_id,
            etime):
        treeview.emit_stop_by_name('drag-data-get')
        def _func_sel_get(store, path, iter, data):
            data.append(path)
        data = []
        treeselection = treeview.get_selection()
        treeselection.selected_foreach(_func_sel_get, data)
        data = str(data[0])
        selection.set(selection.target, 8, data)

    def drag_data_received(self, treeview, context, x, y, selection,
            info, etime):
        treeview.emit_stop_by_name('drag-data-received')
        if treeview.sequence:
            for model in self.screen.models.models:
                if model[treeview.sequence].get_state_attrs(
                        model).get('readonly', False):
                    return
        model = treeview.get_model()
        data = eval(selection.data)
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            idx = path[0]
            if position in (gtk.TREE_VIEW_DROP_BEFORE,
                    gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                model.move(data, idx)
            else:
                model.move(data, idx + 1)
        context.drop_finish(False, etime)
        if treeview.sequence:
            self.screen.models.set_sequence(field=treeview.sequence)

    def drag_data_delete(self, treeview, context):
        treeview.emit_stop_by_name('drag-data-delete')

    def __button_press(self, treeview, event):
        if event.button == 3:
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            selection = treeview.get_selection()
            if selection.get_mode() == gtk.SELECTION_SINGLE:
                model = selection.get_selected()[0]
            elif selection.get_mode() == gtk.SELECTION_MULTIPLE:
                model = selection.get_selected_rows()[0]
            if (not path) or not path[0]:
                return False
            model = model.models[path[0][0]]

            if path[1]._type == 'many2one':
                value = model[path[1].name].get(model)
                ir_action_keyword = RPCProxy('ir.action.keyword')
                try:
                    relates = ir_action_keyword.get_keyword('form_relate',
                            (self.screen.fields[path[1].name]['relation'], 0),
                            rpc.CONTEXT)
                except Exception, exception:
                    common.process_exception(exception, self.window)
                    return False
                menu_entries = []
                menu_entries.append((None, None, None))
                menu_entries.append((_('Actions'),
                    lambda x: self.click_and_action(
                        'form_action', value, path), 0))
                menu_entries.append((_('Reports'),
                    lambda x: self.click_and_action(
                        'form_print', value, path), 0))
                menu_entries.append((None, None, None))
                for relate in relates:
                    relate['string'] = relate['name']
                    fct = lambda action: lambda x: \
                            self.click_and_relate(action, value, path)
                    menu_entries.append(
                            ('... ' + relate['name'], fct(relate), 0))
                menu = gtk.Menu()
                for stock_id, callback, sensitivity in menu_entries:
                    if stock_id:
                        item = gtk.ImageMenuItem(stock_id)
                        if callback:
                            item.connect('activate', callback)
                        item.set_sensitive(bool(sensitivity or value))
                    else:
                        item = gtk.SeparatorMenuItem()
                    item.show()
                    menu.append(item)
                menu.popup(None, None, None, event.button, event.time)
        return False

    def click_and_relate(self, action, value, path):
        data = {}
        context = {}
        act = action.copy()
        if not(value):
            message(_('You must select a record to use the relation!'))
            return False
        from tryton.gui.window.view_form.screen import Screen
        screen = Screen(self.screen.fields[path[1].name]['relation'],
                self.window)
        screen.load([value])
        act['domain'] = screen.current_model.expr_eval(act['domain'],
                check_load=False)
        act['context'] = str(screen.current_model.expr_eval(act['context'],
            check_load=False))
        return Action._exec_action(act, data, context)

    def click_and_action(self, atype, value, path):
        return Action.exec_keyword(atype, {
            'model': self.screen.fields[path[1].name]['relation'],
            'id': value or False, 'ids': [value]})

    def signal_record_changed(self, signal, *args):
        if self.store:
            if signal == 'record-added':
                self.store.added(*args)
            elif signal == 'record-removed':
                self.store.removed(*args)
        self.update_children()

    def cancel(self):
        pass

    def __str__(self):
        return 'ViewList (%s)' % self.screen.resource

    def __getitem__(self, name):
        return None

    def destroy(self):
        if CONFIG['client.tree_width']:
            fields = {}
            last_col = None
            for col in self.widget_tree.get_columns():
                if col.get_width() != col.width and col.get_visible():
                    fields[col.name] = col.get_width()
                if col.get_visible():
                    last_col = col
            #Don't set width for last visible columns
            #as it depends of the screen size
            if last_col and last_col.name in fields:
                del fields[last_col.name]

            if fields:
                try:
                    rpc.execute('object', 'execute', 'ir.ui.view_tree_width',
                            'set_width', self.screen.name, fields, rpc.CONTEXT)
                except:
                    pass
        self.widget_tree.destroy()
        del self.screen
        del self.widget_tree
        del self.widget

    def __sig_switch(self, treeview, *args):
        self.screen.row_activate()

    def __select_changed(self, tree_sel):
        if tree_sel.get_mode() == gtk.SELECTION_SINGLE:
            model, iter = tree_sel.get_selected()
            if iter:
                path = model.get_path(iter)[0]
                self.screen.current_model = model.models[path]
        elif tree_sel.get_mode() == gtk.SELECTION_MULTIPLE:
            model, paths = tree_sel.get_selected_rows()
            if paths:
                self.screen.current_model = model.models[paths[0][0]]
        self.update_children()


    def set_value(self):
        if hasattr(self.widget_tree, 'editable') \
                and self.widget_tree.editable:
            self.widget_tree.set_value()

    def reset(self):
        pass

    # self.widget.set_model(self.store) could be removed if the store
    # has not changed -> better ergonomy. To test
    def display(self):
        if self.reload \
                or (not self.widget_tree.get_model()) \
                    or self.screen.models != \
                        self.widget_tree.get_model().model_group:
            self.store = AdaptModelGroup(self.screen.models)
            self.widget_tree.set_model(self.store)
        self.reload = False
        if not self.screen.current_model:
            # Should find a simpler solution to do something like
            #self.widget.set_cursor(None,None,False)
            if self.store:
                self.widget_tree.set_model(self.store)
        self.set_state()
        self.update_children()

    def set_state(self):
        model = self.screen.current_model
        values = rpc.CONTEXT.copy()
        values['state'] = 'draft'
        if model:
            for field in model.mgroup.fields:
                values[field] = model[field].get(model, check_load=False)
            for field in model.mgroup.fields:
                modelfield = model.mgroup.mfields.get(field, None)
                if modelfield:
                    modelfield.state_set(model, values)

    def update_children(self):
        ids = self.sel_ids_get()
        for child in self.children:
            value = 0.0
            loaded = True
            for model in self.screen.models.models:
                if not model.loaded:
                    loaded = False
                    break
                if model.id in ids or not ids:
                    if not value:
                        value = model.fields_get()[self.children[child][0]]\
                                .get(model, check_load=False)
                    else:
                        value += model.fields_get()[self.children[child][0]]\
                                .get(model, check_load=False)
            if loaded:
                label_str = locale.format('%.' + str(self.children[child][3]) + 'f',
                        value, True)
            else:
                label_str = '-'
            if self.children[child][4]:
                self.children[child][2].set_markup('<b>%s</b>' % label_str)
            else:
                self.children[child][2].set_markup(label_str)

    def set_cursor(self, new=False):
        self.widget_tree.grab_focus()
        if self.screen.current_model:
            path = self.store.on_get_path(self.screen.current_model)
            focus_column = None
            for column in self.widget_tree.get_columns():
                renderer = column.get_cell_renderers()[0]
                if isinstance(renderer, gtk.CellRendererToggle):
                    editable = renderer.get_property('activatable')
                else:
                    editable = renderer.get_property('editable')
                if column.get_visible() and editable:
                    focus_column = column
                    break
            self.widget_tree.set_cursor(path, focus_column, new)

    def sel_ids_get(self):
        def _func_sel_get(store, path, iter, ids):
            model = store.on_get_iter(path)
            if model.id:
                ids.append(model.id)
        ids = []
        sel = self.widget_tree.get_selection()
        sel.selected_foreach(_func_sel_get, ids)
        return ids

    def sel_models_get(self):
        def _func_sel_get(store, path, iter, models):
            models.append(store.on_get_iter(path))
        models = []
        sel = self.widget_tree.get_selection()
        sel.selected_foreach(_func_sel_get, models)
        return models

    def unset_editable(self):
        self.widget_tree.editable = False
        for col in self.widget_tree.get_columns():
            for renderer in col.get_cell_renderers():
                if isinstance(renderer, gtk.CellRendererToggle):
                    renderer.set_property('activatable', False)
                else:
                    renderer.set_property('editable', False)
