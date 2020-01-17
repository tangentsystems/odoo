# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


from odoo.http import request, route
from odoo.addons.bus.controllers.main import BusController


class ChatBotController(BusController):
    # --------------------------
    # Anonymous routes (Common Methods)
    # --------------------------
    @route('/chatbot/chat_post', type="json", auth="user")
    def chatbot_post(self, channel_id):
        history = request.env['dialog.history'].search([('channel_id', '=', channel_id)], order="create_date desc, id desc", limit=1)
        if not history:
            return True
        history.detect_intent(text=history.request)
        body = history.response
        channel = request.env['mail.channel'].browse(channel_id)
        odoobot_id = request.env['ir.model.data'].sudo().xmlid_to_res_id("base.partner_root")
        if channel and body:
            subtype_id = request.env['ir.model.data'].sudo().xmlid_to_res_id('mail.mt_comment')
            channel.with_context({
                'mail_create_nosubscribe': True,
                'no_update_pin': True
            }).sudo().message_post(
                body=body, author_id=odoobot_id,
                message_type='comment', subtype_id=subtype_id
            )
        return True
