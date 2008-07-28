#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
"View tree"
import gtk
import gobject
from tryton.config import CONFIG
import time
import math
import tryton.rpc as rpc
from parse import Parse
import datetime as DT
import locale
from tryton.common import DT_FORMAT, DHM_FORMAT
import tryton.common as common
from _strptime import LocaleTime

FIELDS_LIST_TYPE = {
    'boolean': gobject.TYPE_BOOLEAN,
    'integer': gobject.TYPE_INT,
}


class ViewTreeModel(gtk.GenericTreeModel, gtk.TreeSortable):
    """
    BUG: ids = []

    Tree struct:  [ id, values, childs, childs_id ]

       values: [...]
       childs: [ tree_struct ]
               [] for no childs
               None for undevelopped (with childs!)
           assert: no childs => []

    Node struct: [list of (pos, list) ]
    """

    def __init__(self, ids, view, fields, fields_type, fields_attrs,
            context=None, pixbufs=None, treeview=None):
        gtk.GenericTreeModel.__init__(self)
        self.fields = fields
        self.fields_type = fields_type
        self.fields_attrs = fields_attrs
        self.view = view
        self.roots = ids
        self.context = context or {}
        self.to_reload = []
        self.tree = self._node_process(self.roots)
        self.pixbufs = pixbufs or {}
        self.treeview = treeview

    def _read(self, ids, fields):
        ctx = {}
        ctx.update(rpc.CONTEXT)
        ctx.update(self.context)
        res_ids = []
        if ids:
            args = ('object', 'execute', self.view['model'], 'read', ids, fields,
                    ctx)
            try:
                res_ids = rpc.execute(*args)
                for obj_id in ids:
                    if obj_id in self.to_reload:
                        self.to_reload.remove(obj_id)
            except Exception, exception:
                for obj_id in ids:
                    val = {'id': obj_id}
                    for field in fields:
                        if field in self.fields_type \
                                and self.fields_type[field]['type'] \
                                    in ('one2many', 'many2many'):
                            val[field] = []
                        else:
                            val[field] = ''
                    res_ids.append(val)
                    if obj_id not in self.to_reload:
                        self.to_reload.append(obj_id)
        for field in self.fields:
            field_type = self.fields_type[field]['type']
            if field in self.fields_attrs \
                    and 'widget' in self.fields_attrs[field]:
                field_type = self.fields_attrs[field]['widget']
            if field_type in ('date',):
                display_format = LocaleTime().LC_date.replace('%y', '%Y')
                for obj in res_ids:
                    if obj[field]:
                        date = time.strptime(obj[field], DT_FORMAT)
                        obj[field] = time.strftime(display_format, date)
            elif field_type in ('datetime',):
                display_format = LocaleTime().LC_date.replace('%y', '%Y') \
                        + ' %H:%M:%S'
                for obj in res_ids:
                    if obj[field]:
                        date = time.strptime(obj[field], DHM_FORMAT)
                        if 'timezone' in rpc.CONTEXT:
                            try:
                                import pytz
                                lzone = pytz.timezone(rpc.CONTEXT['timezone'])
                                szone = pytz.timezone(rpc.TIMEZONE)
                                datetime = DT.datetime(date[0], date[1],
                                        date[2], date[3], date[4], date[5],
                                        date[6])
                                sdt = szone.localize(datetime, is_dst=True)
                                ldt = sdt.astimezone(lzone)
                                date = ldt.timetuple()
                            except:
                                pass
                        obj[field] = time.strftime(display_format, date)
            elif field_type in ('many2one',):
                for obj in res_ids:
                    if obj[field]:
                        obj[field] = obj[field][1]
            elif field_type in ('selection'):
                for obj in res_ids:
                    if obj[field]:
                        selection = self.fields_type[field]['selection']
                        if 'relation' in self.fields_type[field]:
                            try:
                                selection = rpc.execute('object', 'execute',
                                        self.fields_type[field]['relation'],
                                        'name_search', '',
                                        self.fields_type[field].get('domain', []),
                                        'ilike', rpc.CONTEXT)
                            except:
                                selection = []
                        else:
                            if not isinstance(self.fields_type[field]['selection'],
                                    (list, tuple)):
                                try:
                                    selection = rpc.execute('object', 'execute',
                                            self.view['model'],
                                            self.fields_type[field]['selection'],
                                            rpc.CONTEXT)
                                except:
                                    selection = []
                        self.fields_type[field]['selection'] = selection
            elif field_type in ('float', 'numeric'):
                digits = self.fields_type[field].get('digits', (16, 2))
                if isinstance(digits, str):
                    digits = eval(digits, obj)
                for obj in res_ids:
                    obj[field] = locale.format('%.' + str(digits[1]) + 'f',
                            obj[field] or 0.0, True)
            elif field_type in ('interger',):
                for obj in res_ids:
                    obj[field] = locale.format('%d', obj[field] or 0, True)
            elif field_type in ('float_time',):
                for obj in res_ids:
                    val = '%02d:%02d' % (math.floor(abs(obj[field])),
                            round(abs(obj[field]) % 1 + 0.01, 2) * 60)
                    if obj[field] < 0:
                        val = '-' + val
                    obj[field] = val
            elif field_type in ('boolean',):
                for obj in res_ids:
                    obj[field] = bool(obj[field])
        return res_ids

    def _node_process(self, ids):
        tree = []
        if self.view.get('field_childs', False):
            res = self._read(ids, self.fields + [self.view['field_childs']])
            for obj in res:
                tree.append([obj['id'], None, [],
                    obj[self.view['field_childs']]])
                tree[-1][1] = [obj[y] for y in self.fields]
                if obj[self.view['field_childs']]:
                    tree[-1][2] = None
        else:
            res = self._read(ids, self.fields)
            for obj in res:
                tree.append([obj['id'], [obj[y] for y in self.fields], []])
        return tree

    def _node_expand(self, node):
        node[2] = self._node_process(node[3])

    #Mandatory GenericTreeModel method
    def on_get_path(self, node):
        '''returns the tree path (a tuple of indices)'''
        return tuple([x[0] for x in node])

    def on_get_flags(self):
        return 0

    def on_get_n_columns(self):
        return len(self.fields)+1

    def on_get_column_type(self, index):
        if index in self.pixbufs:
            return gtk.gdk.Pixbuf
        if index == 0:
            return gobject.TYPE_INT
        return FIELDS_LIST_TYPE.get(
                self.fields_type[self.fields[index-1]]['type'],
                gobject.TYPE_STRING)

    def on_get_tree_path(self, node):
        '''returns the tree path (a tuple of indices)'''
        return tuple([x[0] for x in node])

    def on_get_iter(self, path):
        '''returns the node corresponding to the given path.'''
        node = []
        tree = self.tree
        for i in path:
            if not tree or i >= len(tree):
                return None
            node.append((i, tree))
            tree = tree[i][2]
        return node

    def on_get_value(self, node, column):
        (i, values) = node[-1]
        if column:
            value = values[i][1][column - 1]
        else:
            value = values[i][0]

        res = value or ''
        if (column in self.pixbufs) and res:
            return self.treeview.render_icon(stock_id=res,
                    size=gtk.ICON_SIZE_BUTTON, detail=None)
        field = self.fields[column - 1]
        if hasattr(self.fields_type[field], 'selection'):
            res = dict(self.fields_type[field]['selection']).get(res, '')
        return res

    def on_iter_next(self, node):
        '''returns the next node at this level of the tree'''
        node = node[:]
        (i, values) = node[-1]
        if i < len(values) - 1:
            node[-1] = (i + 1, values)
            return node
        return None

    def on_iter_children(self, node):
        '''returns the first child of this node'''
        if node is None:
            return [(0, self.tree)]
        node = node[:]
        (i, values) = node[-1]

        to_reload = False
        if len(values[i]) >= 4:
            for obj_id in values[i][3]:
                if obj_id in self.to_reload:
                    to_reload = True

        if values[i][2] is None or to_reload:
            self._node_expand(values[i])
        if values[i][2] == []:
            return None
        node.append((0, values[i][2]))
        return node

    def on_iter_has_child(self, node):
        '''returns true if this node has children'''
        (i, values) = node[-1]
        return values[i][2] != []

    def on_iter_n_children(self, node):
        '''returns the number of children of this node'''
        if node is None:
            return len(self.tree)
        (i, values) = node[-1]

        to_reload = False
        if len(values[i]) >= 4:
            for obj_id in values[i][3]:
                if obj_id in self.to_reload:
                    to_reload = True

        if values[i][2] is None or to_reload:
            self._node_expand(values[i])
        return len(values[i][2])

    def on_iter_nth_child(self, node, child):
        '''returns the nth child of this node'''
        if node is None:
            if child < len(self.tree):
                return [(child, self.tree)]
            return None
        node = node[:]
        (i, values) = node[-1]

        to_reload = False
        if len(values[i]) >= 4:
            for obj_id in values[i][3]:
                if obj_id in self.to_reload:
                    to_reload = True

        if values[i][2] is None or to_reload:
            self._node_expand(values[i])
        if child < len(values[i][2]):
            node.append((child, values[i][2]))
            return node
        return None

    def on_iter_parent(self, node):
        '''returns the parent of this node'''
        if node is None:
            return None
        return node[:-1]

    def cus_refresh(self):
        tree = self.tree
        tree[0][2] = None

    def _cus_row_find(self, ids_res):
        tree = self.tree
        try:
            ids = ids_res[:]
            while len(ids)>0:
                if ids[-1] in self.roots:
                    ids.pop()
                    break
                ids.pop()
            path = []
            while ids != []:
                path.append(0)
                val = ids.pop()
                i = iter(tree)
                while True:
                    node = i.next()
                    if node[0] == val:
                        break
                    path[-1] += 1
                if (node[2] is None) and (ids != []):
                    return None
                tree = node[2]
            return (tuple(path), node)
        except:
            return None

