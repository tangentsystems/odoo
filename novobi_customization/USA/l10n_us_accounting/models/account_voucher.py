# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountVoucherUSA(models.Model):
    _name = 'account.voucher'
    _inherit = ['account.voucher', 'account.caching.mixin.usa']

    pay_now = fields.Selection(default='pay_now')
    payment_id = fields.Many2one('account.payment', 'Linked Payment')

    @api.multi
    def proforma_voucher(self):
        super(AccountVoucherUSA, self).proforma_voucher()

        journal_name = self.payment_journal_id.name
        self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
        self.trigger_apply_matching(self.build_journal_item_key(journal_name))

    @api.multi
    def voucher_pay_now_payment_create(self):
        res = super(AccountVoucherUSA, self).voucher_pay_now_payment_create()
        res['voucher_id'] = self.id
        return res

    @api.multi
    def cancel_voucher(self):
        # Override function
        for voucher in self:
            voucher.move_id.line_ids.remove_move_reconcile()
            voucher.move_id.button_cancel()
            voucher.move_id.unlink()
            voucher.payment_id.cancel()
            voucher.payment_id.unlink()
        self.write({'state': 'cancel', 'move_id': False, 'payment_id': False})
