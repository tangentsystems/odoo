odoo.define("tangent_account_dashboard.journal_data_item", function (require) {
    'use strict';

    let AccountDashboard = require('account_dashboard.account_dashboard');

    AccountDashboard.include({
        init: function() {
            this._super.apply(this, arguments);
            this.jsLibs.push('/tangent_account_dashboard/static/src/js/libs/stack_group_chart.js');
        },
        _renderChart: function () {
            if (this.graph.setting.stack_group_bar) {
                let self = this;
                let data = this._prepare_stack_group_chart_data();
                let graph_view = this.$el.find('.content_kanban_view');
                graph_view.empty();
                graph_view.css('cssText', 'position: initial !important;');
                let canvas = $('<canvas/>');
                graph_view.append(canvas);
                let context = canvas[0].getContext('2d');
                new Chart(context, {
                    type: 'groupableBar',
                    data: data,
                    options: {
                        legend: {
                            labels: {
                                generateLabels: function (chart) {
                                    return Chart.defaults.global.legend.labels.generateLabels.apply(this, [chart]).filter(function (item, i) {
                                        return i <= 4;
                                    });
                                }
                            }
                        },
                        scales: {
                            yAxes: [{
                                stacked: true,
                                ticks: {
                                    callback: (value, index, values) => self._formatCurrencyValue(value, 'compact')
                                }
                            }]
                        },
                        tooltips: {
                            callbacks: {
                                label: (tooltipItem, data) => {
                                    let label = (data.datasets[tooltipItem.datasetIndex].label + ': ') || '';
                                    let value = self._formatCurrencyValue((data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index] || 0));
                                    return label + value;
                                }
                            }
                        },
                    }
                });
            } else {
                return this._super.apply(this, arguments);
            }
        },
        _prepare_stack_group_chart_data() {
            let result = {};
            result.labels = this.graph.label;
            result.datasets = [{
                label: this.graph.data[0].label, // Income - stack 1
                backgroundColor: this.graph.data[0].backgroundColor,
                data: this.graph.data[0].data,
                stack: 1
            }, {
                label: this.graph.data[1].label, // Operating Expense
                backgroundColor: this.graph.data[1].backgroundColor,
                data: Array(this.graph.data[1].data.length).fill(0),
                stack: 1
            }, {
                label: this.graph.data[2].label, // Cost of Revenue
                backgroundColor: this.graph.data[2].backgroundColor,
                data: Array(this.graph.data[2].data.length).fill(0),
                stack: 1
            }, {
                label: this.graph.data[3].label, // Depreciation
                backgroundColor: this.graph.data[3].backgroundColor,
                data: Array(this.graph.data[3].data.length).fill(0),
                stack: 1
            }, {
                label: this.graph.data[4].label, // Other Expense
                backgroundColor: this.graph.data[4].backgroundColor,
                data: Array(this.graph.data[4].data.length).fill(0),
                stack: 1
            }, {
                label: this.graph.data[0].label, // Income - stack 2
                backgroundColor: this.graph.data[0].backgroundColor,
                data: Array(this.graph.data[0].data.length).fill(0),
                stack: 2
            }, {
                label: this.graph.data[1].label, // Operating Expense
                backgroundColor: this.graph.data[1].backgroundColor,
                data: this.graph.data[1].data,
                stack: 2
            }, {
                label: this.graph.data[2].label, // Cost of Revenue
                backgroundColor: this.graph.data[2].backgroundColor,
                data: this.graph.data[2].data,
                stack: 2
            }, {
                label: this.graph.data[3].label, // Depreciation
                backgroundColor: this.graph.data[3].backgroundColor,
                data: this.graph.data[3].data,
                stack: 2
            }, {
                label: this.graph.data[4].label, // Other Expense
                backgroundColor: this.graph.data[4].backgroundColor,
                data: this.graph.data[4].data,
                stack: 2
            }];
            return result;
        }
    });
});
