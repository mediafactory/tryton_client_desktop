#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gobject
import gettext
import re
import tryton.common as common
from tryton.config import CONFIG, GLADE, TRYTON_ICON, PIXMAPS_DIR
import tryton.rpc as rpc

_ = gettext.gettext


class DBCreate(object):
    def server_connection_state(self, state):
        """
        Method to set the server connection information depending on the
        connection state. If state is True, the connection string will shown.
        Otherwise the wrong connection string will be shown plus an additional
        errormessage, colored in red. In this case, all entryboxes set
        insensitive
        """
        if state:
            self.entry_serverpasswd.set_sensitive(True)
            self.entry_dbname.set_sensitive(True)
            self.entry_adminpasswd.set_sensitive(True)
            self.entry_adminpasswd2.set_sensitive(True)
            self.entry_server_connection.modify_text(gtk.STATE_INSENSITIVE, \
                gtk.gdk.color_parse(common.COLOR_SCHEMES["black"]))
            self.tooltips.set_tip(self.entry_server_connection,_("This is the URL of " \
            "the Tryton server. Use server 'localhost' and port '8070' if " \
            "the server is installed on this computer. Click on 'Change' to " \
            "change the address."), None)
        else:
            self.entry_serverpasswd.set_sensitive(False)
            self.entry_dbname.set_sensitive(False)
            self.entry_adminpasswd.set_sensitive(False)
            self.entry_adminpasswd2.set_sensitive(False)
            self.entry_server_connection.set_editable(False)
            self.entry_server_connection.set_sensitive(False)
            self.entry_server_connection.set_text( \
                self.entry_server_connection.get_text()
                + "  " + _("No connection!"))
            self.entry_server_connection.modify_text(gtk.STATE_INSENSITIVE, \
                gtk.gdk.color_parse(common.COLORS["invalid"]))
            self.tooltips.set_tip(self.entry_server_connection, _( \
                "Can not connect to the Tryton server!\n" \
                "1. Try to check if the Tryton server is running.\n" \
                "2. Find out on which address and port it is listen.\n" \
                "3. If there is a firewall between the server and this " \
                "client, make shure that the Tryton server address and port " \
                "(usually 8070) are not blocked.\n" \
                "Click on 'Change' to change the address."), None)
        return state

    def server_change(self, widget, parent):
        """
        This method checks the server connection via host and port. If the
        connection is successfull, it query the language list and pass true
        state to the GUI. Otherwise it pass false state to the GUI.
        """
        res = common.request_server(self.entry_server_connection, parent)
        if not res:
            return False
        host, port = res
        try:
            if self.combo_language and host and port:
                common.refresh_langlist(self.combo_language, host, port)
            self.server_connection_state(True)
        except:
            self.server_connection_state(False)
            return False
        return True

    def event_passwd_clear(self, widget, event, data=None):
        """
        This event method clear the text in a widget if CTRL-u
        is pressed.
        """
        if  (event.keyval == gtk.keysyms.u) \
            and (event.state & gtk.gdk.CONTROL_MASK):
            widget.set_text("")

    def event_show_button_create(self, widget, event, data=None):
        """
        This event method decide by rules if the Create button will be
        sensitive or insensitive. The general rule is, all given fields
        must be filled, then the Create button is set to sensitive. This
        event method doesn't check the valid of single entrys.
        """
        if  self.entry_server_connection.get_text() !=  "" \
            and self.entry_serverpasswd.get_text() != "" \
            and self.entry_dbname.get_text() != "" \
            and self.combo_language.get_active() != -1 \
            and self.entry_adminpasswd.get_text() != "" \
            and self.entry_adminpasswd2.get_text() != "":
            widget.unset_flags(gtk.HAS_DEFAULT)
            self.button_create.set_sensitive(True)
            self.button_create.set_flags(gtk.CAN_DEFAULT)
            self.button_create.set_flags(gtk.HAS_DEFAULT)
            self.button_create.set_flags(gtk.CAN_FOCUS)
            self.button_create.set_flags(gtk.RECEIVES_DEFAULT)
            self.button_create.grab_default()

        else:
            self.button_create.set_sensitive(False)

    def entry_insert_text(self, entry, new_text, new_text_length, position):
        """
        This event method checks each text input for the PostgreSQL
        database name. It allows the following rules: 
        - Allowed characters are alpha-nummeric [A-Za-z0-9] and underscore (_)
        - First character must be a letter
        """
        def _move_cursor(entry, pos):
            """
            Helper function for entry_insert_text. It is used to position
            the cursor for right and wron inputs correctly.
            """
            entry.set_position(pos)
            return False

        if (new_text.isalnum() or new_text == '_' ):
            _hid = entry.get_data('handlerid')
            entry.handler_block(_hid)
            _pos = entry.get_position()
            if _pos == 0 and not new_text.isalpha():
                new_text = ""
            _pos = entry.insert_text(new_text, _pos)
            entry.handler_unblock(_hid)
            gobject.idle_add(_move_cursor, entry, _pos)
        entry.stop_emission("insert-text")

    def __init__(self, sig_login):
        """
        This method defines the complete GUI.
        """
        self.dialog = gtk.Dialog(
            title =  _("Create new database"),
            parent = None,
            flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
            | gtk.WIN_POS_CENTER_ON_PARENT,
        )
        self.dialog.set_has_separator(False)
        self.dialog.set_size_request(700, 301)
        self.dialog.set_icon(TRYTON_ICON)
        # This event is needed for controlling the button_create
        self.dialog.connect("key-press-event", self.event_show_button_create)
        self.tooltips = gtk.Tooltips()
        self.dialog.add_button("gtk-cancel", \
            gtk.RESPONSE_CANCEL)
        self.button_create = gtk.Button(_('C_reate'))
        self.button_create.set_flags(gtk.CAN_DEFAULT)
        self.button_create.set_flags(gtk.HAS_DEFAULT)
        self.button_create.set_sensitive(False)
        img_connect = gtk.Image()
        img_connect.set_from_stock('tryton-new', gtk.ICON_SIZE_BUTTON)
        self.button_create.set_image(img_connect)
        self.tooltips.set_tip(self.button_create, _('Create the new Tryton ' \
            'database.'))
        self.dialog.add_action_widget(self.button_create, gtk.RESPONSE_OK)
        self.dialog.set_default_response(gtk.RESPONSE_OK)

        dialog_vbox = gtk.VBox()
        table = gtk.Table(9, 3, False)
        table.set_border_width(10)
        table.set_row_spacings(3)
        table.set_col_spacings(3)

        label_server_setup = gtk.Label()
        label_server_setup.set_markup("<b>"+ _("Tryton Server Setup:")+ "</b>")
        label_server_setup.set_justify(gtk.JUSTIFY_LEFT)
        label_server_setup.set_alignment(0, 1)
        label_server_setup.set_padding( 9, 5)
        table.attach(label_server_setup, 0, 3, 0, 1, xoptions=gtk.FILL)
        label_server = gtk.Label(_("Server connection:"))
        label_server.set_alignment(1, 0.5)
        label_server.set_padding(3, 3)
        table.attach(label_server, 0, 1, 1, 2, xoptions=gtk.FILL)
        self.entry_server_connection = gtk.Entry()
        self.entry_server_connection.set_sensitive(False)
        self.entry_server_connection.unset_flags(gtk.CAN_FOCUS)
        self.entry_server_connection.set_editable(False)
        self.entry_server_connection.set_text("http://localhost:8070")
        table.attach(self.entry_server_connection, 1, 2, 1, 2)
        self.tooltips.set_tip(self.entry_server_connection, _("This is the URL of " \
            "the Tryton server. Use server 'localhost' and port '8070' if " \
            "the server is installed on this computer. Click on 'Change' to " \
            "change the address."), None)
        self.button_server_change = gtk.Button(_("C_hange"), stock=None,
             use_underline=True)
        img_button_server_change = gtk.Image()
        img_button_server_change.set_from_stock('tryton-preferences-system', \
            gtk.ICON_SIZE_BUTTON)
        self.button_server_change.set_image(img_button_server_change)
        table.attach(self.button_server_change, 2, 3, 1, 2, yoptions=False, xoptions=gtk.FILL)
        self.tooltips.set_tip(self.button_server_change, _("Setup the Tryton " \
            "server connection..."), None)
        label_serverpasswd = gtk.Label(_("Server password:"))
        label_serverpasswd.set_justify(gtk.JUSTIFY_RIGHT)
        label_serverpasswd.set_alignment(1, 0.5)
        label_serverpasswd.set_padding( 3, 3)
        table.attach(label_serverpasswd, 0, 1, 2, 3, xoptions=gtk.FILL)
        self.entry_serverpasswd = gtk.Entry()
        self.entry_serverpasswd.set_visibility(False)
        self.entry_serverpasswd.set_activates_default(True)
        table.attach(self.entry_serverpasswd, 1, 3, 2, 3)
        self.tooltips.set_tip(self.entry_serverpasswd, _("This is the " \
            "password for Tryton administration. It doesn't belong to a " \
            "Tryton user. This password is usually defined in the trytond " \
            "configuration."), None)
        self.entry_serverpasswd.connect("key-press-event", \
            self.event_passwd_clear)

        hseparator = gtk.HSeparator()
        table.attach(hseparator, 0, 3, 3, 4)

        label_dbname = gtk.Label()
        label_dbname.set_markup("<b>" + _("New database setup:")  + "</b>")
        label_dbname.set_justify(gtk.JUSTIFY_LEFT)
        label_dbname.set_alignment(0, 1)
        label_dbname.set_padding( 9, 5)
        table.attach(label_dbname, 0, 3, 4, 5, xoptions=gtk.FILL)
        label_dbname = gtk.Label(_("Database name:"))
        label_dbname.set_justify(gtk.JUSTIFY_RIGHT)
        label_dbname.set_padding( 3, 3)
        label_dbname.set_alignment(1, 0.5)
        table.attach(label_dbname, 0, 1, 5, 6, xoptions=gtk.FILL)
        self.entry_dbname = gtk.Entry()
        self.entry_dbname.set_max_length(63)
        self.entry_dbname.set_width_chars(16)
        self.entry_dbname.set_activates_default(True)
        table.attach(self.entry_dbname, 1, 3, 5, 6)
        self.tooltips.set_tip(self.entry_dbname, _("Choose the name of the new " \
            "database.\n" \
            "Allowed characters are alphanumerical or _ (underscore)\n" \
            "You need to avoid all accents, space or special characters! " \
            "Example: tryton"), None)
        handlerid = self.entry_dbname.connect("insert-text", \
            self.entry_insert_text)
        self.entry_dbname.set_data('handlerid', handlerid)
        label_language = gtk.Label(_("Default language:"))
        label_language.set_justify(gtk.JUSTIFY_RIGHT)
        label_language.set_alignment(1, 0.5)
        label_language.set_padding( 3, 3)
        table.attach(label_language, 0, 1, 6, 7, xoptions=gtk.FILL)
        eventbox_language = gtk.EventBox()
        self.combo_language = gtk.combo_box_new_text()
        eventbox_language.add(self.combo_language)
        table.attach(eventbox_language, 1, 3, 6, 7)
        self.tooltips.set_tip(eventbox_language, _("Choose the default " \
            "language that will be installed for this database. You will " \
            "be able to install new languages after installation through " \
            "the administration menu."), None)
        label_adminpasswd = gtk.Label(_("Admin password:"))
        label_adminpasswd.set_justify(gtk.JUSTIFY_RIGHT)
        label_adminpasswd.set_padding( 3, 3)
        label_adminpasswd.set_alignment(1, 0.5)
        table.attach(label_adminpasswd, 0, 1, 7, 8, xoptions=gtk.FILL)
        self.entry_adminpasswd = gtk.Entry()
        self.entry_adminpasswd.set_visibility(False)
        self.entry_adminpasswd.set_activates_default(True)
        self.tooltips.set_tip(self.entry_adminpasswd, _("Choose a password for " \
            "the admin user of the new database. With these credentials you " \
            "are later able to login into the database:\n" \
            "User name: admin\n" \
            "Password: <The password you set here>"), None)
        table.attach(self.entry_adminpasswd, 1, 3, 7, 8)
        self.entry_adminpasswd.connect("key-press-event", \
            self.event_passwd_clear)
        label_adminpasswd2 = gtk.Label(_("Confirm admin password:"))
        label_adminpasswd2.set_justify(gtk.JUSTIFY_RIGHT)
        label_adminpasswd2.set_padding( 3, 3)
        label_adminpasswd2.set_alignment(1, 0.5)
        table.attach(label_adminpasswd2, 0, 1, 8, 9, xoptions=gtk.FILL)
        self.entry_adminpasswd2 = gtk.Entry()
        self.entry_adminpasswd2.set_visibility(False)
        self.entry_adminpasswd2.set_activates_default(True)
        self.tooltips.set_tip(self.entry_adminpasswd2, _("Type the Admin " \
            "password again"), None)
        table.attach(self.entry_adminpasswd2, 1, 3, 8, 9)
        self.entry_adminpasswd2.connect("key-press-event", \
            self.event_passwd_clear)
        self.entry_serverpasswd.grab_focus()
        dialog_vbox.pack_start(table)
        self.dialog.vbox.pack_start(dialog_vbox)
        self.sig_login = sig_login

    def run(self, parent):
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        self.dialog.set_transient_for(parent)
        self.dialog.show_all()

        pass_widget = self.entry_serverpasswd
        change_button = self.button_server_change
        admin_passwd = self.entry_adminpasswd
        admin_passwd2 = self.entry_adminpasswd2

        change_button.connect_after('clicked', self.server_change, self.dialog)
        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])
        url = '%s:%d' % (host, port)
        self.entry_server_connection.set_text(url)

        liststore = gtk.ListStore(str, str)
        self.combo_language.set_model(liststore)
        try:
            common.refresh_langlist(self.combo_language, host, port)
        except:
            self.button_create.set_sensitive(False)

        while True:
            res = self.dialog.run()
            dbname = self.entry_dbname.get_text()
            url = self.entry_server_connection.get_text()
            url_m = re.match('^([\w.\-]+):(\d{1,5})', \
                url or '')
            langidx = self.combo_language.get_active_iter()
            langreal = langidx \
                and self.combo_language.get_model().get_value(langidx, 1)
            passwd = pass_widget.get_text()
            if res == gtk.RESPONSE_OK:
                if (not dbname) \
                    or (not re.match('^[a-zA-Z][a-zA-Z0-9_]+$', dbname)):
                    common.warning(_('The database name is restricted to ' \
                        'alpha-nummerical characters and "_" (underscore). ' \
                        'It must begin with a letter and max. sized to 63 ' \
                        'characters at all.\n' \
                        'Try to avoid all accents, space ' \
                        'and any other special characters.'), parent, \
                        _('Wrong characters in database name!'))
                    continue
                elif admin_passwd.get_text() != admin_passwd2.get_text():
                    common.warning(_("The new admin password " \
                        "doesn't match to the retyped password.\n" \
                        "Try to type the same passwords in the " \
                        "admin password and the confirm admin password " \
                        "fields again."), parent, \
                        _("Passwords doesn't match!"))
                    continue
                elif not admin_passwd.get_text():
                    common.warning(_("Admin password and confirmation are " \
                        "required to create a new Tryton database."), \
                        parent, _('Missing admin password!'))
                    continue
                elif url_m.group(1) \
                    and int(url_m.group(2)) \
                    and dbname \
                    and langreal \
                    and passwd \
                    and admin_passwd.get_text():
                    try:
                        if rpc.db_exec( url_m.group(1), int(url_m.group(2)), \
                                'db_exist', dbname):
                            common.warning(_("Database with the same name " \
                                "already exists.\n" \
                                "Try another database name."), parent, \
                                _("Databasename already exist!"))
                            self.entry_dbname.set_text("")
                            self.entry_dbname.grab_focus()
                            continue
                        else: # Everything runs fine, break the block here
                            if url_m:
                                CONFIG['login.server'] = host = url_m.group(1)
                                CONFIG['login.port'] = port = url_m.group(2)
                            rpc.db_exec(host, int(port), 'create', passwd, \
                                dbname, langreal, admin_passwd.get_text())
                            from tryton.gui.main import Main
                            Main.get_main().refresh_ssl()
                            common.message( _("You can now connect to the " \
                                "new database, with the following login:\n" \
                                "User name: admin\n" \
                                "Password:<Admin Password>"), \
                                parent)
                            parent.present()
                            self.dialog.destroy()
                            self.sig_login(dbname=dbname)
                            break
                    except Exception, exception:
                        if str(exception[0]) == "AccessDenied":
                            common.warning(_("Sorry, the Tryton server " \
                                "password seems wrong. Please type again.") \
                                , parent, _("Access denied!"))
                            self.entry_serverpasswd.set_text("")
                            self.entry_serverpasswd.grab_focus()
                            continue
                        else: # Unclassified error
                            common.warning(_("Can't create the Tryton " \
                                "database, caused by an unknown reason.\n" \
                                "If there is a database created, it could " \
                                "be broken. Maybe drop this database! " \
                                "Please check the error message for " \
                                "possible informations.\n" \
                                "Error message:\n") + str(exception[0]), \
                                parent, _("Error creating Tryton database!"))
                        parent.present()
                        self.dialog.destroy()
                        rpc.logout()
                        from tryton.gui.main import Main
                        Main.get_main().refresh_ssl()
                    break
            break
        parent.present()
        self.dialog.destroy()

