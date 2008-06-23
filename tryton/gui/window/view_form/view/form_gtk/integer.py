#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
from char import Char
import locale


class Integer(Char):
    "Integer"

    def __init__(self, window, parent, model, attrs=None):
        super(Integer, self).__init__(window, parent, model=model, attrs=attrs)
        self.entry.set_max_length(0)
        self.entry.set_alignment(1.0)
        self.entry.connect('insert_text', self.sig_insert_text)

    def set_value(self, model, model_field):
        try:
            value = locale.atoi(self.entry.get_text())
        except:
            value = 0
        return model_field.set_client(model, value)

    def display(self, model, model_field):
        super(Char, self).display(model, model_field)
        if not model_field:
            self.entry.set_text('')
            return False
        self.entry.set_text(locale.format('%d',
            model_field.get(model) or 0, True))

    def sig_insert_text(self, entry, new_text, new_text_length, position):
        value = entry.get_text()
        position = entry.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            if new_value == '-':
                return
            locale.atoi(new_value)
        except:
            entry.stop_emission('insert-text')
