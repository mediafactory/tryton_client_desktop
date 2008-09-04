#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gobject


class CellRendererText(gtk.GenericCellRenderer):
    __gproperties__ = {
            'text': (gobject.TYPE_STRING, None, 'Text',
                'Text', gobject.PARAM_READWRITE),
            'foreground': (gobject.TYPE_STRING, None, 'Foreground',
                'Foreground', gobject.PARAM_READWRITE),
            'background': (gobject.TYPE_STRING, None, 'Background',
                'Background', gobject.PARAM_READWRITE),
            'editable': (gobject.TYPE_INT, 'Editable',
                'Editable', 0, 10, 0, gobject.PARAM_READWRITE),
    }

    def __init__(self):
        self.__gobject_init__()
        self._renderer = gtk.CellRendererText()
        self.set_property("mode", self._renderer.get_property("mode"))

        self.text = self._renderer.get_property('text')
        self.editable = self._renderer.get_property('editable')

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
        self._renderer.set_property(pspec.name, value)
        self.set_property("mode", self._renderer.get_property("mode"))

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_get_size(self, widget, cell_area):
        return self._renderer.get_size(widget, cell_area)

    def on_render(self, window, widget, background_area, cell_area,
            expose_area, flags):
        return self._renderer.render(window, widget, background_area,
                cell_area, expose_area, flags)

    def on_activate(self, event, widget, path, background_area, cell_area,
            flags):
        return self._renderer.activate(event, widget, path, background_area,
                cell_area, flags)

    def on_start_editing(self, event, widget, path, background_area,
            cell_area, flags):
        if not event:
            event = gtk.gdk.Event(gtk.keysyms.Tab)
        editable = self._renderer.start_editing(event, widget, path,
                background_area, cell_area, flags)

        colormap = editable.get_colormap()
        if hasattr(self, 'background'):
            colour = colormap.alloc_color(getattr(self, 'background'))
        else:
            colour = colormap.alloc_color('white')
        editable.modify_bg(gtk.STATE_ACTIVE, colour)
        editable.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        editable.modify_base(gtk.STATE_NORMAL, colour)
        editable.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        editable.modify_text(gtk.STATE_INSENSITIVE, gtk.gdk.color_parse("black"))

        return editable

gobject.type_register(CellRendererText)
