import time
import datetime
import tryton.rpc as rpc
from tryton.wizard import Wizard
#import tryton.printer
from tryton.common import message, error, selection
from tryton.gui.window import Window
import gettext

_ = gettext.gettext

class Action(object):

    @staticmethod
    def exec_report(name, data, context=None):
        if context is None:
            context = {}
        datas = data.copy()
        ids = datas['ids']
        del datas['ids']
        if not ids:
            ids =  rpc.session.rpc_exec_auth('/object', 'execute',
                    datas['model'], 'search', [])
            if ids == []:
                from tryton.gui import Main
                message(_('Nothing to print!'), Main.get_main().window)
                return False
            datas['id'] = ids[0]
        try:
            ctx = rpc.session.context.copy()
            ctx.update(context)
            report_id = rpc.session.rpc_exec_auth('/report', 'report', name,
                    ids, datas, ctx)
            state = False
            attempt = 0
            while not state:
                val = rpc.session.rpc_exec_auth('/report', 'report_get',
                        report_id)
                state = val['state']
                if not state:
                    time.sleep(1)
                    attempt += 1
                if attempt > 200:
                    from tryton.gui import Main
                    message(_('Printing aborted, too long delay !'),
                            Main.get_main().window)
                    return False
            printer.print_data(val)
        except rpc.RPCException, exp:
            from tryton.gui import Main
            error(_('Error: ') + str(exp.type), exp.message,
                    Main.get_main().window, exp.data)
        return True

    @staticmethod
    def execute(act_id, datas, action_type=None, context=None):
        if context is None:
            context = {}
        ctx = rpc.session.context.copy()
        ctx.update(context)
        if not action_type:
            res = rpc.session.rpc_exec_auth('/object', 'execute',
                    'ir.actions.actions', 'read', act_id, ['type'], ctx)
            if not res:
                raise Exception, 'ActionNotFound'
            action_type = res['type']
        res = rpc.session.rpc_exec_auth('/object', 'execute', action_type,
                'read', act_id, False, ctx)
        Action._exec_action(res, datas)

    @staticmethod
    def _exec_action(action, datas=None, context=None):
        if context is None:
            context = {}
        if datas is None:
            datas = {}
        if 'type' not in action:
            return
        from tryton.gui import Main
        win = Main.get_main().window
        if 'window' in datas:
            win = datas['window']
            del datas['window']

        if action['type'] == 'ir.actions.act_window':
            for key in (
                    'res_id',
                    'res_model',
                    'view_type',
                    'limit',
                    'auto_refresh',
                    ):
                datas[key] = action.get(key, datas.get(key, None))

            if datas['limit'] is None or datas['limit'] == 0:
                datas['limit'] = 80

            view_ids = False
            datas['view_mode'] = None
            if action.get('views', []):
                view_ids = [x[0] for x in action['views']]
                datas['view_mode'] = [x[1] for x in action['views']]
            elif action.get('view_id', False):
                view_ids = [action['view_id'][0]]

            if not action.get('domain', False):
                action['domain'] = '[]'
            ctx = {
                    'active_id': datas.get('id',False),
                    'active_ids': datas.get('ids',[]),
                    'user': rpc.session.user,
                    }
            ctx.update(eval(action.get('context','{}'), ctx.copy()))
            ctx.update(context)

            domain_context = ctx.copy()
            domain_context['time'] = time
            domain_context['datetime'] = datetime
            domain = eval(action['domain'], domain_context)

            if datas.get('domain', False):
                domain.append(datas['domain'])

            Window.create(view_ids, datas['res_model'], datas['res_id'], domain,
                    action['view_type'], win, ctx,
                    datas['view_mode'], name=action.get('name', False),
                    limit=datas['limit'], auto_refresh=datas['auto_refresh'])
        elif action['type'] == 'ir.actions.wizard':
            Wizard.execute(action['wiz_name'], datas, win,
                    context=context)
        elif action['type'] == 'ir.actions.report.custom':
            datas['report_id'] = action['report_id']
            Action.exec_report('custom', datas)

        elif action['type'] == 'ir.actions.report.xml':
            Action.exec_report(action['report_name'], datas)

    @staticmethod
    def exec_keyword(keyword, data=None, context=None):
        actions = []
        if 'id' in data:
            try:
                model_id = data.get('id', False)
#                actions = rpc.session.rpc_exec_auth('/object', 'execute',
#                        'ir.values', 'get', 'action', keyword,
#                        [(data['model'], model_id)], False, rpc.session.context)
#                actions = [x[2] for x in actions]
                actions = rpc.session.rpc_exec_auth('/object', 'execute',
                        'ir.action.keyword', 'get_keyword', keyword,
                        (data['model'], model_id))
            except rpc.RPCException, exp:
                from tryton.gui import Main
                error(_('Error: ')+str(exp.type), exp.message,
                        Main.get_main().window, exp.data)
                return False

        keyact = {}
        for action in actions:
            keyact[action['name']] = action

        from tryton.gui import Main
        res = selection(_('Select your action'), keyact, Main.get_main().window)
        if res:
            (name, action) = res
            Action._exec_action(action, data, context=context)
            return (name, action)
        elif not len(keyact):
            message(_('No action defined!'), Main.get_main().window)
        return False
