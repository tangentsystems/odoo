from odoo import models, api, _, fields
import logging


class USAReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"

    # Change title of Partner Ledger report
    @api.model
    def get_report_name(self):
        context = self.env.context
        if context.get('active_model', False) == 'res.partner' and context.get('active_id', False):
            partner = self.env['res.partner'].browse(context['active_id'])
            return partner.partner_ledger_label
        return _('Partner Ledger')

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        # TODO: check and remove
        if options.get('partner_id', False):
            partner = self.env['res.partner'].browse(options['partner_id'])
            label = partner.partner_ledger_label
            return label.lower().replace(' ', '_')
        return self.get_report_name().lower().replace(' ', '_')
