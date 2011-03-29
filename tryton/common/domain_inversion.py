#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import operator
import types

OPERATORS = {
    '=': operator.eq,
    '>': operator.gt,
    '<': operator.lt,
    '<=': operator.le,
    '>=': operator.ge,
    '!=': operator.ne,
    'in': lambda a, b: operator.contains(b, a),
    'not in': lambda a, b: not operator.contains(b, a),
    # Those operators are not supported (yet ?)
    'like': lambda a, b: True,
    'ilike': lambda a, b: True,
    'not like': lambda a, b: True,
    'not ilike': lambda a, b: True,
    'child_of': lambda a, b: True,
    'not child_of': lambda a, b: True,
}

def locale_part(expression, field_name):
    if expression == field_name:
        return 'id'
    if '.' in expression:
        fieldname, local = expression.split('.', 1)
        return local
    return expression

def is_leaf(expression):
    return (isinstance(expression, (list, tuple))
        and len(expression) > 2
        and isinstance(expression[1], basestring)
        and expression[1] in OPERATORS)

def eval_leaf(part, context, boolop=operator.and_):
    field, operand, value = part[:3]
    if '.' in field:
        # In the case where the leaf concerns a m2o then having a value in the
        # evaluation context is deemed suffisant
        return bool(context.get(field.split('.')[0]))
    if operand == '=' and not context[field] and boolop == operator.and_:
        # We should consider that other domain inversion will set a correct
        # value to this field
        return True
    return OPERATORS[operand](context[field], value)

def inverse_leaf(domain):
    if domain in ('AND', 'OR'):
        return domain
    elif is_leaf(domain):
        if 'child_of' in domain[1]:
            if len(domain) == 3:
                return domain
            else:
                return [domain[3]] + domain[1:]
        return domain
    else:
        return map(inverse_leaf, domain)

def eval_domain(domain, context, boolop=operator.and_):
    "compute domain boolean value according to the context"
    if is_leaf(domain):
        return eval_leaf(domain, context, boolop=boolop)
    elif not domain and boolop is operator.and_:
        return True
    elif not domain and boolop is operator.or_:
        return False
    elif domain[0] == 'AND':
        return eval_domain(domain[1:], context)
    elif domain[0] == 'OR':
        return eval_domain(domain[1:], context, operator.or_)
    else:
        return boolop(eval_domain(domain[0], context),
            eval_domain(domain[1:], context, boolop))

def localize_domain(domain, field_name=None):
    "returns only locale part of domain. eg: langage.code -> code"
    if domain in ('AND', 'OR', True, False):
        return domain
    elif is_leaf(domain):
        return [locale_part(domain[0], field_name)] + domain[1:]
    else:
        return [localize_domain(part, field_name) for part in domain]

def unlocalize_domain(domain, fieldname):
    if domain in ('AND', 'OR', True, False):
        return domain
    elif is_leaf(domain):
        return ['%s.%s' % (fieldname, domain[0])] + domain[1:]
    else:
        return [unlocalize_domain(part, fieldname) for part in domain]

def simplify(domain):
    "remove unused domain delimiter"
    if is_leaf(domain):
        return domain
    elif domain in ('OR', 'AND'):
        return domain
    elif (isinstance(domain, list) and len(domain) == 1
        and not is_leaf(domain[0])):
        return simplify(domain[0])
    elif (isinstance(domain, list) and len(domain) == 2
        and domain[0] in ('AND', 'OR')):
        return [simplify(domain[1])]
    else:
        return [simplify(branch) for branch in domain]

def merge(domain, domoperator=None):
    if not domain or domain in ('AND', 'OR'):
        return []
    domain_type = 'OR' if domain[0] == 'OR' else 'AND'
    if is_leaf(domain):
        return [domain]
    elif domoperator is None:
        return [domain_type] + reduce(operator.add,
                [merge(e, domain_type) for e in domain])
    elif domain_type == domoperator:
        return reduce(operator.add, [merge(e, domain_type) for e in domain])
    else:
        # without setting the domoperator
        return [merge(domain)]


def parse(domain):
    if is_leaf(domain):
        return domain
    elif not domain:
        return And([])
    elif domain[0] == 'OR':
        return Or(domain[1:])
    else:
        return And(domain[1:] if domain[0] == 'AND' else domain)

def domain_inversion(domain, symbol, context=None):
    """compute an inversion of the domain eventually the context is used to
    simplify the expression"""
    if context is None:
        context = {}
    expression = parse(domain)
    if symbol not in expression.variables:
        return True
    return expression.inverse(symbol, context)


