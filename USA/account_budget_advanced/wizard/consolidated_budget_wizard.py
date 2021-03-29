# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


from odoo import models, api, _, fields
from odoo.exceptions import UserError


class ConsolidatedBudgetWizard(models.TransientModel):
    _name = 'consolidated.budget.wizard'

    def _default_budget_ids(self):
        active_ids = self.env.context.get('active_ids', False)
        return [(6, 0, active_ids)] if active_ids else []

    budget_ids = fields.Many2many('crossovered.budget', string='Budgets', default=_default_budget_ids)

    def action_view_report(self):
        if len(self.budget_ids) <=1:
            raise UserError('Please choose more budgets to view consolidated report.')

        budget = self.budget_ids[0]
        if any(bud.budget_type != budget.budget_type or bud.date_from != budget.date_from
               or bud.date_to != budget.date_to for bud in self.budget_ids):
            raise UserError('All budgets must have the same Budget Type and Date Period.')

        name = 'Combine Budget Reports'
        action_obj = self.sudo().env.ref('account_budget_advanced.action_usa_budget_report')
        action_obj['params'] = {'crossovered_budget_id': budget.id,
                                'budget_ids': self.budget_ids.ids}  # for refreshing the page
        action = action_obj.read()[0]

        action.update({
            'name': name,
            'display_name': name,
            'context': {'model': 'usa.budget.report',
                        'crossovered_budget_id': budget.id,
                        'budget_ids': self.budget_ids.ids}
        })
        return action
