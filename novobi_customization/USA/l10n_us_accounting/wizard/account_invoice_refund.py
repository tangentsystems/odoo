# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..models.account_mixin import AccountMixinUSA
from ..models.model_const import ACCOUNT_ACCOUNT
from ..utils import action_utils


class AccountInvoiceRefundUSA(models.TransientModel, AccountMixinUSA):
    """Write Off Bad Debt"""

    _name = 'account.invoice.refund.usa'
    _inherit = 'account.invoice.refund'
    _description = 'Write Off An Account'

    def _default_write_off_amount(self):
        inv_obj = self.env['account.invoice']
        context = dict(self._context or {})
        for inv in inv_obj.browse(context.get('active_ids')):
            self._validate_state(inv.state)
            return inv.residual
        return 0.0

    def _default_bad_debt_account_id(self):
        return self.env.user.company_id.bad_debt_account_id.id \
            if self.env.user.company_id.bad_debt_account_id else False

    write_off_amount = fields.Monetary(string='Write Off Amount', default=_default_write_off_amount,
                                       currency_field='company_currency_id', required=True)

    company_currency_id = fields.Many2one('res.currency', readonly=True,
                                          default=lambda self: self.env.user.company_id.currency_id)

    account_id = fields.Many2one(ACCOUNT_ACCOUNT, string='Account', required=True, default=_default_bad_debt_account_id,
                                 domain=[('deprecated', '=', False)])

    company_id = fields.Many2one('res.company', string='Company', change_default=True, readonly=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))

    @api.multi
    @api.constrains('write_off_amount')
    def _check_write_off_amount(self):
        for record in self:
            if record.write_off_amount <= 0:
                raise ValidationError(_('Amount must be greater than 0.'))

    @api.multi
    def action_write_off(self):
        inv_obj = self.env['account.invoice']
        context = dict(self._context or {})
        is_apply = self.env.context.get('create_and_apply', False)

        refund_list = []
        for form in self:
            for inv in inv_obj.browse(context.get('active_ids')):
                self._validate_state(inv.state)

                description = form.description or inv.name
                refund = inv.create_refund(form.write_off_amount, form.company_currency_id, form.account_id,
                                           form.date_invoice, description, inv.journal_id.id)

                # Put the reason in the chatter
                subject = 'Write Off An Account'
                body = description
                refund.message_post(body=body, subject=subject)

                refund_list.append(refund)

                if is_apply:  # validate, reconcile and stay on invoice form.
                    to_reconcile_lines = inv.move_id.line_ids.filtered(lambda line:
                                                                       line.account_id.id == inv.account_id.id)
                    refund.action_invoice_open()  # validate write-off
                    to_reconcile_lines += refund.move_id.line_ids.filtered(lambda line:
                                                                           line.account_id.id == inv.account_id.id)
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    return True

        return self.redirect_to_edit_mode_form('l10n_us_accounting.write_off_form_usa', refund_list[0].id, self._module,
                                               'action_invoice_write_off_usa') if refund_list else True

    @staticmethod
    def _validate_state(state):
        if state in ['draft', 'cancel']:
            raise UserError('Cannot create write off an account for the draft/cancelled invoice.')


class AccountInvoiceRefundCreditNoteUSA(models.TransientModel, AccountMixinUSA):
    """Credit Notes"""

    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        invoice_refund = super(AccountInvoiceRefundCreditNoteUSA, self).compute_refund(mode)
        if not isinstance(invoice_refund, int):
            form_view = 'account.invoice_form'
            action_id = action_utils.find_action_id(invoice_refund)
            if action_id:
                form_view = action_id == 'action_invoice_out_refund' and 'l10n_us_accounting.credit_note_form_usa' or \
                            action_id == 'action_invoice_in_refund' and 'l10n_us_accounting.credit_note_supplier_form_usa'

            return self.redirect_to_edit_mode_form(form_view,
                                                   next((i[2][0] for i in invoice_refund.get('domain', []) if 'id' in i), invoice_refund.get('res_id')),
                                                   'account',
                                                   action_id)
        return invoice_refund

    @api.depends('date_invoice')
    @api.one
    def _get_refund_only(self):
        """Always hide 2 options 'cancel' and 'modify' since we already have Cancel and Set to Draft buttons"""
        self.refund_only = True