class And(object):

    def __init__(self, expressions):
        self.branches = map(parse, expressions)
        self.variables = set()
        for expression in self.branches:
            if is_leaf(expression):
                self.variables.add(self.base(expression[0]))
            elif isinstance(expression, And):
                self.variables |= expression.variables

    def base(self, expression):
        return expression if '.' not in expression else expression.split('.')[0]

    def inverse(self, symbol, context):
        result = []
        for part in self.branches:
            if isinstance(part, And):
                part_inversion = part.inverse(symbol, context)
                evaluated = isinstance(part_inversion, types.BooleanType)
                if not evaluated:
                    result.append(part_inversion)
                elif part_inversion:
                    continue
                else:
                    return False
            elif is_leaf(part) and self.base(part[0]) == symbol:
                result.append(part)
            else:
                field, _, _ = part
                if (field not in context
                    or field in context
                    and eval_leaf(part, context, operator.and_)):
                    result.append(True)
                else:
                    return False

        result = filter(lambda e: e is not True, result)
        if result == []:
            return True
        else:
            return simplify(result)


class Or(And):

    def inverse(self, symbol, context):
        result = []
        known_variables = set(context.keys())
        if (symbol not in self.variables
            and not known_variables >= self.variables):
            # In this case we don't know anything about this OR part, we
            # consider it to be True (because people will have the constraint on
            # this part later).
            return True
        for part in self.branches:
            if isinstance(part, And):
                part_inversion = part.inverse(symbol, context)
                evaluated = isinstance(part_inversion, types.BooleanType)
                if symbol not in part.variables:
                    if evaluated and part_inversion:
                        return True
                    continue
                if not evaluated:
                    result.append(part_inversion)
                elif part_inversion:
                    return True
                else:
                    continue
            elif is_leaf(part) and self.base(part[0]) == symbol:
                result.append(part)
            else:
                field, _, _ = part
                field = self.base(field)
                if (field in context
                        and eval_leaf(part, context, operator.or_)):
                    return True
                elif (field in context
                        and not eval_leaf(part, context, operator.or_)):
                    result.append(False)

        result = filter(lambda e: e is not False, result)
        if result == []:
            return False
        else:
            return simplify(['OR'] + result)

# Test stuffs
def test_simple_inversion():
    domain = [['x', '=', 3]]
    assert domain_inversion(domain, 'x') == [['x', '=', 3]]

    domain = []
    assert domain_inversion(domain, 'x') == True
    assert domain_inversion(domain, 'y') == True
    assert domain_inversion(domain, 'x', {'x': 5}) == True
    assert domain_inversion(domain, 'z', {'x': 7}) == True

    domain = [['x.id', '>', 5]]
    assert domain_inversion(domain, 'x') == [['x.id', '>', 5]]

def test_and_inversion():
    domain = [['x', '=', 3], ['y', '>', 5]]
    assert domain_inversion(domain, 'x') == [['x', '=', 3]]
    assert domain_inversion(domain, 'x', {'y': 4}) == False
    assert domain_inversion(domain, 'x', {'y': 6}) == [['x', '=', 3]]

    domain = [['x', '=', 3], ['y', '=', 5]]
    assert domain_inversion(domain, 'z') == True
    assert domain_inversion(domain, 'z', {'x': 2, 'y': 7}) == True
    assert domain_inversion(domain, 'x', {'y': False}) == [['x', '=', 3]]

    domain = [['x.id', '>', 5], ['y', '<', 3]]
    assert domain_inversion(domain, 'y') == [['y', '<', 3]]
    assert domain_inversion(domain, 'y', {'x': 3}) == [['y', '<', 3]]
    assert domain_inversion(domain, 'x') == [['x.id', '>', 5]]

