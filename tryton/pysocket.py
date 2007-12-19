import socket
import cPickle

DNS_CACHE = {}

class PySocketException(Exception):

    def __init__(self, code, string):
        Exception.__init__(self)
        self.faultCode = code
        self.faultString = string
        self.args = (code, string)

class PySocket:

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.settimeout(120)

    def connect(self, host, port=False):
        if not port:
            buf = host.split('//')[1]
            host, port = buf.split(':')
        if host in DNS_CACHE:
            host = DNS_CACHE[host]
        self.sock.connect((host, int(port)))
        DNS_CACHE[host], port = self.sock.getpeername()

    def disconnect(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def send(self, msg, exception=False, traceback=None):
        print "msg:", msg
        msg = cPickle.dumps([msg, traceback])
        size = len(msg)
        self.sock.send('%8d' % size)
        self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent

    def receive(self):
        buf = ''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            buf += chunk
        size = int(buf)
        buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            chunk = self.sock.recv(size-len(msg))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            msg = msg + chunk
        res = cPickle.loads(msg)
        if isinstance(res[0], Exception):
            if exception:
                raise PySocketException(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]
