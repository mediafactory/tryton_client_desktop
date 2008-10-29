#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import common
import os
import imp
import gettext

_ = gettext.gettext

PLUGINS_PATH = os.path.join(os.path.dirname(__file__), 'plugins')
MODULES = []

if os.path.isdir(PLUGINS_PATH):
    for plugin in os.listdir(PLUGINS_PATH):
        module = os.path.splitext(plugin)[0]
        try:
            module = imp.load_module(module, *imp.find_module(module, [PLUGINS_PATH]))
            MODULES.append(module)
        except Exception, exception:
            continue

def execute(datas, parent):
    result = {}

    for module in MODULES:
        try:
            for name, func in module.get_plugins(datas['model']):
                result[name] = func
        except Exception, exception:
            continue
    if not result:
        common.message(_('No available plugin for this resource!'), parent)
        return False
    res = common.selection(_('Choose a Plugin'), result, parent, alwaysask=True)
    if res:
        res[1](datas, parent)
    return True
