"Parse"
import gtk
from xml.parsers import expat
import gettext

_ = gettext.gettext

class Parse(object):
    "Parse"

    def __init__(self, fields):
        self.fields = fields
        self.pixbufs = {}
        self.fields_order = []
        self.title = _('Tree')
        self.toolbar = False
        self.tree = None
        self.pos = 1

    def _psr_start(self, name, attrs):
        if name == 'tree':
            if 'string' in attrs:
                self.title = attrs['string']
            if 'toolbar' in attrs:
                self.toolbar = bool(attrs.get('toolbar'))
        elif name == 'field':
            field_type = self.fields[attrs['name']]['type']
            if field_type != 'boolean':
                column = gtk.TreeViewColumn(
                        self.fields[attrs['name']]['string'])
                if 'icon' in attrs:
                    render_pixbuf = gtk.CellRendererPixbuf()
                    column.pack_start(render_pixbuf, expand=False)
                    column.add_attribute(render_pixbuf, 'pixbuf', self.pos)
                    self.fields_order.append(str(attrs['icon']))
                    self.pixbufs[self.pos] = True
                    self.pos += 1

                cell = gtk.CellRendererText()
                cell.set_fixed_height_from_font(1)
                if field_type in ('float', 'numeric', 'integer'):
                    cell.set_property('xalign', 1.0)
                column.pack_start(cell, expand=False)
                column.add_attribute(cell, 'text', self.pos)
            else:
                cell = gtk.CellRendererToggle()
                column = gtk.TreeViewColumn(
                        self.fields[attrs['name']]['string'])
                column.pack_start(cell, expand=False)
                column.add_attribute(cell, 'active', self.pos)
            self.pos += 1
            column.set_resizable(1)
            self.fields_order.append(str(attrs['name']))
            self.tree.append_column(column)
        else:
            import logging
            log = logging.getLogger('view')
            log.error('unknown tag: '+str(name))
            del log

    def _psr_end(self, name):
        pass

    def _psr_char(self, char):
        pass

    def parse(self, xml_data, tree):
        "Parse"
        cell = gtk.CellRendererText()
        cell.set_fixed_height_from_font(1)
        column = gtk.TreeViewColumn('ID', cell, text=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(60)
        column.set_visible(False)
        tree.append_column(column)
        self.tree = tree
        psr = expat.ParserCreate()
        psr.StartElementHandler = self._psr_start
        psr.EndElementHandler = self._psr_end
        psr.CharacterDataHandler = self._psr_char
        psr.Parse(xml_data)
        return self.pos