class ViewTree(object):
    "View tree"

    def __init__(self, view_info, ids, window, sel_multi=False,
            context=None):
        self.window = window
        self.view = gtk.TreeView()
        self.view.set_headers_visible(not CONFIG['client.modepda'])
        self.context = {}
        self.context.update(rpc.CONTEXT)
        if context:
            self.context.update(context)
        self.fields = view_info['fields']
        parse = Parse(self.fields)
        parse.parse(view_info['arch'], self.view)
        self.toolbar = parse.toolbar
        self.pixbufs = parse.pixbufs
        self.name = parse.title
        self.sel_multi = sel_multi

        if sel_multi:
            self.view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        else:
            self.view.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.view.set_expander_column(self.view.get_column(1))
        self.view.set_enable_search(False)
        self.view.get_column(0).set_visible(False)

        self.ids = ids
        self.view_info = view_info
        self.fields_order = parse.fields_order
        self.fields_attrs = parse.fields_attrs
        self.model = None
        self.reload()

        self.view.show_all()
        self.search = []
        self.next = 0

    def reload(self):
        del self.model
        self.model = ViewTreeModel(self.ids, self.view_info, self.fields_order,
                self.fields, self.fields_attrs, context=self.context,
                pixbufs=self.pixbufs, treeview=self.view)
        self.view.set_model(self.model)

    def widget_get(self):
        return self.view

    def sel_ids_get(self):
        sel = self.view.get_selection()
        if not sel:
            return None
        sel = sel.get_selected_rows()
        if not sel:
            return []
        (model, iters) = sel
        return [int(model.get_value(model.get_iter(x), 0)) for x in iters]

    def sel_id_get(self):
        res = self.sel_ids_get()
        if res:
            res = res[0]
        return res

    def value_get(self, col):
        sel = self.view.get_selection().get_selected_rows()
        if sel is None:
            return None
        (model, i) = sel
        if not i:
            return None
        return model.get_value(i, col)
