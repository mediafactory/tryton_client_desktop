import xmlrpclib
import logging
import socket
import pysocket
import common
from config import CONFIG
import re
import translate
import gettext
import gtk
_ = gettext.gettext

class RPCException(Exception):

    def __init__(self, code, backtrace):
        Exception.__init__(self)
        self.code = code
        self.args = backtrace
        if hasattr(code, 'split'):
            lines = code.split('\n')

            self.type = lines[0].split(' -- ')[0]
            self.message = ''
            if len(lines[0].split(' -- ')) > 1:
                self.message = lines[0].split(' -- ')[1]

            self.data = '\n'.join(lines[2:])
        else:
            self.type = 'error'
            self.message = backtrace
            self.data = backtrace

        self.backtrace = backtrace

        logging.getLogger('rpc.exception').warning('CODE %s: %s' % \
                (str(code), self.message))

class GWInter(object):
    __slots__ = ('_url', '_db', '_user', '_passwd', '_sock', '_obj')

    def __init__(self, url, database, user, passwd, obj='/object'):
        self._url = url
        self._db = database
        self._user = user
        self._obj = obj
        self._passwd = passwd

    def exec_auth(self, method, *args):
        pass

    def execute(self, method, *args):
        pass

class XMLRpcGW(GWInter):
    __slots__ = ('_url', '_db', '_user', '_passwd', '_sock', '_obj')

    def __init__(self, url, database, user, passwd, obj='/object'):
        GWInter.__init__(self, url, database, user, passwd, obj)
        self._sock = xmlrpclib.ServerProxy(url+obj)

    def exec_auth(self, method, *args):
        logging.getLogger('rpc.request').info(str((method, self._db, self._user,
            self._passwd, args)))
        res = self.execute(method, self._user, self._passwd, *args)
        logging.getLogger('rpc.result').debug(str(res))
        return res

    def __convert(self, result):
        if type(result) == type(u''):
            return result.encode('utf-8')
        elif type(result) == type([]):
            return [self.__convert(x) for x in result]
        elif type(result) == type({}):
            newres = {}
            for i in result.keys():
                newres[i] = self.__convert(result[i])
            return newres
        else:
            return result

    def execute(self, method, *args):
        result = getattr(self._sock, method)(self._db, *args)
        return self.__convert(result)

class PySocketGW(GWInter):
    __slots__ = ('_url', '_db', '_user', '_passwd', '_sock', '_obj')

    def __init__(self, url, database, user, passwd, obj='/object'):
        GWInter.__init__(self, url, database, user, passwd, obj)
        self._sock = pysocket.PySocket()
        self._obj = obj[1:]

    def exec_auth(self, method, *args):
        logging.getLogger('rpc.request').info(str((method, self._db, self._user,
            self._passwd, args)))
        res = self.execute(method, self._user, self._passwd, *args)
        logging.getLogger('rpc.result').debug(str(res))
        return res

    def execute(self, method, *args):
        self._sock.connect(self._url)
        self._sock.send((self._obj, method, self._db)+args)
        res = self._sock.receive()
        self._sock.disconnect()
        return res

