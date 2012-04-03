#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
"Preference"
import gettext
import gtk
import copy
from tryton.gui.window.view_form.screen import Screen
from tryton.config import TRYTON_ICON
import tryton.common as common
from tryton.common import RPCExecute, RPCException

_ = gettext.gettext


class Preference(object):
    "Preference window"

    def __init__(self, user):
        self.parent = common.get_toplevel_window()
        self.win = gtk.Dialog(_('Preferences'), self.parent,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.win.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.win.set_has_separator(False)
        self.win.set_icon(TRYTON_ICON)

        self.accel_group = gtk.AccelGroup()
        self.win.add_accel_group(self.accel_group)

        self.but_cancel = self.win.add_button(gtk.STOCK_CANCEL,
                gtk.RESPONSE_CANCEL)
        self.but_ok = self.win.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.but_ok.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Return, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        self.win.set_default_response(gtk.RESPONSE_OK)

        try:
            view = RPCExecute('model', 'res.user',
                'get_preferences_fields_view')
        except RPCException:
            self.win.destroy()
            self.win = None
            return

        title = gtk.Label(_('Edit User Preferences'))
        title.show()
        self.win.vbox.pack_start(title, expand=False, fill=True)
        self.screen = Screen('res.user', mode=[])
        self.screen.add_view(view)
        self.screen.new(default=False)

        try:
            preferences = RPCExecute('model', 'res.user', 'get_preferences',
                False)
        except RPCException:
            self.win.destroy()
            self.win = None
            return
        self.screen.current_record.set(preferences)
        self.screen.current_record.validate(softvalidation=True)
        self.screen.screen_container.set(self.screen.current_view.widget)
        self.screen.display(set_cursor=True)

        self.screen.widget.show()
        self.win.vbox.pack_start(self.screen.widget)
        self.win.set_title(_('Preference'))

        width, height = self.parent.get_size()
        self.win.set_default_size(int(width * 0.9), int(height * 0.9))

        self.win.show()

    def run(self):
        "Run the window"
        if not self.win:
            return False
        res = False
        while True:
            if self.win.run() == gtk.RESPONSE_OK:
                if self.screen.current_record.validate():
                    vals = copy.copy(self.screen.get(get_modifiedonly=True))
                    if 'password' in vals:
                        password = common.ask(_('Current Password:'),
                            visibility=False)
                        if not password:
                            break
                    else:
                        password = False
                    try:
                        RPCExecute('model', 'res.user', 'set_preferences',
                            vals, password)
                    except RPCException:
                        continue
                    res = True
                    break
            else:
                break
        self.parent.present()
        self.win.destroy()
        return res
