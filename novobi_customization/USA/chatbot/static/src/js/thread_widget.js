odoo.define('chatbot.ThreadWindow', function (require) {
    "use strict";

    var ThreadWidget = require('mail.widget.Thread');

    ThreadWidget.include({
        events: _.extend({}, ThreadWidget.prototype.events, {
            'click .cb_open_action': 'onClickOpen',
            'click .cb_yes_no': 'onClickYesNo',
        }),

        onClickOpen: function (ev) {
            ev.preventDefault();
            var self = this;
            var action_type_id = '';
            try {
                action_type_id = ev.target.attributes['data-id'].value;
            } catch (err) {
                console.log(err);
            }

            return this._rpc({
                model: 'dialog.history',
                method: 'get_bot_answer',
                args: [action_type_id],
            }).then(function (action) {
                self.do_action(action);
            });

        },
        onClickYesNo: function (ev) {
            ev.preventDefault();
            var $input = $("textarea.o_composer_text_field");
            $input.val(ev.target.text);
            $input.trigger($.Event('keydown', {key: 'Enter', which: 13, keyCode: 13}));
            $input.val();
        },

    });

})