class RPCSession(object):
    __slots__ = ('_open', '_url', 'user', 'uname', '_passwd', '_gw', 'database',
            'context', 'timezone')
    def __init__(self):
        self._open = False
        self._url = None
        self._passwd = None
        self.user = None
        self.context = {}
        self.uname = None
        self._gw = None
        self.database = None
        self.timezone = 'utc'

    def rpc_exec(self, obj, method, *args):
        try:
            sock = self._gw(self._url, self.database, self.user,
                    self._passwd, obj)
            return sock.execute(method, *args)
        except socket.error, exception:
            from gui import Main
            common.error(_('Connection refused !'), Main.get_main().window,
                    str(exception))
            raise RPCException(69, _('Connection refused!'))
        except xmlrpclib.Fault, exception:
            raise RPCException(exception.faultCode, exception.faultString)

    def rpc_exec_auth_try(self, obj, method, *args):
        if self._open:
            sock = self._gw(self._url, self.database, self.user,
                    self._passwd, obj)
            return sock.exec_auth(method, *args)
        else:
            raise RPCException(1, 'not logged')

    def rpc_exec_auth_wo(self, obj, method, *args):
        try:
            sock = self._gw(self._url, self.database, self.user,
                    self._passwd, obj)
            return sock.exec_auth(method, *args)
        except xmlrpclib.Fault, exception:
            rcp_exception = RPCException(exception.faultCode,
                    exception.faultString)
        except pysocket.PySocketException, exception:
            rpc_exception = RPCException(exception.faultCode,
                    exception.faultString)
        if rpc_exception.code in ('warning', 'UserError'):
            from gui import Main
            common.warning(rcp_exception.data, Main.get_main().window,
                    rpc_exception.message)
            return None
        raise

    def _process_exception(self, exception, obj, method, *args):
        rpc_exception = RPCException(exception.faultCode,
                exception.faultString)
        if rpc_exception.type in ('warning','UserError'):
            if rpc_exception.message in ('ConcurrencyException') \
                    and len(args) > 4:
                if concurrency(args[0], args[2][0], args[4]):
                    if 'read_delta' in args[4]:
                        del args[4]['read_delta']
                    return self.rpc_exec_auth(obj, method, *args)
            else:
                from gui import Main
                common.warning(rpc_exception.data, Main.get_main().window,
                        rpc_exception.message)
        else:
            from gui import Main
            common.error(_('Application Error'), exception.faultCode,
                    Main.get_main().window, exception.faultString)

    def rpc_exec_auth(self, obj, method, *args):
        if self._open:
            try:
                sock = self._gw(self._url, self.database, self.user,
                        self._passwd, obj)
                return sock.exec_auth(method, *args)
            except socket.error, exception:
                from gui import Main
                common.error(_('Connection refused !'), Main.get_main().window,
                        str(exception))
                raise RPCException(69, 'Connection refused!')
            except xmlrpclib.Fault, exception:
                self._process_exception(exception, obj, method, args)
            except pysocket.PySocketException, exception:
                self._process_exception(exception, obj, method, args)
            except Exception, exception:
                from gui import Main
                common.error(_('Application Error'), Main.get_main().window,
                        str(exception))
        else:
            raise RPCException(1, 'not logged')

    def login(self, uname, passwd, url, port, protocol, database):
        _protocol = protocol
        if _protocol == 'http://' or _protocol == 'https://':
            _url = _protocol + url+':'+str(port)+'/xmlrpc'
            _sock = xmlrpclib.ServerProxy(_url+'/common')
            self._gw = XMLRpcGW
            try:
                res = _sock.login(database or '', uname or '', passwd or '')
            except socket.error:
                return -1
            if not res:
                self._open = False
                self.user = False
                return -2
        else:
            _url = _protocol+url+':'+str(port)
            _sock = pysocket.PySocket()
            self._gw = PySocketGW
            try:
                _sock.connect(url, int(port))
                _sock.send(('common', 'login', database or '', uname or '',
                    passwd or ''))
                res = _sock.receive()
                _sock.disconnect()
            except socket.error:
                return -1
            if not res:
                self._open = False
                self.user = False
                return -2
        self._url = _url
        self._open = True
        self.user = res
        self.uname = uname
        self._passwd = passwd
        self.database = database

        self._gw(self._url, self.database, self.user, self._passwd)
        self.context_reload()
        return 1

    def list_db(self, url):
        match = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$',
                url or '')
        if not match:
            return -1
        if match.group(1) == 'http://' or match.group(1) == 'https://':
            sock = xmlrpclib.ServerProxy(url + '/xmlrpc/db')
            try:
                return sock.list()
            except:
                return -1
        else:
            sock = pysocket.PySocket()
            try:
                sock.connect(match.group(2), int(match.group(3)))
                sock.send(('db', 'list'))
                res = sock.receive()
                sock.disconnect()
                return res
            except:
                return -1

    def db_exec_no_except(self, url, method, *args):
        match = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$',
                url or '')
        if match.group(1) == 'http://' or match.group(1) == 'https://':
            sock = xmlrpclib.ServerProxy(url + '/xmlrpc/db')
            return getattr(sock, method)(*args)
        else:
            sock = pysocket.PySocket()
            sock.connect(match.group(2), int(match.group(3)))
            sock.send(('db', method)+args)
            res = sock.receive()
            sock.disconnect()
            return res

    def db_exec(self, url, method, *args):
        res = False
        try:
            res = self.db_exec_no_except(url, method, *args)
        except socket.error:
            from gui import Main
            common.warning(_('Could not contact server!'),
                    Main.get_main().window)
        except xmlrpclib.Fault, exception:
            if exception.faultString == 'AccessDenied:None' \
                    or str(exception) == 'AccessDenied':
                from gui import Main
                common.warning(_('Bad database administrator password!'),
                        Main.get_main().window)
        except pysocket.PySocketException, exception:
            if exception.faultString == 'AccessDenied:None' \
                    or str(exception) == 'AccessDenied':
                from gui import Main
                common.warning(_('Bad database administrator password!'),
                        Main.get_main().window)
        return res

    def context_reload(self):
        self.context = {}
        self.timezone = 'utc'
        # self.user
        context = self.rpc_exec_auth('/object', 'execute', 'ir.values', 'get',
                'meta', False, [('res.user', self.user or False)], False, {},
                True, True, False)
        for ctx in context:
            if ctx[2]:
                self.context[ctx[1]] = ctx[2]
            if ctx[1] == 'lang':
                translate.setlang(ctx[2])
                CONFIG['client.lang'] = ctx[2]
                ids = self.rpc_exec_auth('/object', 'execute', 'res.lang',
                        'search', [('code', '=', ctx[2])])
                if ids:
                    lang = self.rpc_exec_auth('/object', 'execute', 'res.lang',
                            'read', ids, ['direction'])
                    if lang and 'direction' in lang[0]:
                        common.DIRECTION = lang[0]['direction']
                        if common.DIRECTION == 'rtl':
                            gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)
                        else:
                            gtk.widget_set_default_direction(gtk.TEXT_DIR_LTR)
            elif ctx[1] == 'tz':
                self.timezone = self.rpc_exec_auth('/common', 'timezone_get')
                try:
                    import pytz
                except:
                    from gui import Main
                    common.warning(_('Could not find pytz library !\n' \
                            'The timezone functionality will be disable.'),
                            Main.get_main().window)

    def logged(self):
        return self._open

    def logout(self):
        if self._open:
            self._open = False
            self.uname = None
            self.user = None
            self._passwd = None
        else:
            pass

SESSION = RPCSession()
session = SESSION


class RPCProxy(object):

    def __init__(self, resource):
        self.resource = resource
        self.__attrs = {}

    def __getattr__(self, name):
        if not name in self.__attrs:
            self.__attrs[name] = RPCFunction(self.resource, name)
        return self.__attrs[name]


class RPCFunction(object):

    def __init__(self, resource, func_name):
        self.object = resource
        self.func = func_name

    def __call__(self, *args):
        return SESSION.rpc_exec_auth('/object', 'execute', self.object,
                self.func, *args)

def concurrency(resource, obj_id, context, parent):
    dia = glade.XML(GLADE, 'dialog_concurrency_exception', gettext.textdomain())
    win = dia.get_widget('dialog_concurrency_exception')

    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)

    res = win.run()
    parent.present()
    win.destroy()

    if res == gtk.RESPONSE_OK:
        return True
    if res == gtk.RESPONSE_APPLY:
        from gui.window import Window
        Window.create(False, resource, obj_id, [], 'form', None, context,
                'form,tree')
    return False


