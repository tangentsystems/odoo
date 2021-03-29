odoo.define('web.usa.ribbon', function (require) {
    'use strict';

    var widgetRegistry = require('web.widget_registry');
    var Widget = require('web.Widget');

    var RibbonWidget = Widget.extend({
        template: 'web.usa.ribbon',
        xmlDependencies: ['/odoo_12_ribbon/static/src/xml/ribbon.xml'],

        init: function (parent, data, options) {
            this._super.apply(this, arguments);
            this.text = options.attrs.title || options.attrs.text;
            this.bgColor = options.attrs.bg_color;
        }

    });

    widgetRegistry.add('web_usa_ribbon', RibbonWidget);

    return RibbonWidget;
});