def test_or_inversion():
    domain = ['OR', ['x', '=', 3], ['y', '>', 5], ['z', '=', 'abc']]
    assert domain_inversion(domain, 'x') == [['x', '=', 3]]
    assert domain_inversion(domain, 'x', {'y': 4}) == [['x', '=', 3]]
    assert domain_inversion(domain, 'x', {'y': 4, 'z': 'ab'}) == [['x', '=', 3]]
    assert domain_inversion(domain, 'x', {'y': 7}) == True
    assert domain_inversion(domain, 'x', {'y': 7, 'z': 'b'}) == True
    assert domain_inversion(domain, 'x', {'z': 'abc'}) == True
    assert domain_inversion(domain, 'x', {'y': 4, 'z': 'abc'}) == True

    domain = ['OR', ['x', '=', 3], ['y', '=', 5]]
    assert domain_inversion(domain, 'x', {'y': False}) == [['x', '=', 3]]

    domain = ['OR', ['x', '=', 3], ['y', '>', 5]]
    assert domain_inversion(domain, 'z') == True

    domain = ['OR', ['x.id', '>', 5], ['y', '<', 3]]
    assert domain_inversion(domain, 'y') == [['y', '<', 3]]
    assert domain_inversion(domain, 'y', {'z': 4}) == [['y', '<', 3]]
    assert domain_inversion(domain, 'y', {'x': 3}) == True

    domain = [u'OR', [u'length', u'>', 5], [u'language.code', u'=', u'de_DE']]
    assert domain_inversion(domain, 'length', {'length': 0, 'name': 'n'}) ==\
        [['length', '>', 5]]

def test_orand_inversion():
    domain = ['OR', [['x', '=', 3], ['y', '>', 5], ['z', '=', 'abc']],
        [['x', '=', 4]], [['y', '>', 6]]]
    assert domain_inversion(domain, 'x') == True
    assert domain_inversion(domain, 'x', {'y': 4}) == [[['x', '=', 4]]]
    assert domain_inversion(domain, 'x', {'z': 'abc', 'y': 7}) == True
    assert domain_inversion(domain, 'x', {'y': 7}) == True
    assert domain_inversion(domain, 'x', {'z': 'ab'}) == True

def test_andor_inversion():
    domain = [['OR', ['x', '=', 4], ['y', '>', 6]], ['z', '=', 3]]
    assert domain_inversion(domain, 'z') == [['z', '=', 3]]
    assert domain_inversion(domain, 'z', {'x': 5}) == [['z', '=', 3]]
    assert domain_inversion(domain, 'z', {'x': 5, 'y': 5}) == False
    assert domain_inversion(domain, 'z', {'x': 5, 'y': 7}) == [['z', '=', 3]]

def test_andand_inversion():
    domain = [[['x', '=', 4], ['y', '>', 6]], ['z', '=', 3]]
    assert domain_inversion(domain, 'z') == [['z', '=', 3]]
    assert domain_inversion(domain, 'z', {'x': 5}) == False
    assert domain_inversion(domain, 'z', {'y': 5}) == False
    assert domain_inversion(domain, 'z', {'x': 4, 'y': 7}) == [['z', '=', 3]]

    domain = [[['x', '=', 4], ['y', '>', 6], ['z', '=', 2]], [['w', '=', 2]]]
    assert domain_inversion(domain, 'z', {'x': 4}) == [['z', '=', 2]]

def test_oror_inversion():
    domain = ['OR', ['OR', ['x', '=', 3], ['y', '>', 5]],
        ['OR', ['x', '=', 2], ['z', '=', 'abc']],
        ['OR', ['y', '=', 8], ['z', '=', 'y']]]
    assert domain_inversion(domain, 'x') == True
    assert domain_inversion(domain, 'x', {'y': 4}) == True
    assert domain_inversion(domain, 'x', {'z': 'ab'}) == True
    assert domain_inversion(domain, 'x', {'y': 7}) == True
    assert domain_inversion(domain, 'x', {'z': 'abc'}) == True
    assert domain_inversion(domain, 'x', {'z': 'y'}) == True
    assert domain_inversion(domain, 'x', {'y': 8}) == True
    assert domain_inversion(domain, 'x', {'y': 8, 'z': 'b'}) == True
    assert domain_inversion(domain, 'x', {'y': 4, 'z': 'y'}) == True
    assert domain_inversion(domain, 'x', {'y': 7, 'z': 'abc'}) == True
    assert domain_inversion(domain, 'x', {'y': 4, 'z': 'b'}) == \
            ['OR', [['x', '=', 3]], [['x', '=', 2]]]

def test_parse():
    domain = parse([['x', '=', 5]])
    assert domain.variables == set('x')
    domain = parse(['OR', ['x', '=', 4], ['y', '>', 6]])
    assert domain.variables == set('xy')
    domain = parse([['OR', ['x', '=', 4], ['y', '>', 6]], ['z', '=', 3]])
    assert domain.variables == set('xyz')
    domain = parse([[['x', '=', 4], ['y', '>', 6]], ['z', '=', 3]])
    assert domain.variables == set('xyz')

