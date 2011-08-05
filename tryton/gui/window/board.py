#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
"Board"
import gettext
import gtk
from tryton.config import CONFIG
from tryton.signal_event import SignalEvent
from tryton.gui import Main
import tryton.rpc as rpc
from tryton.gui.window.view_board import ViewBoard
import tryton.common as common
from tryton.exceptions import TrytonServerError

from tabcontent import TabContent

_ = gettext.gettext


class Board(SignalEvent, TabContent):
    'Board'

    toolbar_def = [
        ('new', 'tryton-new', _('New'), _('Create a new record'), None),
        ('save', 'tryton-save', _('Save'), _('Save this record'), None),
        ('switch', 'tryton-fullscreen', _('Switch'), _('Switch view'),
            None),
        ('reload', 'tryton-refresh', _('_Reload'), _('Reload'),
            'sig_reload'),
    ]

    menu_def = [
        (_('_New'), 'tryton-new', None, '<tryton>/Form/New'),
        (_('_Save'), 'tryton-save', None, '<tryton>/Form/Save'),
        (_('_Switch View'), 'tryton-fullscreen', None,
            '<tryton>/Form/Switch View'),
        (_('_Reload/Undo'), 'tryton-refresh', 'sig_reload',
            '<tryton>/Form/Reload'),
        (_('_Delete...'), 'tryton-delete', None, '<tryton>/Form/Delete'),
        (_('_Close Tab'), 'tryton-close', 'sig_win_close',
            '<tryton>/Form/Close'),
    ]

    def __init__(self, model, view_id, context=None, name=False,
            auto_refresh=False):
        super(Board, self).__init__()

        try:
            view = rpc.execute('model', 'ir.ui.view', 'read',
                    view_id, ['arch'], context)
        except TrytonServerError, exception:
            common.process_exception(exception)
            raise

        self.board = ViewBoard(view['arch'], context=context)
        self.model = model
        self.view_id = view_id
        self.context = context
        self.auto_refresh = auto_refresh
        self.dialogs = []
        if not name:
            self.name = self.board.name
        else:
            self.name = name

        self.create_tabcontent()

    def get_toolbars(self):
        return {}

    def widget_get(self):
        return self.board.widget_get()

    def sig_reload(self, test_modified=True):
        self.board.reload()
        return True

    def sig_close(self):
        return True

    def __eq__(self, value):
        if not value:
            return False
        if not isinstance(value, Board):
            return False
        return (self.model == value.model
            and self.view_id == value.view_id
            and self.context == value.context
            and self.name == value.name
            and self.auto_refresh == value.auto_refresh)

    def sig_win_close(self, widget):
        Main.get_main().sig_win_close(widget)
