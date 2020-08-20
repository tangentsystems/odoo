# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import fields, models, api
from dateutil.relativedelta import relativedelta


class PurchaseOrder(models.TransientModel):
    _inherit = 'cash.flow.projection'
    
    def _query_remaining_amount_of_so(self, from_date, to_date, so_lead_time):
        real_from_date = from_date - relativedelta(days=so_lead_time)
        real_to_date = to_date - relativedelta(days=so_lead_time)
        query = """
            SELECT so.id, (so.amount_total - SUM(COALESCE(amount_invoiced, 0))) as amount_so_remaining, so.amount_total, so.confirmation_date, so.partner_id, so.name
            FROM (
                SELECT so.id, SUM(COALESCE(ainv.amount_total, 0)) as amount_invoiced, so.amount_total, so.confirmation_date, so.partner_id, so.name
                FROM (
                        SELECT so.id, so.amount_total, so.confirmation_date, so.partner_id, so.name
                        FROM sale_order so
                        WHERE so.state = 'sale'
                                AND so.confirmation_date IS NOT NULL
                                AND CAST(so.confirmation_date as date) >= '{from_date}'
                                AND CAST(so.confirmation_date as date) <= '{to_date}'
                                AND so.company_id = {company_id}
                    ) as so
                    LEFT JOIN sale_order_line sol ON so.id = sol.order_id
                    LEFT JOIN sale_order_line_invoice_rel sinv ON sol.id = sinv.order_line_id
                    LEFT JOIN account_invoice_line ainvl ON sinv.invoice_line_id = ainvl.id
                    LEFT JOIN (
                                SELECT id, amount_total
                                FROM account_invoice
                                WHERE state NOT IN ('draft', 'cancel')
                                    AND type = 'out_invoice'
                                    AND company_id = {company_id}
                                ) ainv ON ainvl.invoice_id = ainv.id
                GROUP BY so.id, so.amount_total, so.partner_id, so.confirmation_date, so.name
                UNION ALL
                SELECT so.id, -SUM(COALESCE(aml.amount_residual, 0)) as amount_invoiced, so.amount_total, so.confirmation_date, so.partner_id, so.name
                FROM (
                        SELECT so.id, so.amount_total, so.confirmation_date, so.partner_id, so.name
                        FROM sale_order so
                        WHERE so.state = 'sale'
                                AND so.confirmation_date IS NOT NULL
                                AND CAST(so.confirmation_date as date) >= '{from_date}'
                                AND CAST(so.confirmation_date as date) <= '{to_date}'
                                AND so.company_id = {company_id}
                    ) as so
                    LEFT JOIN (
                                SELECT id, sale_deposit_id
                                FROM account_payment
                                WHERE state NOT IN ('draft', 'cancel')
                                ) ap ON so.id = ap.sale_deposit_id
                    LEFT JOIN (
                                SELECT payment_id, amount_residual
                                FROM account_move_line
                                WHERE credit > 0
                                        AND company_id = {company_id}
                                ) aml ON ap.id = aml.payment_id
                GROUP BY so.id, so.amount_total, so.partner_id, so.confirmation_date, so.name
            ) as so
            GROUP BY so.id, so.amount_total, so.partner_id, so.confirmation_date, so.name
        """.format(from_date=real_from_date, to_date=real_to_date, company_id=self.env.user.company_id.id)
        return query
    
    def _query_remaining_amount_of_po(self, from_date, to_date, po_lead_time):
        real_from_date = from_date - relativedelta(days=po_lead_time)
        real_to_date = to_date - relativedelta(days=po_lead_time)
        query = """
            SELECT po.id, (po.amount_total - SUM(COALESCE(amount_invoiced, 0))) as amount_so_remaining, po.amount_total, po.date_approve, po.partner_id, po.name
            FROM (
                SELECT po.id, SUM(COALESCE(ainv.amount_total, 0)) as amount_invoiced, po.amount_total, po.date_approve, po.partner_id, po.name
                FROM (
                        SELECT po.id, po.amount_total, po.date_approve, po.partner_id, po.name
                        FROM purchase_order po
                        WHERE po.state = 'purchase'
                                AND po.date_approve IS NOT NULL
                                AND CAST(po.date_approve as date) >= '{from_date}'
                                AND CAST(po.date_approve as date) <= '{to_date}'
                                AND po.company_id = {company_id}
                    ) as po
                    LEFT JOIN account_invoice_purchase_order_rel pinv ON po.id = pinv.purchase_order_id
                    LEFT JOIN (
                                SELECT id, amount_total
                                FROM account_invoice
                                WHERE state NOT IN ('draft', 'cancel')
                                        AND type = 'in_invoice'
                                        AND company_id = {company_id}
                                ) ainv ON pinv.account_invoice_id = ainv.id
                GROUP BY po.id, po.amount_total, po.partner_id, po.date_approve, po.name
                UNION ALL
                SELECT po.id, SUM(COALESCE(aml.amount_residual, 0)) as amount_invoiced, po.amount_total, po.date_approve, po.partner_id, po.name
                FROM (
                        SELECT po.id, po.amount_total, po.date_approve, po.partner_id, po.name
                        FROM purchase_order po
                        WHERE po.state = 'purchase'
                                AND po.date_approve IS NOT NULL
                                AND CAST(po.date_approve as date) >= '{from_date}'
                                AND CAST(po.date_approve as date) <= '{to_date}'
                                AND po.company_id = {company_id}
                    ) as po
                    LEFT JOIN (
                                SELECT id, purchase_deposit_id
                                FROM account_payment
                                WHERE state NOT IN ('draft', 'cancel')
                                ) ap ON po.id = ap.purchase_deposit_id
                    LEFT JOIN (
                                SELECT payment_id, amount_residual
                                FROM account_move_line
                                WHERE debit > 0
                                        AND company_id = {company_id}
                                ) aml ON ap.id = aml.payment_id
                GROUP BY po.id, po.amount_total, po.partner_id, po.date_approve, po.name
            ) as po
            GROUP BY po.id, po.amount_total, po.partner_id, po.date_approve, po.name
        """.format(from_date=real_from_date, to_date=real_to_date, company_id=self.env.user.company_id.id)
        return query
