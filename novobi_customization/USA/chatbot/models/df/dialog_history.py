# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)

RECOMMENED_ACTIONS = ['Invoices', 'Customers', 'Products', 'Chart of Accounts']


class DialogHistory(models.Model):
    _name = 'dialog.history'
    _rec_name = 'request'
    _inherit = 'dialog.base'
    _description = 'Store user story conversation with OdooBot'

    user_id = fields.Many2one(
        'res.users',
        'User',
        default=lambda self: self.env.user
    )
    request = fields.Char('Request')
    request_raw = fields.Text('Request raw')
    response = fields.Char('Response')
    response_raw = fields.Text('Response Raw')
    channel_id = fields.Char('Channel ID')
    parameters = fields.Text('Parameters')

    def _set_domain(self, domain, res_model, res_filter):
        """Add domain via back-end side

        Param:
            - domain (list): current domain from action
            - res_model (str): model from action
            - res_filter (str): text from user's message

        Return:
            - domain (list): additional domain
        """
        try:
            domain = safe_eval(domain)
        except Exception:
            domain = []

        by_model = self.env['ir.model'].search([('model', '=', res_model)])
        if by_model:
            # Generally, get field `search_by_field_ids` in dynamic cases
            by_fields = by_model.mapped('field_id').filtered(
                lambda f: f.name in ['name', 'number']
            )
            operators, new_domain = [], []
            for field in by_fields:
                if len(operators) < len(by_fields) - 1:
                    operators += ["|"]
                new_domain += [(field.name, 'ilike', res_filter)]
            domain = domain + operators + new_domain
        return domain

    def _set_context(self, context, res_model, res_filter):
        """Add context via back-end side

        Param:
            - context (dict): current context from action
            - res_model (str): model from action
            - res_filter (str): text from user's message

        Return:
            - context (dict): additional context
        """
        if not context:
            return {}
        try:
            context = safe_eval(context)
        except Exception:
            context = {}
        return context

    def _set_options(self, period, date_from=None, date_to=None):
        """Normally, this function add options for account_report (enterprise edition)
        Param:
            period (str): this_month/this_year/...
            date_from (str)
            date_to (str)
        Return:
            options (dict)
        """
        today = date.today().strftime(DATE_FORMAT)
        if period:
            return {
                'date': {
                    'date': today,
                    'filter': period
                }
            }
        return {}

    @api.model
    def get_action(self, action_type, action_id_str, res_filter, period):
        """Get action from specific type, id and even more filter

        Param:
            action_type (str): type of action
            action_id_str (str): ID of action
            res_filter (str): text from user's message
        Return:
            action (dict)
        """
        # Convert string to integer
        action_id = int(action_id_str)
        action = self.env[action_type].browse(action_id)
        if action_type == 'ir.actions.server':
            action_dict = action.run()
        else:
            # Action window
            action_dict = action.read()[0]

        # Set domain, context based on res_filter
        res_model = action_dict.get('res_model', False)
        domain = action_dict.get('domain', [])
        new_domain = self._set_domain(domain, res_model, res_filter)

        context = action_dict.get('context', {})
        new_context = \
            self._set_context(context, res_model, res_filter)

        # `tree` can not use in do_action()
        # replace `tree` by `list`
        views = action_dict.get('views', False)
        new_views = [[False, 'list'], [False, 'form']]
        if views:
            str_views = str(views)
            new_views = safe_eval(str_views.replace('tree', 'list'))

        # Handle options for action
        options = self._set_options(period)

        # Update new domain, context, views
        action_dict.update({
            'domain': new_domain,
            'context': new_context,
            'views': new_views,
            'options': options,
        })
        return action_dict

    @api.model
    def get_bot_answer(self, action_type_id):
        """This function is called by Client (JS).

        Param:
            action_type_id (string): <action_type,action_id,filter,period>
        Return:
            action (dict)
        """
        if not action_type_id:
            return False
        [action_type, action_id_str, res_filter, period] = action_type_id.split(',')
        action = self.get_action(action_type, action_id_str, res_filter, period)
        return action

    def _prepare_li(self, action_type_id, action_name):
        """
        List actions preparation
        Param:
            action_type_id (string): <action_type,action_id,filter>
            action_name (string): Name of action
        Return
            List actions
        """
        url = "<a href='#' target='_blank' class='cb_open_action' data-id='{action_type_id}'>{action_name}</a>" \
            .format(action_type_id=action_type_id,
                    action_name=action_name)
        # badge = '<span class="badge badge-primary badge-pill">%d</span>' % 10
        return """<li class="list-group-item d-flex justify-content-between align-items-center">
                    %s
                </li>""" % url

    def _menu_exists(self, menu_name):
        count = self.env['ir.ui.menu'].search_count([
            ('name', 'ilike', menu_name)
        ])
        if not count:
            return False
        return True

    def _generate_recommened_actions(self):
        menu = self.env['ir.ui.menu'].search([
            ('name', 'in', RECOMMENED_ACTIONS)
        ], limit=5)

        actions = menu.filtered(lambda m: m.action).mapped('action')
        final_li = ""
        for action in actions:
            if not action:
                continue
            action_type_id = ','.join([action.type, str(action.id), '', ''])
            li = self._prepare_li(action_type_id, action.name)
            final_li += li

        template = """
        <br><br>Look at these examples below or type <b>/help</b> for more detail.
            <ul class="list-group">
                %s
            </ul>
        """
        list_actions = template % final_li
        return list_actions

    def _generate_actions(self, menu_name, res_filter='', period=''):
        """
        Param:
            menu_name (string)
            res_filter (string): name/id of the resource
        Return:
            actions (html): List actions url
        """
        menus = self.env['ir.ui.menu'].search([
            ('name', 'ilike', menu_name)
        ], limit=3)

        # Can not use `mapped` cause we have 4 types of action
        actions = []
        for menu in menus.filtered(lambda m: m.action):
            actions.append(menu.action)

        if not actions:
            return False
        final_li = ""
        for action in actions:
            if not action:
                continue
            action_type_id = ','.join([action.type, str(action.id), res_filter, period])
            li = self._prepare_li(action_type_id, action.name)
            final_li += li

        template = """
            <ul class="list-group">
                %s
            </ul>
        """
        list_actions = template % final_li
        return list_actions

    def _handle_yes_no(self):
        return """
<ul class="list-group">
    <li class="list-group-item d-flex justify-content-between align-items-center">
        <a href="#" target="_blank" class="cb_yes_no">Sure</a>
    </li>
    <li class="list-group-item d-flex justify-content-between align-items-center">
        <a href="#" target="_blank" class="cb_yes_no">No, thanks</a>
    </li>
</ul>
        """

    @api.multi
    def _handle_yes(self):
        self.ensure_one()
        return ''

    @api.multi
    def _handle_no(self, parameters):
        self.ensure_one()
        menu = parameters.get('menu', False)
        self.delete_all_contexts()
        return self._generate_actions(menu_name=menu, res_filter='')

    @api.multi
    def _handle_any(self, parameters):
        self.ensure_one()
        menu = parameters.get('menu', False)
        res_filter = parameters.get('any', False)
        self.delete_all_contexts()
        return self._generate_actions(menu_name=menu, res_filter=res_filter)

    @api.multi
    def _handle_report(self, parameters):
        self.ensure_one()
        report = parameters.get('report', False)
        period = parameters.get('period', False)
        if not period:
            return ''
        self.delete_all_contexts()
        return self._generate_actions(menu_name=report, period=period)

    @api.multi
    def _handle_fallback(self):
        self.ensure_one()
        self.delete_all_contexts()
        return self._generate_recommened_actions()

    @api.multi
    def handle_parameters(self, parameters, isFallback):
        """ This function handle parameters from intent (dict)
        Param:
            parameters (dict)
            isFallback (boolean)
        Return:
            answer (str)
        """
        self.ensure_one()
        report = parameters.get('report', '')
        menu = parameters.get('menu', '')
        open_action = parameters.get('open', '')

        yes = parameters.get('yes', False)
        no = parameters.get('no', False)
        yes_no = parameters.get('yes_no', False)
        any_param = parameters.get('any', False)

        answer = ''
        if open_action:
            if menu:
                if yes_no:
                    answer = self._handle_yes_no()
                if no:
                    answer = self._handle_no(parameters)
                if yes:
                    answer = self._handle_yes()
                    if any_param:
                        answer = self._handle_any(parameters)
            if report:
                answer = self._handle_report(parameters)
        if isFallback:
            answer = self._handle_fallback()
            self.delete_all_contexts()

        return answer

    @api.multi
    def merge_parameters(self, origin_parameters, outputContexts, alternativeQueryResults):
        merged_parameters = origin_parameters

        # Get context from alternative results
        for alternativeQueryResult in alternativeQueryResults:
            context = alternativeQueryResult.get('outputContexts', [])
            if context:
                outputContexts += context
        # combine all parameters
        for outputContext in outputContexts:
            parameters = outputContext.get('parameters', {})
            if parameters:
                merged_parameters.update(parameters)

        return merged_parameters

    @api.multi
    def generate_expected_answer(self, request_raw):
        """
        Receive the request from dialogflow, extract datas and generate answer
        Param:
            request_raw (dict)
        Return:
            expected_answer (html)
            merged_parameters (dict)
        """
        self.ensure_one()

        query_result = request_raw.get('queryResult', {})
        intent = query_result.get('intent', {})

        fulfillmentText = query_result.get('fulfillmentText', '')
        origin_parameters = query_result.get('parameters', {})
        isFallback = intent.get('isFallback', False)

        # Check menu/report name if it exists
        menu = origin_parameters.get('menu', False)
        if menu:
            if not self._menu_exists(menu):
                actions = self._generate_recommened_actions()
                answer = \
                    "The menu <b>%s</b> doesn't exist, please try again or look at recommended menus" % menu
                expected_answer = answer + actions
                return expected_answer, origin_parameters

        merged_parameters = self.merge_parameters(
            origin_parameters,
            query_result.get('outputContexts', []),
            request_raw.get('alternativeQueryResults', [])
        )
        answer = self.handle_parameters(merged_parameters, isFallback)
        expected_answer = fulfillmentText + answer

        return expected_answer, merged_parameters

    @api.multi
    def _parse_response(self, response):
        """ Parse response from DialogFlow to expected answer

        Param:
            response (pb2 object)
        Return:
            expected_answer (string)
            request_raw (dictionary)
        :return expected_answer, result:
        """
        self.ensure_one()
        request_raw = self._convert_message_to_dict(response)
        expected_answer, response_raw = self.generate_expected_answer(request_raw)

        return expected_answer, request_raw, response_raw

    @api.multi
    def detect_intent(self, text):
        """ Detect text from DialogFlow and parse it to expected answer

        :param text:
        :return expected_answer, response_raw:
        """
        self.ensure_one()
        response = self.detect_intent_text(text)
        expected_answer, request_raw, response_raw = \
            self._parse_response(response)

        self.update({
            'request_raw': request_raw,
            'response_raw': response_raw,
            'response': expected_answer,
        })
        return True

    @api.model
    def get_answer(self, channel_id):
        """ Get answer and sent it to current channel
        """
        history = self.search([('channel_id', '=', channel_id)], order="create_date desc, id desc", limit=1)
        if not history:
            return True
        history.detect_intent(text=history.request)
        body = history.response
        channel = self.env['mail.channel'].browse(channel_id)
        odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
        if channel and body:
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')
            channel.with_context({
                'mail_create_nosubscribe': True,
                'no_update_pin': True,
            }).sudo().message_post(
                body=body, author_id=odoobot_id,
                message_type='comment', subtype_id=subtype_id
            )
