odoo.define("tangent_account_dashboard.journal_data_item", function (require) {
    var fieldRegistry = require('web.field_registry');

    var JournalData = fieldRegistry.get('journal_data');
    var session = require('web.session');

    JournalData.include({
        init: function() {
            this._super.apply(this, arguments);
            this.jsLibs.push('/tangent_account_dashboard/static/src/js/libs/nvd3_stack_group_chart.js');
        },
        _render_chart: function (parent, data, data_type, extra_graph_setting) {
            if (extra_graph_setting && extra_graph_setting.normal_value) {
                this.currency_symbol = '';
            }

            if (extra_graph_setting && extra_graph_setting.stack_group_bar) {
                var self = this;

                parent.empty();

                // Prepare data for stack group chart
                var graph_data = [];
                _.each(data, function (item) {
                    graph_data.push(self._prepare_stack_group_data(item));
                });

                // Render chart
                nv.addGraph(function () {
                    var div_svg = $('<div class="table_svg" style="width:100%; height:100%"></div>');
                    parent.append(div_svg);

                    self.$svg = parent.find('.table_svg').append('<svg style="width:100%; height:100%">');

                    var svg = d3.select(self.$('.table_svg svg')[0]);

                    self.chart = nv.models.GroupedStackedBarChart().percentageMode(false);
                    self.chart.tooltip.valueFormatter(d3.format(self.format_currency_for_tooltip()));
                    self.chart.valueFormat(self.format_currency);

                    svg.datum(self._customizeData(graph_data, data_type));
                    svg.transition()
                        .duration(600)
                        .call(self.chart);

                    nv.utils.windowResize(self.chart.update);
                    self.chart.update();
                    d3.selectAll(".nv-series").style("cursor", "default").on("click", null);
                });

            } else {
                return this._super.apply(this, arguments);
            }
        },
        _prepare_stack_group_data(data) {
            var result = {
                key: data.key,
                color: data.color,
                label: data.key,
                groups: []
            };
            var is_income = data.key === 'Income';

            _.each(data.values, function (item) {
                result.groups.push({
                    group_label: item.name,
                    group_key: item.name,
                    stacks: [{
                            stack_key: 'income',
                            stack_label: 'income',
                            stack_value: is_income ? item.y : 0
                        }, {
                            stack_key: 'expense',
                            stack_label: 'expense',
                            stack_value: is_income ? 0 : item.y
                        }]
                });
            });

            return result
        },
        format_currency_for_tooltip: function() {
            var currency = session.get_currency(this.data.currency_id);
            var formatted_value = ',.2f';
            if (currency) {
                if (currency.position === "after") {
                    formatted_value += currency.symbol;
                } else {
                    formatted_value = currency.symbol + formatted_value;
                }
            }
            return formatted_value;
        }
    });
});
