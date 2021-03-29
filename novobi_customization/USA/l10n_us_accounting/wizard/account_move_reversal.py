from odoo import models, fields, api
from odoo.tools.translate import _


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    @api.multi
    def reverse_moves(self):
        AccountMove = self.env['account.move']

        if self._context.get('active_model', False) == 'account.payment':
            payment_id = self._context.get('active_id', False)

            if payment_id:
                payment = self.env['account.payment'].browse(payment_id)
                ac_move_ids = payment.move_line_ids.mapped('move_id')
                res = ac_move_ids.reverse_moves(self.date, self.journal_id or False)

                if res:
                    payment.has_been_voided = True
                    moves = AccountMove.browse(res)
                    msg = "This payment has been voided. The reverse entries were created: {}".format(', '.join([record.name for record in moves]))
                    payment.message_post(body=msg, message_type="comment", subtype="mail.mt_note")

                    return {
                        'name': _('Reverse Moves'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'account.move',
                        'domain': [('id', 'in', res)],
                    }
            return {'type': 'ir.actions.act_window_close'}
        else:
            return super().reverse_moves()
