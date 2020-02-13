odoo.define("account_dashboard.journal_data_item", function (require) {
    // var JournalDashboardGraph = require("web.JournalDashboardGraph");
    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var session = require('web.session');
    var qweb = core.qweb;

    var FORMAT_OPTIONS = {
        // allow to decide if utils.human_number should be used
        humanReadable: function (value) {
            return Math.abs(value) >= 1000;
        },
        // with the choices below, 1236 is represented by 1.24k
        minDigits: 1,
        decimals: 2,
        // avoid comma separators for thousands in numbers when human_number is used
        formatterCallback: function (str) {
            return str;
        },
    };

    var JournalData = AbstractField.extend({
        className: "o_journal",
        cssLibs: [
            '/web/static/lib/nvd3/nv.d3.css',
        ],
        jsLibs: [
            '/web/static/lib/nvd3/d3.v3.js',
            '/web/static/lib/nvd3/nv.d3.js',
            '/web/static/src/js/libs/nvd3.js',
            '/account_dashboard/static/src/js/libs/nvd3_chart_extend.js',
        ],
        events:{
            'change select': '_change_selection',
        },

        init: function () {
            this._super.apply(this, arguments);
            this.graph_type = this.attrs.graph_type;
            this.data = JSON.parse(this.value);
            session.currency_id = this.data.currency_id;
        },
        start: function () {
            this._onResize = this._onResize.bind(this);
            nv.utils.windowResize(this._onResize);
            return this._super.apply(this, arguments);
        },
        destroy: function () {
            if ('nv' in window) {
                // if the widget is destroyed before the lazy loaded libs (nv) are
                // actually loaded (i.e. after the widget has actually started),
                // nv is undefined, but the handler isn't bound yet anyway
                nv.utils.offWindowResize(this._onResize);
            }
            this._super.apply(this, arguments);
        },

        /**
         * The widget view uses the nv(d3) lib to render the graph. This lib
         * requires that the rendering is done directly into the DOM (so that it can
         * correctly compute positions). However, the views are always rendered in
         * fragments, and appended to the DOM once ready (to prevent them from
         * flickering). We here use the on_attach_callback hook, called when the
         * widget is attached to the DOM, to perform the rendering. This ensures
         * that the rendering is always done in the DOM.
         */
        on_attach_callback: function () {
            this._isInDOM = true;
            this._render();
        },
        /**
         * Called when the field is detached from the DOM.
         */
        on_detach_callback: function () {
            this._isInDOM = false;
        },

        //--------------------------------------------------------------------------
        // Event
        //--------------------------------------------------------------------------
        _change_selection: function () {
            this._render()
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private: render chart
         */
        _render_info: function (parent, info) {
            parent.empty();
            $(qweb.render('InfoView', {
                'info': info
            })).appendTo(parent);
        },

        _render_chart: function (parent, data, data_type, extra_graph_setting) {
            var format_number = ',.2f';
            var format_number_minimal = ',.2s';
            var self = this;

            // Find min max range of each dim to append to chart
            switch (data_type){
                case 'line':
                case 'bar':
                case 'horizontal_bar':
                    var minY = 2 >> 30,
                        maxY = 0,
                        minX = 2 >> 30,
                        maxX = 0;
                    var percentage_padding_chart = 0.05;

                    data.forEach(function (d) {
                        d.values.forEach(function (s) {
                            minY = Math.min(minY, s.y);
                            maxY = Math.max(maxY, s.y);
                            minX = Math.min(minX, s.x);
                            maxX = Math.max(maxX, s.x);
                        });
                    });
                    var deltaX = maxX - minX;
                    var deltaY = maxY - minY;
                    break
                case 'multi_chart':
                    var minY = [2 >> 30, 2 >> 30],
                        maxY = [0, 0],
                        minX = [2 >> 30, 2 >> 30],
                        maxX = [0, 0];
                    var percentage_padding_chart = 0.05;

                    data.forEach(function (d) {
                        d.values.forEach(function (s) {
                            var idx = d.yAxis - 1;
                            minY[idx] = Math.min(minY[idx], s.y);
                            maxY[idx] = Math.max(maxY[idx], s.y);
                            minX[idx] = Math.min(minX[idx], s.x);
                            maxX[idx] = Math.max(maxX[idx], s.x);
                        });
                    });
                    var deltaX = maxX.map(function(item, index) {
                        return item - minX[index];
                    });
                    var deltaY = maxY.map(function(item, index) {
                        return item - minY[index];
                    });
                    break
            }

            parent.empty();

            // Render chart base on the type of chart pass from parameter
            nv.addGraph(function() {
                var div_svg = $('<div class="table_svg" style="width:100%; height:100%"></div>');
                parent.append(div_svg);

                self.$svg = parent.find('.table_svg').append('<svg style="width:100%; height:100%">');

                var svg = d3.select(self.$('.table_svg svg')[0]);

                switch (data_type){
                    case 'line':
                        self.chart = nv.models.lineChart()
                        // .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                            .showLegend(true)       //Show the legend, allowing users to turn on/off line series.
                            .showYAxis(true)        //Show the y-axis
                            .showXAxis(true)        //Show the x-axis
                            .margin({ right: 40 })
                            .x(function(d) {return d.x; })
                            .y(function(d) {return d.y; })
                        ;
                        self.chart.legend.updateState(false);

                        self.chart.yAxis
                            .tickFormat(self.format_currency);
                        self.chart.tooltip.valueFormatter(d3.format(self.currency_symbol+format_number));

                        self.chart.xAxis.tickFormat(function (d) {
                            var name = '';
                            _.each(data, function (line){
                                _.each(line.values, function (v){
                                    if (typeof v.x == 'string') {
                                        name = v.x
                                    } else if (v.x === d && v.name){
                                        name = v.name;
                                    }
                                });
                            });
                            return name;
                        }).showMaxMin(false);
                        // self.chart.useInteractiveGuideline(true);

                        self.chart.forceY([minY-deltaY*percentage_padding_chart, maxY+deltaY*percentage_padding_chart]);
                        self.chart.padData(false);
                        var availableWidth = (self.chart.width() || parseInt(svg.style('width')) || 960) - self.chart.margin().left - self.chart.margin().right
                        self.chart.xRange([availableWidth * .05, availableWidth * .95]);
                        break;
                    case 'horizontal_bar':
                        self.chart = nv.models.multiBarHorizontalChart()
                            .showControls(false)
                            .showValues(extra_graph_setting.showValues === undefined? false: extra_graph_setting.showValues)
                            .stacked(extra_graph_setting.stacked === undefined? false: extra_graph_setting.stacked)
                            // .stacked(false)
                            .margin({
                                'left': extra_graph_setting.marginLeft === undefined? 0: extra_graph_setting.marginLeft,
                                'top': 0,
                                'bottom': 0
                            })
                            .x(function(d){return d.label;})
                            .y(function(d){return d.value;})
                            .showLegend(false)
                            .showXAxis(extra_graph_setting.showXAxis === undefined? false: extra_graph_setting.showXAxis)
                            .showYAxis(extra_graph_setting.showYAxis === undefined? false: extra_graph_setting.showYAxis)
                        ;

                        if (extra_graph_setting.height !== undefined){
                            self.chart.height(extra_graph_setting.height);
                            self.$el.find('.journal_info').css('cssText', 'height:' + extra_graph_setting.height + 'px !important;');
                            self.$el.find('.content_kanban_view')
                                .css('cssText', 'height:' + extra_graph_setting.height + 'px !important; ' +
                                    'position: inherit; min-height: ' + extra_graph_setting.height + 'px;');
                        }

                        self.chart.xAxis
                            .showMaxMin(false);

                        self.chart.yAxis
                            .tickFormat(self.format_currency);

                        self.chart.tooltip.valueFormatter(d3.format(self.currency_symbol+format_number));

                        self.chart.valueFormat(self.format_currency);

                        break;
                    case 'bar':
                        self.chart = nv.models.multiBarChart()
                            .reduceXTicks(true)   //If 'false', every single x-axis tick label will be rendered.
                            .rotateLabels(0)      //Angle to rotate x-axis labels.
                            .groupSpacing(0.1)    //Distance between each group of bars.
                            .showControls(false)
                            .stacked(extra_graph_setting.stacked === undefined? false: extra_graph_setting.stacked)
                            .margin({ right: 40 })
                        ;

                        self.chart.legend.dispatch.on('legendClick', function(d,i) {
                            var dt = d3.select(self.$('.table_svg svg')[0]).datum();   // <-- all data
                            console.log("legendClick", dt);

                        });
                        self.chart.legend.updateState(false);

                        self.chart.xAxis.tickFormat(function (d) {
                            var name = '';
                            _.each(data, function (line){
                                _.each(line.values, function (v){
                                    if (v.x === d){
                                        name = v.name?v.name:v.x;

                                    }
                                });
                            });
                            return name;
                        }).showMaxMin(false);

                        self.chart.yAxis
                            .tickFormat(self.format_currency);
                        self.chart.tooltip.valueFormatter(d3.format(self.currency_symbol+format_number));
                        self.chart.forceY([minY-deltaY*percentage_padding_chart, maxY+deltaY*percentage_padding_chart]);
                        break;
                    case 'multi_chart':
                        self.chart = nv.models.multiChart()
                            .margin({ right: 40 });
                        self.chart.legend.updateState(false);

                        self.chart.xAxis.tickFormat(function (d) {
                            var name = '';
                            _.each(data, function (line){
                                _.each(line.values, function (v){
                                    if (v.x === d && v.name){
                                        name = v.name;
                                    }
                                });
                            });
                            return name;
                        }).showMaxMin(false);

                        self.chart.yAxis1
                            .tickFormat(self.format_currency);
                        self.chart.yAxis2
                            .tickFormat(self.format_currency);
                        self.chart.bars1.stacked(true);
                        self.chart.lines1.padData(true);
                        self.chart.useInteractiveGuideline(true);
                        self.chart.interactiveLayer.tooltip.valueFormatter(d3.format(self.currency_symbol+format_number));
                        self.chart.yDomain1([minY[0] - deltaY[0] * percentage_padding_chart,
                            maxY[0] + deltaY[0] * percentage_padding_chart]);
                        self.chart.yDomain2([minY[1] - deltaY[1] *percentage_padding_chart,
                            maxY[1] + deltaY[1] * percentage_padding_chart]);
                        break;
                }

                svg.datum(self._customizeData(data, data_type));
                svg.transition()
                    .duration(600)
                    .call(self.chart);

                nv.utils.windowResize(self.chart.update);
                self.chart.update();
                d3.selectAll(".nv-series").style("cursor", "default").on("click", null);

                self._hide_grid(extra_graph_setting);
                self._customizeChart(data, data_type);
            });
        },

        _hide_grid: function (extra_graph_setting) {
            if (extra_graph_setting.hideGird === undefined? false: extra_graph_setting.hideGird){
                d3.selectAll('line').style('display', 'none')
            }
            d3.selectAll("g.nv-y g g path.domain").style('display', 'none');
            d3.selectAll("g.nv-y1 g g path.domain").style('display', 'none');
            d3.selectAll("g.nv-y2 g g path.domain").style('display', 'none');
        },

        /**
         * @private
         */
        _customizeData: function (data, data_type) {
            if (data_type === 'line' && data.length){
                first_item = data[0].values;
                if (first_item.length === 1) {
                    data[0].values.push(data[0].values[0])
                }
            }

            return data
        },

        _customizeChart: function (data, data_type) {
            if (data_type === 'horizontal_bar') {
                // Add classes related to time on each bar of the bar chart
                var colors = _.map(data[0].values, function (v) {return v.color; });

                _.each(this.$('.nv-bar'), function (v, k){
                    // classList doesn't work with phantomJS & addClass doesn't work with a SVG element
                    $(v).attr('style', $(v).attr('style') + '; fill:' + colors[k] + '; stroke:' + colors[k]);
                });
            }
        },

        /**
         * @private
         */
        _render: function () {
            // note: the rendering of this widget is aynchronous as nvd3 does a
            // setTimeout(0) before executing the callback given to addGraph
            this.$el.css('cssText', 'display:block !important;');
            if (this._isInDOM){
                var self = this;
                self.currency_symbol = '$';

                if (this.value) {
                    var data = JSON.parse(this.value);
                    self.selection = data.selection;
                    var dashboard = {'number_draft': '1',
                        'sum_draft': '$1.00',
                        'number_waiting': '1',
                        'sum_waiting': '$1.23'};
                    if (self.$el.find('.journal_info').length === 0) {
                        $(qweb.render('JournalDataItemView', {
                            'dashboard': dashboard,
                            'type': data.name,
                            'data': data
                        })).appendTo($(self.$el).empty());
                    }

                    var range = self._get_range_period();
                    var defaul_param = [range.start_date, range.end_date, range.date_separate];
                    if (data.function_retrieve === '') {
                        this._render_chart(this.$el.find('.content_kanban_view'), data.data_render, data.data_type, data.extra_graph_setting);
                    } else {
                        this._rpc({
                            method: data.function_retrieve,
                            model: this.model,
                            args: defaul_param.concat(data.extra_param)
                        }).then(function (result) {
                            var extra_graph_setting = result.extra_graph_setting === undefined? {}: result.extra_graph_setting

                            if (extra_graph_setting && extra_graph_setting.normal_value) {
                                session.currency_id = null;
                            }

                            self._render_chart(self.$el.find('.content_kanban_view'), result.graph_data, data.data_type, extra_graph_setting);
                            self._render_info(self.$el.find('.info-view'), result.info_data);
                        });
                    }
                }
                this._onResize();
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _onResize: function () {
            if (this.chart) {
                this.chart.update();
            }
        },

        //--------------------------------------------------------------------------
        // General
        //--------------------------------------------------------------------------
        /**
         * Get information about the range time and type of period chosen in the
         * selection field.
         *
         * @private
         */
        _get_range_period: function () {
            var selection = this.$el.find('select#Period')[0];
            return_value = {}
            if (selection !== undefined) {
                var selected_value = this.$el.find('select#Period')[0].value;
                var start_date = '';
                var end_date = '';
                var date_separate = '';
                for (i in this.selection){
                    item = this.selection[i];
                    if (item.n === selected_value) {
                        return_value.start_date = item.s;
                        return_value.end_date = item.e;
                        return_value.date_separate = item.k;
                    }
                }
            }
            return return_value
        },

        format_currency: function(amount){
            var currency = session.get_currency(session.currency_id);
            var formatted_value = field_utils.format.float(amount || 0, {digits: currency && currency.digits}, FORMAT_OPTIONS);
            if (currency) {
                if (currency.position === "after") {
                    formatted_value += currency.symbol;
                } else {
                    formatted_value = currency.symbol + formatted_value;
                }
            }
            return formatted_value;
        },
    });

    var registry = require('web.field_registry');

    registry.add("journal_data", JournalData);
});
