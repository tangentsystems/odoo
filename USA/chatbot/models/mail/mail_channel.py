# -*- coding: utf-8 -*-

from odoo import api, models, _


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.model
    def init_odoobot(self):
        if self.env.user.odoobot_state == 'not_initialized':
            partner = self.env.user.partner_id
            odoobot_id = self.env['ir.model.data'].xmlid_to_res_id(
                "base.partner_root")
            channel = \
                self.with_context({"mail_create_nosubscribe": True}).create({
                    'channel_partner_ids': [(4, partner.id), (4, odoobot_id)],
                    'public': 'private',
                    'channel_type': 'chat',
                    'email_send': False,
                    'name': 'OdooBot'
                })
            message = _(
                "Hello,<br/>Odoo's chat helps employees collaborate efficiently. I'm here to help you discover its features.<br/>")
            channel.sudo().message_post(body=message,
                                        author_id=odoobot_id,
                                        message_type="comment",
                                        subtype="mail.mt_comment")
            # Force change
            self.env.user.odoobot_state = "smart_bot"
            return channel

    def _bot_command(self):
        # Show the command for OdooBot
        msg = _("""
            <br><br>
            Type "open <b>menu_name</b>" to open that menu.<br>
            e.g. open invoice <br>
            Type "open <b>report_name</b> <b>period</b>" to open that report with period.<br>
            e.g. open profit and loss this month<br>""")
        return msg

    def _execute_command_help(self, **kwargs):
        '''
        Override function for extending chatbot features
        '''
        is_bot = False
        partner = self.env.user.partner_id
        if self.channel_type == 'channel':
            msg = _("You are in channel <b>#%s</b>.") % self.name
            if self.public == 'private':
                msg += _(" This channel is private. People must be invited to join it.")
        else:
            all_channel_partners = self.env['mail.channel.partner'].with_context(active_test=False)
            channel_partners = all_channel_partners.search([('partner_id', '!=', partner.id), ('channel_id', '=', self.id)])
            partner_name = channel_partners[0].partner_id.name if channel_partners else _('Anonymous')
            msg = _("You are in a private conversation with <b>@%s</b>.") % (partner_name)
            if partner_name == 'OdooBot':
                msg += self._bot_command()
                is_bot = True
        if not is_bot:
            msg += _("""<br><br>
                Type <b>@username</b> to mention someone, and grab his attention.<br>
                Type <b>#channel</b>.to mention a channel.<br>
                Type <b>/command</b> to execute a command.<br>
                Type <b>:shortcut</b> to insert canned responses in your message.<br>""")

        self._send_transient_message(partner, msg)
