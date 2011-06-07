#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from __future__ import with_statement
import os
from tryton.config import get_config_dir

KNOWN_HOSTS_PATH = os.path.join(get_config_dir(), 'known_hosts')


class Fingerprints(dict):

    def __init__(self):
        super(Fingerprints, self).__init__()
        self.load()

    def load(self):
        if not os.path.isfile(KNOWN_HOSTS_PATH):
            return
        with open(KNOWN_HOSTS_PATH) as known_hosts:
            for line in known_hosts.xreadlines():
                line = line.strip()
                try:
                    key, sha1 = line.split(' ')
                    host, port = key.rsplit(':', 1)
                except ValueError:
                    continue
                self[(host, port)] = sha1

    def save(self):
        lines = []
        with open(KNOWN_HOSTS_PATH, 'w') as known_hosts:
            known_hosts.writelines('%s:%s %s' % (host, port, sha1)
                    + os.linesep for (host, port), sha1 in self.iteritems())

    def __setitem__(self, key, value):
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert len(value) == 59 # len of formated sha1
        super(Fingerprints, self).__setitem__(key, value)
        self.save()
