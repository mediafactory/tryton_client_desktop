#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk
import pango
import gettext
import socket

from tryton.signal_event import SignalEvent
import tryton.rpc as rpc
import tryton.common as common
from tryton.gui.window.view_form.screen import Screen
from tryton.gui import Main
from tryton.exceptions import TrytonServerError, TrytonServerUnavailable
from tryton.gui.window.nomodal import NoModal
from tryton.common.button import Button
from tryton.common import RPCExecute, RPCException, TRYTON_ICON
_ = gettext.gettext


class Wizard(object):

    def __init__(self, name=False):
        super(Wizard, self).__init__()
        self.widget = gtk.VBox(spacing=3)
        self.toolbar_box = None
        self.widget.show()
        self.name = name or ''
        self.id = None
        self.ids = None
        self.action = None
        self.direct_print = False
        self.email_print = False
        self.email = False
        self.context = None
        self.states = {}
        self.response2state = {}
        self.__processing = False
        self.__waiting_response = False
        self.session_id = None
        self.start_state = None
        self.end_state = None
        self.screen = None
        self.screen_state = None
        self.state = None

    def run(self, action, data, direct_print=False, email_print=False,
            email=None, context=None):
        self.action = action
        self.id = data.get('id')
        self.ids = data.get('ids')
        self.model = data.get('model')
        self.direct_print = direct_print
        self.email_print = email_print
        self.email = email
        self.context = context
        try:
            result = RPCExecute('wizard', action, 'create')
        except RPCException:
            return
        self.session_id, self.start_state, self.end_state = result
        self.state = self.start_state
        self.process()

    def process(self):
        from tryton.action import Action
        if self.__processing or self.__waiting_response:
            return
        try:
            self.__processing = True
            while self.state != self.end_state:
                ctx = self.context.copy()
                ctx['active_id'] = self.id
                ctx['active_ids'] = self.ids
                ctx['active_model'] = self.model
                if self.screen:
                    data = {
                        self.screen_state: self.screen.get_on_change_value(),
                        }
                else:
                    data = {}
                try:
                    result = RPCExecute('wizard', self.action, 'execute',
                        self.session_id, data, self.state, context=ctx)
                except RPCException, rpc_exception:
                    if (not isinstance(rpc_exception.exception,
                            TrytonServerError)
                            or not self.screen):
                        self.state = self.end_state
                    break

                if 'view' in result:
                    self.clean()
                    view = result['view']
                    self.update(view['fields_view'], view['defaults'],
                        view['buttons'])
                    self.screen_state = view['state']
                    self.__waiting_response = True
                else:
                    self.state = self.end_state

                if 'actions' in result:
                    sensitive_widget = self.widget.get_toplevel()
                    if not 'view' in result:
                        self.end()
                    for action in result['actions']:
                        Action._exec_action(*action, context=ctx)
                    if (not 'view' in result
                            or (action[0]['type'] == 'ir.action.wizard'
                                and not sensitive_widget.props.sensitive)):
                        return
                if self.__waiting_response:
                    break

            if self.state == self.end_state:
                self.end()
        finally:
            self.__processing = False

    def destroy(self):
        if self.screen:
            self.screen.destroy()
            del self.screen
        del self.widget

    def end(self):
        try:
            RPCExecute('wizard', self.action, 'delete', self.session_id,
                process_exception=False)
            if self.action == 'ir.module.module.config_wizard':
                rpc.context_reload()
                Main.get_main().sig_win_menu()
        except (TrytonServerError, socket.error, TrytonServerUnavailable):
            pass

    def clean(self):
        for widget in self.widget.get_children():
            self.widget.remove(widget)
        self.states = {}

    def response(self, widget, response):
        self.__waiting_response = False
        state = self.response2state.get(response, self.end_state)
        self.screen.current_view.set_value()
        if (not self.screen.current_record.validate()
                and state != self.end_state):
            self.screen.display()
            return
        self.state = state
        self.process()

    def _get_button(self, definition):
        button = Button(definition)
        self.states[definition['state']] = button
        response = len(self.states)
        self.response2state[response] = definition['state']
        button.show()
        return button

    def _record_modified(self, screen, signal):
        record = screen.current_record
        for button in self.states.itervalues():
            button.state_set(record)

    def update(self, view, defaults, buttons):
        for button in buttons:
            self._get_button(button)

        self.screen = Screen(view['model'], mode=[], context=self.context)
        self.screen.add_view(view, display=True)
        self.screen.widget.show()
        self.screen.signal_connect(self, 'record-modified',
            self._record_modified)

        title = gtk.Label()
        title.set_use_markup(True)
        title.modify_font(pango.FontDescription("14"))
        title.set_label('<b>' + self.screen.current_view.title + '</b>')
        title.set_padding(20, 4)
        title.set_alignment(0.0, 0.5)
        title.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        title.show()

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

        hbox = gtk.HBox()
        hbox.pack_start(title, expand=True, fill=True)
        hbox.pack_start(vbox, expand=False, fill=True, padding=20)
        hbox.show()

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame.add(hbox)
        frame.show()

        eb = gtk.EventBox()
        eb.add(frame)
        eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))
        eb.show()

        self.widget.pack_start(eb, expand=False, fill=True, padding=3)

        if self.toolbar_box:
            self.widget.pack_start(self.toolbar_box, False, True)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.add(self.screen.widget)
        viewport.show()
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.add(viewport)
        self.scrolledwindow.show()

        self.widget.pack_start(self.scrolledwindow)

        self.screen.new(default=False)
        self.screen.current_record.set_default(defaults, modified=True)
        self.screen.set_cursor()


