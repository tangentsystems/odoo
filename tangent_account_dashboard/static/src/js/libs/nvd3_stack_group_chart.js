nv.models.GroupedStackedBarChart = function () {
    "use strict";

    //============================================================
    // Public Variables with Default Settings
    //------------------------------------------------------------

    var legend = nv.models.legend()
        , xAxis = nv.models.axis()
        , yAxis = nv.models.axis()
        , interactiveLayer = nv.interactiveGuideline()
        , controls = nv.models.legend()
        , tooltip = nv.models.tooltip()
        , valueFormat = null
    ;

    var margin = {top: 30, right: 20, bottom: 50, left: 60}
        , marginTop = null
        , width = null
        , height = null
        , color = nv.utils.defaultColor()
        , percentageMode = true
        , x0 //can be accessed via chart.xScale()
        , x1 //can be accessed via chart.xScale()
        , x2 //can be accessed via chart.xScale()
        , y //can be accessed via chart.yScale()
        , dispatch = d3.dispatch('stateChange', 'changeState', 'renderEnd', 'elementMouseover', 'elementMouseout', 'elementMousemove')
        , duration = 250
        , useInteractiveGuideline = false
    ;
    var renderWatch = nv.utils.renderWatch(dispatch, duration);

    tooltip.headerFormatter(function(d, i) {
                return xAxis.tickFormat()(d, i);
            });

    function chart(selection) {
        renderWatch.reset();

        selection.each(function (data) {
            var container = d3.select(this), yBegin;
            container.selectAll('.nv-gsBarHorizontal').remove();
            let fullWidth = width || container.style('width').replace('px', ''),
                fullHeight = height || container.style('height').replace('px', '');
            var availableWidth = fullWidth - margin.left - margin.right
                , availableHeight = fullHeight - margin.top - margin.bottom;

            nv.utils.initSVG(container);

            // var svg = container
            //     .append('svg')
            // .attr('width', width + margin.left + margin.right)
            // .attr('height', height + margin.top + margin.bottom)
            // .append('g')
            // .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
            var wrap = container
                .selectAll('g.nv-wrap.nv-gsBarHorizontal')
                .data([data]);
            var wrapEnter = wrap.enter()
                .append('g')
                .attr('class', 'nvd3 nv-wrap nv-gsBarHorizontal');
            var g = wrap.select('g');

            wrapEnter.append('g').attr('class', 'nv-x nv-axis');
            wrapEnter.append('g').attr('class', 'nv-y nv-axis');
            wrapEnter.append('g').attr('class', 'nv-barsWrap');
            wrapEnter.append('g').attr('class', 'nv-legendWrap');
            wrapEnter.append('g').attr('class', 'nv-controlsWrap');
            wrapEnter.append('g').attr('class', 'nv-interactive');
            wrap.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

            chart.update = function () {
                if (duration === 0)
                    container.call(chart);
                else
                    container.transition()
                        .duration(duration)
                        .call(chart);
            };
            chart.container = this;

            // Setup Scales
            x0 = d3.scale.ordinal().rangeRoundBands([0, availableWidth], 0.1);
            x1 = d3.scale.ordinal();
            x2 = d3.scale.ordinal();
            y = d3.scale.linear().range([availableHeight, 0]);

            var groupDataDict = {};
            data.forEach(function (data_item) {
                data_item.groups.forEach(function (g) {
                    let curGroup = groupDataDict[g.group_key];
                    if (curGroup === undefined) {
                        curGroup = {};
                        curGroup.group_key = g.group_key;
                        curGroup.group_label = g.group_label;
                        curGroup.total = 0;
                        curGroup.items = {};
                        groupDataDict[g.group_key] = curGroup;
                    }
                    g.stacks.forEach(function (s) {
                        let curStack = curGroup.items[s.stack_key + '-' + data_item.key];
                        if (curStack === undefined) {
                            curStack = {};
                            curStack.name = data_item.label;
                            curStack.item_key = data_item.key;
                            curStack.value = s.stack_value;
                            curStack.stack_name = s.stack_label;
                            curStack.stack_key = s.stack_key;
                            curStack.color = data_item.color;

                            curGroup[curStack.item_key + '-' + curStack.stack_key] = curStack.value;
                            let total_stack = curGroup['total_stack-' + curStack.stack_key];
                            if (total_stack === undefined) {
                                total_stack = 0;
                            }
                            curStack.yBegin = total_stack;
                            curStack.yEnd = total_stack + curStack.value;
                            curGroup['total_stack-' + curStack.stack_key] = curStack.yEnd;
                            curGroup.total += curStack.value;

                            curGroup.items[s.stack_key + '-' + data_item.key] = curStack;
                        }
                    });
                    curGroup.total = d3.max(d3.values(curGroup.items), function (d) {
                        return d.yEnd;
                    });
                });
            });
            if (percentageMode) {
                for (let g in groupDataDict) {
                    let groupData = groupDataDict[g];
                    d3.values(groupData.items).forEach(function (d) {
                        d.value = d.value * 100 / groupData['total_stack-' + d.stack_key];
                        d.yBegin = d.yBegin * 100 / groupData['total_stack-' + d.stack_key];
                        d.yEnd = d.yEnd * 100 / groupData['total_stack-' + d.stack_key];
                    });
                    groupData.total = 100;
                }
            }

            //get month names
            let
                groupsKey = d3.keys(groupDataDict)
                , groupsLabel = (function () {
                    let result = [];
                    for (let g in groupsKey) {
                        let groupKey = groupsKey[g];
                        result.push(groupDataDict[groupKey].group_label)
                    }
                    return result;
                })()
                , stacksLabel = (function () {
                    let result = [];
                    for (let g in groupsKey) {
                        let groupKey = groupsKey[g]
                            , groupData = groupDataDict[groupKey];
                        let stacks = [];
                        for (let s in groupData.items) {
                            let item = groupData.items[s];
                            if (stacks.indexOf(item.stack_name) < 0) {
                                stacks.push(item.stack_name)
                            }
                        }
                        result = result.concat(stacks)
                    }
                    return result;
                })()
                , itemsInfo = (function () {
                    let result = []
                        , items_key = [];
                    for (let g in groupsKey) {
                        let groupKey = groupsKey[g]
                            , groupData = groupDataDict[groupKey]
                            , stacks = [];
                        for (let s in groupData.items) {
                            let item_data = groupData.items[s];
                            if (items_key.indexOf(item_data.item_key) < 0) {
                                items_key.push(item_data.item_key);
                                result.push({
                                    'item_key': item_data.item_key,
                                    'color': item_data.color,
                                    'name': item_data.name,
                                    'stack_name': item_data.stack_name
                                })
                            }
                        }
                        result.concat(stacks)
                    }
                    return result;
                })();

            x0.domain(groupsLabel).rangeRoundBands([0, availableWidth], 0.015, 0.01);

            x2.domain(d3.keys(stacksLabel)).rangeRoundBands([0, availableWidth], 0, 0);
            //get something
            x1.domain(stacksLabel).rangeRoundBands([0, x0.rangeBand()], .01, 0);

            //set y domain, get totals
            y.domain([0, d3.max(d3.values(groupDataDict), function (d) {
                return d.total;
            })]);


            let stackedBars = wrap.selectAll(".stackedBars")
                .data(d3.values(groupDataDict))
                .enter().append('g')
                .attr({
                    //styling
                    'class': function (d) {
                        return 'group-col ' + d.group_key;
                    },
                    'transform': function (d) {
                        return "translate(" + x0(d.group_label) + ",0)";
                    }
                })
                , bars = stackedBars.selectAll("rect")
                .data(function (d) {
                    return d3.values(d.items);
                });

            bars
                .enter().append("rect")
                .attr({
                    //coords
                    'x': function (d) {
                        return x1(d.stack_name) + 1
                    },
                    'y': availableHeight,

                    //style
                    'fill': function (d) {
                        return d.color;
                    },
                    'width': x1.rangeBand(),
                    'height': 0,
                    'class': 'item',

                    //data entry
                    'data-name': function (d) {
                        return d.name;
                    },
                    'data-value': function (d) {
                        return d.value;
                    },
                    'data-stack': function (d) {
                        return d.stack_key;
                    }
                }).on('mouseover', function(d, i) {
                    // Tooltips
                    d3.select(this).classed('hover', true);
                    var evt = {};
                    var class_name_arr = [];
                    if (d instanceof Array && d.length) {
                        evt = {
                            series: {
                                key: d[0].key,
                                value: d[0].groups[0].stacks[0].stack_value,
                                color: d[0].color
                            },
                            value: d[0].groups[0].group_label
                        };
                    } else {
                        class_name_arr = d3.select(this.parentNode).attr('class').split(' ');
                        evt = {
                            series: {
                                key: d.name,
                                value: d.value,
                                color: d.color
                            },
                            value: class_name_arr[1] + ' ' + class_name_arr[2]
                        };
                    }
                    tooltip.data(evt).hidden(false);
                }).on('mouseout', function(evt) {
                    tooltip.hidden(true);
                }).on('mousemove', function (evt) {
                    tooltip();
                });

            bars
                .transition()
                .duration(duration)
                .attr({
                    //coords
                    'y': function (d) {
                        return y(d.yEnd)
                    },

                    //style
                    'height': function (d) {
                        var height = y(d.yBegin) - y(d.yEnd);
                        if (height < 0) {
                            height = 0;
                        }
                        return height;
                    }
                });

            //legend items
            wrap.selectAll(".group-col")
                .data(d3.values(groupDataDict))
                .append('g')
                .attr({
                    'class': 'legend-item',

                    'text-anchor': 'middle',
                    'transform': function () {
                        return 'translate(' + wrap.select('.item').attr('width') + ',' + parseInt(height + margin.top) + ')';
                    }
                });

            // Stack labels
            // xAxis = d3.svg.axis()
            //     .scale(x2)
            //     .orient('bottom')
            //     .tickSize(0)
            //     .tickFormat(function (d) {
            //         return stacksLabel[d];
            //     }).outerTickSize(0);
            // wrap.append('g')
            //     .attr('class', 'x axis')
            //     .attr('transform', 'translate(' + (0.1) + ',' + availableHeight + ')')
            //     .call(xAxis);

            // Group labels
            var xAxisGroup = d3.svg.axis()
                .scale(x0)
                .orient('bottom')
                .tickFormat(function (d) {

                    return d;
                }).outerTickSize(0);
            wrap.append('g')
                .attr({
                    'transform': 'translate(0,' + (availableHeight) + ')',
                    'class': 'x axis-group'
                })
                .call(xAxisGroup);

            yAxis
                .scale(y)
                .orient('left')
                .showMaxMin(true)
                ._ticks(nv.utils.calcTicksY(availableWidth / 100, data))
                .tickSize(-availableHeight, 0)
                .tickFormat(valueFormat);

            wrap.append('g')
                .attr('class', 'y axis')
                .call(yAxis);

            // Legend
            legend.width(availableWidth);
            wrap.select('.nv-legendWrap')
                .datum(data)
                .call(legend);
            if (margin.top !== legend.height()) {
                margin.top = legend.height();
                availableHeight = nv.utils.availableHeight(height, container, margin);
            }
            wrap.select('.nv-legendWrap')
                .attr('transform', 'translate(0,' + (-margin.top) + ')');

            // Reduce ticks on x axis
            wrap.select('.axis-group').selectAll('.tick').filter(function (d, i) {
                return i % Math.ceil(data[0].groups.length / (availableWidth / 100)) !== 0;
            }).selectAll('text, line').style('opacity', 0);

            // Remove tick bar of y axis
            wrap.select('.y.axis').selectAll('.tick').remove();
        });

        renderWatch.renderEnd('groupedstackedbarchart immediate');
        return chart;
    }

    //============================================================
    // Expose Public Variables
    //------------------------------------------------------------

    chart.xAxis = xAxis;
    chart.yAxis = yAxis;
    chart.tooltip = tooltip;
    chart.options = nv.utils.optionsFunc.bind(chart);
    //
    chart._options = Object.create({}, {
        width: {
            get: function () {
                return width;
            }, set: function (_) {
                width = _;
            }
        },
        height: {
            get: function () {
                return height;
            }, set: function (_) {
                height = _;
            }
        },
        percentageMode: {
            get: function () {
                return percentageMode;
            }, set: function (_) {
                percentageMode = _;
            }
        },
        duration: {
            get: function () {
                return duration;
            }, set: function (_) {
                duration = _;
                xAxis.duration(duration);
                yAxis.duration(duration);
                renderWatch.reset(duration);
            }
        },
        valueFormat: {
            get: function () {
                return valueFormat;
            },
            set: function (_) {
                valueFormat = _;
            }
        }
    });

    nv.utils.initOptions(chart);

    return chart;
};