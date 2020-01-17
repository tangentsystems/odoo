# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountMoveDeposit(models.Model):
    _inherit = 'account.move'

    is_deposit = fields.Boolean('Is a Deposit?')


class AccountMoveLineDeposit(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    def remove_move_reconcile(self):
        rec_move_ids = self.env['account.partial.reconcile']

        for record in self:
            if record.move_id.is_deposit:
                for aml in record.move_id.line_ids:
                    for invoice in aml.payment_id.invoice_ids:
                        if invoice.id == self.env.context.get(
                                'invoice_id') and aml in invoice.payment_move_line_ids:
                            aml.payment_id.write({'invoice_ids': [(3, invoice.id, None)]})
                    rec_move_ids += aml.matched_debit_ids
                    rec_move_ids += aml.matched_credit_ids
                rec_move_ids.unlink()

                record.move_id.button_cancel()
                record.move_id.unlink()
            else:
                super(AccountMoveLineDeposit, self).remove_move_reconcile()