class WizardForm(Wizard, SignalEvent):
    "Wizard"

    def __init__(self, name=False):
        super(WizardForm, self).__init__(name=name)
        self.toolbar_box = gtk.HBox()
        self.hbuttonbox = gtk.HButtonBox()
        self.hbuttonbox.set_spacing(5)
        self.hbuttonbox.set_layout(gtk.BUTTONBOX_END)
        self.hbuttonbox.show()
        self.widget.pack_start(self.toolbar_box, False, True)
        self.dialogs = []

        self.handlers = {
            'but_close': self.sig_close
        }

    def clean(self):
        super(WizardForm, self).clean()
        for button in self.hbuttonbox.get_children():
            self.hbuttonbox.remove(button)

    def _get_button(self, state):
        button = super(WizardForm, self)._get_button(state)
        response = len(self.states)
        button.connect('clicked', self.response, response)
        self.hbuttonbox.pack_start(button)
        return button

    def update(self, view, defaults, buttons):
        super(WizardForm, self).update(view, defaults, buttons)
        self.widget.pack_start(self.hbuttonbox, expand=False, fill=True)

    def sig_close(self):
        if self.end_state in self.states:
            self.states[self.end_state].clicked()
        return self.state == self.end_state

    def destroy(self):
        if self.toolbar_box.get_children():
            toolbar = self.toolbar_box.get_children()[0]
            self.toolbar_box.remove(toolbar)
        super(WizardForm, self).destroy()

    def end(self):
        super(WizardForm, self).end()
        Main.get_main()._win_del(self.widget)

    def set_cursor(self):
        if self.screen:
            self.screen.set_cursor()


class WizardDialog(Wizard, NoModal):

    def __init__(self, name=False):
        if not name:
            name = _('Wizard')
        Wizard.__init__(self, name=name)
        NoModal.__init__(self)
        self.dia = gtk.Dialog(self.name, self.parent,
            gtk.DIALOG_DESTROY_WITH_PARENT)
        self.dia.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dia.set_icon(TRYTON_ICON)
        if hasattr(self.dia, 'set_deletable'):
            self.dia.set_deletable(False)
        self.dia.connect('close', self.close)
        self.dia.connect('response', self.response)
        self.dia.connect('state-changed', self.state_changed)

        self.accel_group = gtk.AccelGroup()
        self.dia.add_accel_group(self.accel_group)

        self.dia.vbox.add(self.widget)

        self.register()

    def clean(self):
        super(WizardDialog, self).clean()
        hbuttonbox = self.dia.get_action_area()
        for button in hbuttonbox.get_children():
            hbuttonbox.remove(button)

    def _get_button(self, definition):
        button = super(WizardDialog, self)._get_button(definition)
        response = len(self.states)
        self.dia.add_action_widget(button, response)
        if definition['default']:
            button.set_flags(gtk.CAN_DEFAULT)
            button.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Return, gtk.gdk.CONTROL_MASK,
                gtk.ACCEL_VISIBLE)
            self.dia.set_default_response(response)
        return button

    def update(self, view, defaults, buttons):
        super(WizardDialog, self).update(view, defaults, buttons)
        sensible_allocation = self.sensible_widget.get_allocation()
        self.dia.set_default_size(int(sensible_allocation.width * 0.9),
            int(sensible_allocation.height * 0.9))
        self.dia.show()
        common.center_window(self.dia, self.parent, self.sensible_widget)

    def destroy(self):
        super(WizardDialog, self).destroy()
        self.dia.destroy()
        NoModal.destroy(self)
        main = Main.get_main()
        if self.parent == main.window:
            current_form = main.get_page()
            if current_form:
                for dialog in current_form.dialogs:
                    dialog.show()
        if self.page.dialogs:
            dialog = self.page.dialogs[-1]
        else:
            dialog = self.page
        if hasattr(dialog, 'screen'):
            dialog.screen.reload(written=True)

    def end(self):
        super(WizardDialog, self).end()
        self.destroy()

    def close(self, widget, event=None):
        widget.emit_stop_by_name('close')
        return True

    def show(self):
        self.dia.show()

    def hide(self):
        self.dia.hide()

    def state_changed(self, widget, state):
        if self.dia.props.sensitive and state == gtk.STATE_INSENSITIVE:
            self.process()
