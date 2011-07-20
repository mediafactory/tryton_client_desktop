#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import gettext
import gtk
import pango

import tryton.common as common
from tryton.config import CONFIG
from tryton.gui import Main

_ = gettext.gettext


class TabContent(object):

    def create_tabcontent(self):
        self.buttons = {}
        self.tooltips = common.Tooltips()
        self.accel_group = Main.get_main().accel_group

        self.widget = gtk.VBox(spacing=3)
        self.widget.show()

        title_box = self.make_title_bar()
        self.widget.pack_start(title_box, expand=False, fill=True, padding=3)

        self.toolbar = self.create_toolbar(self.get_toolbars())
        self.toolbar.show_all()
        self.widget.pack_start(self.toolbar, False, True)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.add(self.widget_get())
        viewport.show()
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.add(viewport)
        self.scrolledwindow.show()

        self.widget.pack_start(self.scrolledwindow)

    def make_title_bar(self):
        title = gtk.Label()
        title.set_use_markup(True)
        title.modify_font(pango.FontDescription("14"))
        title.set_label('<b>' + self.name + '</b>')
        title.set_padding(10, 4)
        title.set_alignment(0.0, 0.5)
        title.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        title.show()

        title_menu = gtk.MenuBar()
        title_item = gtk.MenuItem('')
        title_item.remove(title_item.get_children()[0])
        menu_image = gtk.Image()
        menu_image.set_from_stock('tryton-preferences-system',
            gtk.ICON_SIZE_BUTTON)
        title_item.add(menu_image)
        title_item.set_submenu(self.set_menu_form())
        title_menu.append(title_item)
        title_menu.show_all()

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

        self.status_label = gtk.Label()
        self.status_label.set_padding(5, 4)
        self.status_label.set_alignment(0.0, 0.5)
        self.status_label.show()

        hbox = gtk.HBox()
        hbox.pack_start(title, expand=True, fill=True)
        hbox.pack_start(vbox, expand=False, fill=True, padding=20)
        hbox.pack_start(self.status_label, expand=False, fill=True)
        hbox.show()

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame.add(hbox)
        frame.show()

        eb = gtk.EventBox()
        eb.add(frame)
        eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))
        eb.show()

        frame_menu = gtk.Frame()
        frame_menu.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame_menu.add(title_menu)
        frame_menu.show()

        title_box = gtk.HBox()
        title_box.pack_start(frame_menu, expand=False, fill=True)
        title_box.pack_start(eb, expand=True, fill=True)
        title_box.show()

        return title_box

    def create_base_toolbar(self, toolbar):

        for button_id, stock_id, label, tooltip, callback in self.toolbar_def:
            if button_id:
                toolitem = gtk.ToolButton(stock_id)
                toolitem.set_label(label)
                toolitem.set_use_underline(True)
                if callback:
                    toolitem.connect('clicked', getattr(self, callback))
                else:
                    toolitem.props.sensitive = False
                self.tooltips.set_tip(toolitem, tooltip)
                self.buttons[button_id] = toolitem
            else:
                toolitem = gtk.SeparatorToolItem()
            toolbar.insert(toolitem, -1)

    def set_menu_form(self):
        menu_form = gtk.Menu()
        menu_form.set_accel_group(self.accel_group)
        menu_form.set_accel_path('<tryton>/Form')

        for label, stock_id, callback, accel_path in self.menu_def:
            if label:
                menuitem = gtk.ImageMenuItem(label, self.accel_group)
                if callback:
                    menuitem.connect('activate', getattr(self, callback))
                else:
                    menuitem.props.sensitive = False
                if stock_id:
                    image = gtk.Image()
                    image.set_from_stock(stock_id, gtk.ICON_SIZE_MENU)
                    menuitem.set_image(image)
                if accel_path:
                    menuitem.set_accel_path(accel_path)
            else:
                menuitem = gtk.SeparatorMenuItem()
            menu_form.add(menuitem)

        menu_form.show_all()
        return menu_form

    def create_toolbar(self, toolbars):
        gtktoolbar = gtk.Toolbar()
        option = CONFIG['client.toolbar']
        if option == 'default':
            gtktoolbar.set_style(False)
        elif option == 'both':
            gtktoolbar.set_style(gtk.TOOLBAR_BOTH)
        elif option == 'text':
            gtktoolbar.set_style(gtk.TOOLBAR_TEXT)
        elif option == 'icons':
            gtktoolbar.set_style(gtk.TOOLBAR_ICONS)
        self.create_base_toolbar(gtktoolbar)
        return gtktoolbar
