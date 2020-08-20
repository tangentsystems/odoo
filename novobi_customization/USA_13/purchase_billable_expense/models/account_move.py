from odoo import models, fields


class AccountMoveUSA(models.Model):
    _inherit = 'account.move'

    def open_expense_popup(self):
        # Override
        self.ensure_one()
        bill_line_ids = self.billable_expenses_ids.mapped('bill_line_id')
        expense_env = self.env['billable.expenses'].sudo()

        for line in self.invoice_line_ids - bill_line_ids:
            if line.purchase_line_id and line.purchase_line_id.billable_expenses_ids:
                line.purchase_line_id.billable_expenses_ids.write({
                    'bill_id': self.id,
                    'bill_line_id': line.id
                })
            else:
                expense_env.create({
                    'bill_id': self.id,
                    'bill_line_id': line.id,
                    'description': line.name,
                    'amount': line.price_subtotal,
                    'bill_date': self.invoice_date
                })

        return self._get_expense_popup()
