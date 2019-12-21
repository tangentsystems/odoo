odoo.define('chatbot.account_report', function (require) {
'use strict';
	var account_report = require('account_reports.account_report');

	account_report.include({

		init: function (parent, action) {
	        this._super.apply(this, arguments);
            try{
            	// Handle additional option from back-end side
            	if (action.options.date){
                	this.report_options.date = action.options.date;
            	}
            }
            catch (err){
            	// No need to check it, just an option
            }
	        
	    },
	});

});