def test_simplify():
    domain = [['x', '=', 3]]
    assert simplify(domain) == [['x', '=', 3]]
    domain = [[['x', '=', 3]]]
    assert simplify(domain) == [['x', '=', 3]]
    domain = ['OR', ['x', '=', 3]]
    assert simplify(domain) == [['x', '=', 3]]
    domain = ['OR', [['x', '=', 3]], [['y', '=', 5]]]
    assert simplify(domain) == ['OR', [['x', '=', 3]], [['y', '=', 5]]]
    domain = ['OR', ['x', '=', 3], ['AND', ['y', '=', 5]]]
    assert simplify(domain) == ['OR', ['x', '=', 3], ['y', '=', 5]]

def test_merge():
    domain = [['x', '=', 6], ['y', '=', 7]]
    assert merge(domain) == ['AND', ['x', '=', 6], ['y', '=', 7]]
    domain = ['AND', ['x', '=', 6], ['y', '=', 7]]
    assert merge(domain) == ['AND', ['x', '=', 6], ['y', '=', 7]]
    domain = [['z', '=', 8], ['AND', ['x', '=', 6], ['y', '=', 7]]]
    assert merge(domain) == ['AND', ['z', '=', 8], ['x', '=', 6],
        ['y', '=', 7]]
    domain = ['OR', ['x', '=', 1], ['y', '=', 2], ['z', '=', 3]]
    assert merge(domain) == ['OR', ['x', '=', 1], ['y', '=', 2],
        ['z', '=', 3]]
    domain = ['OR', ['x', '=', 1], ['OR', ['y', '=', 2], ['z', '=', 3]]]
    assert merge(domain) == ['OR', ['x', '=', 1], ['y', '=', 2],
        ['z', '=', 3]]
    domain = ['OR', ['x', '=', 1], ['AND', ['y', '=', 2], ['z', '=', 3]]]
    assert merge(domain) == ['OR', ['x', '=', 1], ['AND', ['y', '=', 2],
        ['z', '=', 3]]]
    domain = [['z', '=', 8], ['OR', ['x', '=', 6], ['y', '=', 7]]]
    assert merge(domain) == ['AND', ['z', '=', 8], ['OR', ['x', '=', 6],
        ['y', '=', 7]]]
    domain = ['AND', ['OR', ['a', '=', 1], ['b', '=', 2]],
        ['OR', ['c', '=', 3], ['AND', ['d', '=', 4], ['d2', '=', 6]]],
        ['AND', ['d', '=', 5], ['e', '=', 6]], ['f', '=', 7]]
    assert merge(domain) == ['AND', ['OR', ['a', '=', 1], ['b', '=', 2]],
        ['OR', ['c', '=', 3], ['AND', ['d', '=', 4], ['d2', '=', 6]]],
        ['d', '=', 5], ['e', '=', 6], ['f', '=', 7]]

def test_evaldomain():
    domain = [['x', '>', 5]]
    assert eval_domain(domain, {'x': 6})
    assert not eval_domain(domain, {'x': 4})

    domain = ['OR', ['x', '>', 10], ['x', '<', 0]]
    assert eval_domain(domain, {'x': 11})
    assert eval_domain(domain, {'x': -4})
    assert not eval_domain(domain, {'x': 5})

    domain = [['x', '>', 0], ['OR', ['x', '=', 3], ['x', '=', 2]]]
    assert not eval_domain(domain, {'x': 1})
    assert eval_domain(domain, {'x': 3})
    assert eval_domain(domain, {'x': 2})
    assert not eval_domain(domain, {'x': 4})
    assert not eval_domain(domain, {'x': 5})
    assert not eval_domain(domain, {'x': 6})

    domain = ['OR', ['x', '=', 4], [['x', '>', 6], ['x', '<', 10]]]
    assert eval_domain(domain, {'x': 4})
    assert eval_domain(domain, {'x': 7})
    assert not eval_domain(domain, {'x': 3})
    assert not eval_domain(domain, {'x': 5})
    assert not eval_domain(domain, {'x': 11})

if __name__ == '__main__':
    test_simple_inversion()
    test_and_inversion()
    test_or_inversion()
    test_orand_inversion()
    test_andor_inversion()
    test_andand_inversion()
    test_oror_inversion()
    test_parse()
    test_simplify()
    test_evaldomain()
