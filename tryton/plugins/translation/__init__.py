#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
from tryton.gui.window import Window

def translate_view(datas, parent):
    model = datas['model']
    Window.create(False, 'ir.translation', [],
            [('model', '=', model)], 'form',
            mode=['tree', 'form'], window=parent)

def get_plugins(model):
    return [
        (_('Translate view'), translate_view),
    ]
