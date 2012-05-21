#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
"Browser"
import gettext
from tryton.signal_event import SignalEvent
from tryton.gui import Main
import tryton.rpc as rpc
from tryton.gui.window.view_browser import ViewBrowser
import tryton.common as common
from tryton.exceptions import TrytonServerError

from tabcontent import TabContent

_ = gettext.gettext


class Browser(SignalEvent, TabContent):
    'Browser'

    toolbar_def = [
    ]

    menu_def = [
    ]

    def __init__(self, model, view_id, context=None, name=False,
            auto_refresh=False):
        super(Browser, self).__init__()

        try:
            view = rpc.execute('model', 'ir.ui.view', 'read',
                    view_id, ['arch'], context)
        except TrytonServerError, exception:
            common.process_exception(exception)
            raise

        self.browser = ViewBrowser(self, view['arch'], context=context)
        self.model = model
        self.view_id = view_id
        self.context = context
        self.auto_refresh = auto_refresh
        self.dialogs = []
        if not name:
            self.name = self.browser.name
        else:
            self.name = name

        self.create_tabcontent()

    def get_toolbars(self):
        return {}

    def widget_get(self):
        return self.browser.widget_get()

    def sig_reload(self, test_modified=True):
        self.browser.reload()
        return True

    def sig_close(self):
        return True

    def __eq__(self, value):
        if not value:
            return False
        if not isinstance(value, Browser):
            return False
        return (self.model == value.model
            and self.view_id == value.view_id
            and self.context == value.context
            and self.name == value.name
            and self.auto_refresh == value.auto_refresh)

    def sig_win_close(self, widget):
        Main.get_main().sig_win_close(widget)

    def set_cursor(self):
        pass