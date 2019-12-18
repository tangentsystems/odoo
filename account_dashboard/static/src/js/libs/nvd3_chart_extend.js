odoo.define('account_dashboard.graph_extensions', function () {
    'use strict';

    nv.models.multiBarHorizontalChart = function() {
        //============================================================
        // Public Variables with Default Settings
        //------------------------------------------------------------

        var multibar = nv.models.multiBarHorizontal()
            , xAxis = nv.models.axis()
            , yAxis = nv.models.axis()
            , legend = nv.models.legend().height(30)
            , controls = nv.models.legend().height(30)
            , tooltip = nv.models.tooltip()
        ;

        var margin = {top: 30, right: 20, bottom: 50, left: 60}
            , marginTop = null
            , width = null
            , height = null
            , color = nv.utils.defaultColor()
            , showControls = true
            , controlsPosition = 'top'
            , controlLabels = {}
            , showLegend = true
            , legendPosition = 'top'
            , showXAxis = true
            , showYAxis = true
            , stacked = false
            , x //can be accessed via chart.xScale()
            , y //can be accessed via chart.yScale()
            , state = nv.utils.state()
            , defaultState = null
            , noData = null
            , dispatch = d3.dispatch('stateChange', 'changeState','renderEnd')
            , controlWidth = function() { return showControls ? 180 : 0 }
            , duration = 250
        ;

        state.stacked = false; // DEPRECATED Maintained for backward compatibility

        multibar.stacked(stacked);

        xAxis
            .orient('left')
            .tickPadding(5)
            .showMaxMin(false)
            .tickFormat(function(d) { return d })
        ;
        yAxis
            .orient('bottom')
            .tickFormat(d3.format(',.1f'))
        ;

        tooltip
            .duration(0)
            .valueFormatter(function(d, i) {
                return yAxis.tickFormat()(d, i);
            })
            .headerFormatter(function(d, i) {
                return xAxis.tickFormat()(d, i);
            });

        controls.updateState(false);

        //============================================================
        // Private Variables
        //------------------------------------------------------------

        var stateGetter = function(data) {
            return function(){
                return {
                    active: data.map(function(d) { return !d.disabled }),
                    stacked: stacked
                };
            }
        };

        var stateSetter = function(data) {
            return function(state) {
                if (state.stacked !== undefined)
                    stacked = state.stacked;
                if (state.active !== undefined)
                    data.forEach(function(series,i) {
                        series.disabled = !state.active[i];
                    });
            }
        };

        var renderWatch = nv.utils.renderWatch(dispatch, duration);

        function chart(selection) {
            renderWatch.reset();
            renderWatch.models(multibar);
            if (showXAxis) renderWatch.models(xAxis);
            if (showYAxis) renderWatch.models(yAxis);

            selection.each(function(data) {
                var container = d3.select(this),
                    that = this;
                nv.utils.initSVG(container);
                var availableWidth = nv.utils.availableWidth(width, container, margin),
                    availableHeight = nv.utils.availableHeight(height, container, margin);

                chart.update = function() { container.transition().duration(duration).call(chart) };
                chart.container = this;

                stacked = multibar.stacked();

                state
                    .setter(stateSetter(data), chart.update)
                    .getter(stateGetter(data))
                    .update();

                // DEPRECATED set state.disableddisabled
                state.disabled = data.map(function(d) { return !!d.disabled });

                if (!defaultState) {
                    var key;
                    defaultState = {};
                    for (key in state) {
                        if (state[key] instanceof Array)
                            defaultState[key] = state[key].slice(0);
                        else
                            defaultState[key] = state[key];
                    }
                }

                // Display No Data message if there's nothing to show.
                if (!data || !data.length || !data.filter(function(d) { return d.values.length }).length) {
                    nv.utils.noData(chart, container)
                    return chart;
                } else {
                    container.selectAll('.nv-noData').remove();
                }

                // Setup Scales
                x = multibar.xScale();
                y = multibar.yScale().clamp(true);

                // Setup containers and skeleton of chart
                var wrap = container.selectAll('g.nv-wrap.nv-multiBarHorizontalChart').data([data]);
                var gEnter = wrap.enter().append('g').attr('class', 'nvd3 nv-wrap nv-multiBarHorizontalChart').append('g');
                var g = wrap.select('g');

                gEnter.append('g').attr('class', 'nv-x nv-axis');
                gEnter.append('g').attr('class', 'nv-y nv-axis')
                    .append('g').attr('class', 'nv-zeroLine')
                    .append('line');
                gEnter.append('g').attr('class', 'nv-barsWrap');
                gEnter.append('g').attr('class', 'nv-legendWrap');
                gEnter.append('g').attr('class', 'nv-controlsWrap');

                // Legend
                if (!showLegend) {
                    g.select('.nv-legendWrap').selectAll('*').remove();
                } else {
                    legend.width(availableWidth - controlWidth());

                    g.select('.nv-legendWrap')
                        .datum(data)
                        .call(legend);
                    if (legendPosition === 'bottom') {
                        margin.bottom = xAxis.height() + legend.height();
                        availableHeight = nv.utils.availableHeight(height, container, margin);
                        g.select('.nv-legendWrap')
                            .attr('transform', 'translate(' + controlWidth() + ',' + (availableHeight + xAxis.height())  +')');
                    } else if (legendPosition === 'top') {

                        if (!marginTop && legend.height() !== margin.top) {
                            margin.top = legend.height();
                            availableHeight = nv.utils.availableHeight(height, container, margin);
                        }

                        g.select('.nv-legendWrap')
                            .attr('transform', 'translate(' + controlWidth() + ',' + (-margin.top) +')');
                    }
                }

                // Controls
                if (!showControls) {
                    g.select('.nv-controlsWrap').selectAll('*').remove();
                } else {
                    var controlsData = [
                        { key: controlLabels.grouped || 'Grouped', disabled: multibar.stacked() },
                        { key: controlLabels.stacked || 'Stacked', disabled: !multibar.stacked() }
                    ];

                    controls.width(controlWidth()).color(['#444', '#444', '#444']);

                    if (controlsPosition === 'bottom') {
                        margin.bottom = xAxis.height() + legend.height();
                        availableHeight = nv.utils.availableHeight(height, container, margin);
                        g.select('.nv-controlsWrap')
                            .datum(controlsData)
                            .attr('transform', 'translate(0,' + (availableHeight + xAxis.height()) +')')
                            .call(controls);

                    } else if (controlsPosition === 'top') {
                        g.select('.nv-controlsWrap')
                            .datum(controlsData)
                            .attr('transform', 'translate(0,' + (-margin.top) +')')
                            .call(controls);
                    }
                }

                wrap.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

                // Main Chart Component(s)
                multibar
                    .disabled(data.map(function(series) { return series.disabled }))
                    .width(availableWidth)
                    .height(availableHeight)
                    .color(data.map(function(d,i) {
                        return d.color || color(d, i);
                    }).filter(function(d,i) { return !data[i].disabled }));

                var barsWrap = g.select('.nv-barsWrap')
                    .datum(data.filter(function(d) { return !d.disabled }));

                barsWrap.transition().call(multibar);

                // Setup Axes
                if (showXAxis) {
                    xAxis
                        .scale(x)
                        ._ticks( nv.utils.calcTicksY(availableHeight/24, data) )
                        .tickSize(-availableWidth, 0);

                    g.select('.nv-x.nv-axis').call(xAxis);

                    var xTicks = g.select('.nv-x.nv-axis').selectAll('g');

                    xTicks
                        .selectAll('line, text');
                }

                if (showYAxis) {
                    yAxis
                        .scale(y)
                        ._ticks( nv.utils.calcTicksX(availableWidth/100, data) )
                        .tickSize( -availableHeight, 0);

                    g.select('.nv-y.nv-axis')
                        .attr('transform', 'translate(0,' + availableHeight + ')');
                    g.select('.nv-y.nv-axis').call(yAxis);
                }

                // Zero line
                g.select(".nv-zeroLine line")
                    .attr("x1", y(0))
                    .attr("x2", y(0))
                    .attr("y1", 0)
                    .attr("y2", -availableHeight)
                ;

                //============================================================
                // Event Handling/Dispatching (in chart's scope)
                //------------------------------------------------------------

                legend.dispatch.on('stateChange', function(newState) {
                    for (var key in newState)
                        state[key] = newState[key];
                    dispatch.stateChange(state);
                    chart.update();
                });

                controls.dispatch.on('legendClick', function(d,i) {
                    if (!d.disabled) return;
                    controlsData = controlsData.map(function(s) {
                        s.disabled = true;
                        return s;
                    });
                    d.disabled = false;

                    switch (d.key) {
                        case 'Grouped':
                        case controlLabels.grouped:
                            multibar.stacked(false);
                            break;
                        case 'Stacked':
                        case controlLabels.stacked:
                            multibar.stacked(true);
                            break;
                    }

                    state.stacked = multibar.stacked();
                    dispatch.stateChange(state);
                    stacked = multibar.stacked();

                    chart.update();
                });

                // Update chart from a state object passed to event handler
                dispatch.on('changeState', function(e) {

                    if (typeof e.disabled !== 'undefined') {
                        data.forEach(function(series,i) {
                            series.disabled = e.disabled[i];
                        });

                        state.disabled = e.disabled;
                    }

                    if (typeof e.stacked !== 'undefined') {
                        multibar.stacked(e.stacked);
                        state.stacked = e.stacked;
                        stacked = e.stacked;
                    }

                    chart.update();
                });
            });
            renderWatch.renderEnd('multibar horizontal chart immediate');
            return chart;
        }

        //============================================================
        // Event Handling/Dispatching (out of chart's scope)
        //------------------------------------------------------------

        multibar.dispatch.on('elementMouseover.tooltip', function(evt) {
            evt.value = chart.x()(evt.data);
            evt['series'] = {
                key: evt.data.key,
                value: chart.y()(evt.data),
                color: evt.color
            };
            tooltip.data(evt).hidden(false);
        });

        multibar.dispatch.on('elementMouseout.tooltip', function(evt) {
            tooltip.hidden(true);
        });

        multibar.dispatch.on('elementMousemove.tooltip', function(evt) {
            tooltip();
        });

        //============================================================
        // Expose Public Variables
        //------------------------------------------------------------

        // expose chart's sub-components
        chart.dispatch = dispatch;
        chart.multibar = multibar;
        chart.legend = legend;
        chart.controls = controls;
        chart.xAxis = xAxis;
        chart.yAxis = yAxis;
        chart.state = state;
        chart.tooltip = tooltip;

        chart.options = nv.utils.optionsFunc.bind(chart);

        chart._options = Object.create({}, {
            // simple options, just get/set the necessary values
            width:      {get: function(){return width;}, set: function(_){width=_;}},
            height:     {get: function(){return height;}, set: function(_){height=_;}},
            showLegend: {get: function(){return showLegend;}, set: function(_){showLegend=_;}},
            legendPosition: {get: function(){return legendPosition;}, set: function(_){legendPosition=_;}},
            controlsPosition: {get: function(){return controlsPosition;}, set: function(_){controlsPosition=_;}},
            showControls: {get: function(){return showControls;}, set: function(_){showControls=_;}},
            controlLabels: {get: function(){return controlLabels;}, set: function(_){controlLabels=_;}},
            showXAxis:      {get: function(){return showXAxis;}, set: function(_){showXAxis=_;}},
            showYAxis:    {get: function(){return showYAxis;}, set: function(_){showYAxis=_;}},
            defaultState:    {get: function(){return defaultState;}, set: function(_){defaultState=_;}},
            noData:    {get: function(){return noData;}, set: function(_){noData=_;}},

            // options that require extra logic in the setter
            margin: {get: function(){return margin;}, set: function(_){
                if (_.top !== undefined) {
                    margin.top = _.top;
                    marginTop = _.top;
                }
                margin.right  = _.right  !== undefined ? _.right  : margin.right;
                margin.bottom = _.bottom !== undefined ? _.bottom : margin.bottom;
                margin.left   = _.left   !== undefined ? _.left   : margin.left;
            }},
            duration: {get: function(){return duration;}, set: function(_){
                duration = _;
                renderWatch.reset(duration);
                multibar.duration(duration);
                xAxis.duration(duration);
                yAxis.duration(duration);
            }},
            color:  {get: function(){return color;}, set: function(_){
                color = nv.utils.getColor(_);
                legend.color(color);
            }},
            barColor:  {get: function(){return multibar.barColor;}, set: function(_){
                multibar.barColor(_);
                legend.color(function(d,i) {return d3.rgb('#ccc').darker(i * 1.5).toString();})
            }}
        });

        nv.utils.inheritOptions(chart, multibar);
        nv.utils.initOptions(chart);

        return chart;
    };
    nv.models.multiBarHorizontal = function() {
        //============================================================
        // Public Variables with Default Settings
        //------------------------------------------------------------

        var margin = {top: 0, right: 0, bottom: 0, left: 0}
            , width = 960
            , height = 500
            , id = Math.floor(Math.random() * 10000) //Create semi-unique ID in case user doesn't select one
            , container = null
            , x = d3.scale.ordinal()
            , y = d3.scale.linear()
            , getX = function(d) { return d.x }
            , getY = function(d) { return d.y }
            , getYerr = function(d) { return d.yErr }
            , forceY = [0] // 0 is forced by default.. this makes sense for the majority of bar graphs... user can always do chart.forceY([]) to remove
            , color = nv.utils.defaultColor()
            , barColor = null // adding the ability to set the color for each rather than the whole group
            , disabled // used in conjunction with barColor to communicate from multiBarHorizontalChart what series are disabled
            , stacked = false
            , showValues = false
            , showBarLabels = false
            , valuePadding = 60
            , groupSpacing = 0.1
            , fillOpacity = 0.75
            , valueFormat = d3.format(',.2f')
            , delay = 1200
            , xDomain
            , yDomain
            , xRange
            , yRange
            , duration = 250
            , dispatch = d3.dispatch('chartClick', 'elementClick', 'elementDblClick', 'elementMouseover', 'elementMouseout', 'elementMousemove', 'renderEnd')
        ;

        //============================================================
        // Private Variables
        //------------------------------------------------------------

        var x0, y0; //used to store previous scales
        var renderWatch = nv.utils.renderWatch(dispatch, duration);

        function chart(selection) {
            renderWatch.reset();
            selection.each(function(data) {
                var availableWidth = width - margin.left - margin.right,
                    availableHeight = height - margin.top - margin.bottom;

                container = d3.select(this);
                nv.utils.initSVG(container);

                if (stacked)
                    data = d3.layout.stack()
                        .offset('zero')
                        .values(function(d){ return d.values })
                        .y(getY)
                        (data);

                //add series index and key to each data point for reference
                data.forEach(function(series, i) {
                    series.values.forEach(function(point) {
                        point.series = i;
                        point.key = series.key;
                    });
                });

                // HACK for negative value stacking
                if (stacked)
                    data[0].values.map(function(d,i) {
                        var posBase = 0, negBase = 0;
                        data.map(function(d) {
                            var f = d.values[i]
                            f.size = Math.abs(f.y);
                            if (f.y<0)  {
                                f.y1 = negBase - f.size;
                                negBase = negBase - f.size;
                            } else
                            {
                                f.y1 = posBase;
                                posBase = posBase + f.size;
                            }
                        });
                    });

                // Setup Scales
                // remap and flatten the data for use in calculating the scales' domains
                var seriesData = (xDomain && yDomain) ? [] : // if we know xDomain and yDomain, no need to calculate
                    data.map(function(d) {
                        return d.values.map(function(d,i) {
                            return { x: getX(d,i), y: getY(d,i), y0: d.y0, y1: d.y1 }
                        })
                    });

                x.domain(xDomain || d3.merge(seriesData).map(function(d) { return d.x }))
                    .rangeBands(xRange || [0, availableHeight], groupSpacing);

                y.domain(yDomain || d3.extent(d3.merge(seriesData).map(function(d) { return stacked ? (d.y > 0 ? d.y1 + d.y : d.y1 ) : d.y }).concat(forceY)))

                if (showValues && !stacked)
                    y.range(yRange || [(y.domain()[0] < 0 ? valuePadding : 0), availableWidth - (y.domain()[1] > 0 ? valuePadding : 0) ]);
                else
                    y.range(yRange || [0, availableWidth]);

                x0 = x0 || x;
                y0 = y0 || d3.scale.linear().domain(y.domain()).range([y(0),y(0)]);

                // Setup containers and skeleton of chart
                var wrap = d3.select(this).selectAll('g.nv-wrap.nv-multibarHorizontal').data([data]);
                var wrapEnter = wrap.enter().append('g').attr('class', 'nvd3 nv-wrap nv-multibarHorizontal');
                var defsEnter = wrapEnter.append('defs');
                var gEnter = wrapEnter.append('g');
                var g = wrap.select('g');

                gEnter.append('g').attr('class', 'nv-groups');
                wrap.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

                var groups = wrap.select('.nv-groups').selectAll('.nv-group')
                    .data(function(d) { return d }, function(d,i) { return i });
                groups.enter().append('g')
                    .style('stroke-opacity', 1e-6)
                    .style('fill-opacity', 1e-6);
                groups.exit().watchTransition(renderWatch, 'multibarhorizontal: exit groups')
                    .style('stroke-opacity', 1e-6)
                    .style('fill-opacity', 1e-6)
                    .remove();
                groups
                    .attr('class', function(d,i) { return 'nv-group nv-series-' + i })
                    .classed('hover', function(d) { return d.hover })
                    .style('fill', function(d,i){ return color(d, i) })
                    .style('stroke', function(d,i){ return color(d, i) });
                groups.watchTransition(renderWatch, 'multibarhorizontal: groups')
                    .style('stroke-opacity', 1)
                    .style('fill-opacity', fillOpacity);

                var bars = groups.selectAll('g.nv-bar')
                    .data(function(d) { return d.values });
                bars.exit().remove();

                var barsEnter = bars.enter().append('g')
                    .attr('transform', function(d,i,j) {
                        return 'translate(' + y0(stacked ? d.y0 : 0) + ',' + (stacked ? 0 : (j * x.rangeBand() / data.length ) + x(getX(d,i))) + ')'
                    });

                barsEnter.append('rect')
                    .attr('width', 0)
                    .attr('height', x.rangeBand() / (stacked ? 1 : data.length) )

                bars
                    .on('mouseover', function(d,i) { //TODO: figure out why j works above, but not here
                        d3.select(this).classed('hover', true);
                        dispatch.elementMouseover({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill")
                        });
                    })
                    .on('mouseout', function(d,i) {
                        d3.select(this).classed('hover', false);
                        dispatch.elementMouseout({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill")
                        });
                    })
                    .on('mouseout', function(d,i) {
                        dispatch.elementMouseout({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill")
                        });
                    })
                    .on('mousemove', function(d,i) {
                        dispatch.elementMousemove({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill")
                        });
                    })
                    .on('click', function(d,i) {
                        var element = this;
                        dispatch.elementClick({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill"),
                            event: d3.event,
                            element: element
                        });
                        d3.event.stopPropagation();
                    })
                    .on('dblclick', function(d,i) {
                        dispatch.elementDblClick({
                            data: d,
                            index: i,
                            color: d3.select(this).style("fill")
                        });
                        d3.event.stopPropagation();
                    });

                if (getYerr(data[0],0)) {
                    barsEnter.append('polyline');

                    bars.select('polyline')
                        .attr('fill', 'none')
                        .attr('points', function(d,i) {
                            var xerr = getYerr(d,i)
                                , mid = 0.8 * x.rangeBand() / ((stacked ? 1 : data.length) * 2);
                            xerr = xerr.length ? xerr : [-Math.abs(xerr), Math.abs(xerr)];
                            xerr = xerr.map(function(e) { return y(e + ((getY(d,i) < 0) ? 0 : getY(d,i))) - y(0); });
                            var a = [[xerr[0],-mid], [xerr[0],mid], [xerr[0],0], [xerr[1],0], [xerr[1],-mid], [xerr[1],mid]];
                            return a.map(function (path) { return path.join(',') }).join(' ');
                        })
                        .attr('transform', function(d,i) {
                            var mid = x.rangeBand() / ((stacked ? 1 : data.length) * 2);
                            return 'translate(0, ' + mid + ')';
                        });
                }

                barsEnter.append('text');

                if (showValues && !stacked) {
                    bars.select('text')
                        .attr('text-anchor', function(d,i) { return getY(d,i) < 0 ? 'end' : 'start' })
                        .attr('y', x.rangeBand() / (data.length * 2))
                        .attr('dy', '.32em')
                        .text(function(d,i) {
                            var t = valueFormat(getY(d,i))
                                , yerr = getYerr(d,i);
                            if (yerr === undefined)
                                return t;
                            if (!yerr.length)
                                return t + '±' + valueFormat(Math.abs(yerr));
                            return t + '+' + valueFormat(Math.abs(yerr[1])) + '-' + valueFormat(Math.abs(yerr[0]));
                        });
                    bars.watchTransition(renderWatch, 'multibarhorizontal: bars')
                        .select('text')
                        .attr('x', function(d,i) { return getY(d,i) < 0 ? -4 : y(getY(d,i)) - y(0) + 4 })
                } else {
                    bars.selectAll('text').text('');
                }

                if (showBarLabels && !stacked) {
                    barsEnter.append('text').classed('nv-bar-label',true);
                    bars.select('text.nv-bar-label')
                        .attr('text-anchor', function(d,i) { return getY(d,i) < 0 ? 'start' : 'end' })
                        .attr('y', x.rangeBand() / (data.length * 2))
                        .attr('dy', '.32em')
                        .text(function(d,i) { return getX(d,i) });
                    bars.watchTransition(renderWatch, 'multibarhorizontal: bars')
                        .select('text.nv-bar-label')
                        .attr('x', function(d,i) { return getY(d,i) < 0 ? y(0) - y(getY(d,i)) + 4 : -4 });
                }
                else {
                    bars.selectAll('text.nv-bar-label').text('');
                }

                bars
                    .attr('class', function(d,i) { return getY(d,i) < 0 ? 'nv-bar negative' : 'nv-bar positive'})

                if (barColor) {
                    if (!disabled) disabled = data.map(function() { return true });
                    bars
                        .style('fill', function(d,i,j) { return d3.rgb(barColor(d,i)).darker(  disabled.map(function(d,i) { return i }).filter(function(d,i){ return !disabled[i]  })[j]   ).toString(); })
                        .style('stroke', function(d,i,j) { return d3.rgb(barColor(d,i)).darker(  disabled.map(function(d,i) { return i }).filter(function(d,i){ return !disabled[i]  })[j]   ).toString(); });
                }

                if (stacked)
                    bars.watchTransition(renderWatch, 'multibarhorizontal: bars')
                        .attr('transform', function(d,i) {
                            return 'translate(' + y(d.y1) + ',' + x(getX(d,i)) + ')'
                        })
                        .select('rect')
                        .attr('width', function(d,i) {
                            return Math.abs(y(getY(d,i) + d.y0) - y(d.y0)) || 0
                        })
                        .attr('height', x.rangeBand() );
                else
                    bars.watchTransition(renderWatch, 'multibarhorizontal: bars')
                        .attr('transform', function(d,i) {
                            //TODO: stacked must be all positive or all negative, not both?
                            return 'translate(' +
                                (getY(d,i) < 0 ? y(getY(d,i)) : y(0))
                                + ',' +
                                (d.series * x.rangeBand() / data.length
                                    +
                                    x(getX(d,i)) )
                                + ')'
                        })
                        .select('rect')
                        .attr('height', x.rangeBand() / data.length )
                        .attr('width', function(d,i) {
                            return Math.max(Math.abs(y(getY(d,i)) - y(0)),1) || 0
                        });

                //store old scales for use in transitions on update
                x0 = x.copy();
                y0 = y.copy();

            });

            renderWatch.renderEnd('multibarHorizontal immediate');
            return chart;
        }

        //============================================================
        // Expose Public Variables
        //------------------------------------------------------------

        chart.dispatch = dispatch;

        chart.options = nv.utils.optionsFunc.bind(chart);

        chart._options = Object.create({}, {
            // simple options, just get/set the necessary values
            width:   {get: function(){return width;}, set: function(_){width=_;}},
            height:  {get: function(){return height;}, set: function(_){height=_;}},
            x:       {get: function(){return getX;}, set: function(_){getX=_;}},
            y:       {get: function(){return getY;}, set: function(_){getY=_;}},
            yErr:       {get: function(){return getYerr;}, set: function(_){getYerr=_;}},
            xScale:  {get: function(){return x;}, set: function(_){x=_;}},
            yScale:  {get: function(){return y;}, set: function(_){y=_;}},
            xDomain: {get: function(){return xDomain;}, set: function(_){xDomain=_;}},
            yDomain: {get: function(){return yDomain;}, set: function(_){yDomain=_;}},
            xRange:  {get: function(){return xRange;}, set: function(_){xRange=_;}},
            yRange:  {get: function(){return yRange;}, set: function(_){yRange=_;}},
            forceY:  {get: function(){return forceY;}, set: function(_){forceY=_;}},
            stacked: {get: function(){return stacked;}, set: function(_){stacked=_;}},
            showValues: {get: function(){return showValues;}, set: function(_){showValues=_;}},
            // this shows the group name, seems pointless?
            //showBarLabels:    {get: function(){return showBarLabels;}, set: function(_){showBarLabels=_;}},
            disabled:     {get: function(){return disabled;}, set: function(_){disabled=_;}},
            id:           {get: function(){return id;}, set: function(_){id=_;}},
            valueFormat:  {get: function(){return valueFormat;}, set: function(_){valueFormat=_;}},
            valuePadding: {get: function(){return valuePadding;}, set: function(_){valuePadding=_;}},
            groupSpacing: {get: function(){return groupSpacing;}, set: function(_){groupSpacing=_;}},
            fillOpacity:  {get: function(){return fillOpacity;}, set: function(_){fillOpacity=_;}},

            // options that require extra logic in the setter
            margin: {get: function(){return margin;}, set: function(_){
                margin.top    = _.top    !== undefined ? _.top    : margin.top;
                margin.right  = _.right  !== undefined ? _.right  : margin.right;
                margin.bottom = _.bottom !== undefined ? _.bottom : margin.bottom;
                margin.left   = _.left   !== undefined ? _.left   : margin.left;
            }},
            duration: {get: function(){return duration;}, set: function(_){
                duration = _;
                renderWatch.reset(duration);
            }},
            color:  {get: function(){return color;}, set: function(_){
                color = nv.utils.getColor(_);
            }},
            barColor:  {get: function(){return barColor;}, set: function(_){
                barColor = _ ? nv.utils.getColor(_) : null;
            }}
        });

        nv.utils.initOptions(chart);

        return chart;
    };

    nv.models.multiChart = function() {
        "use strict";

        //============================================================
        // Public Variables with Default Settings
        //------------------------------------------------------------

        var margin = {top: 30, right: 20, bottom: 50, left: 60},
            marginTop = null,
            color = nv.utils.defaultColor(),
            width = null,
            height = null,
            showLegend = true,
            noData = null,
            yDomain1,
            yDomain2,
            getX = function(d) { return d.x },
            getY = function(d) { return d.y},
            interpolate = 'linear',
            useVoronoi = true,
            interactiveLayer = nv.interactiveGuideline(),
            useInteractiveGuideline = false,
            legendRightAxisHint = ' (right axis)',
            duration = 250
        ;

        //============================================================
        // Private Variables
        //------------------------------------------------------------

        var x = d3.scale.linear(),
            padDataOuter = .1, //outerPadding to imitate ordinal scale outer padding

            yScale1 = d3.scale.linear(),
            yScale2 = d3.scale.linear(),

            lines1 = nv.models.line().yScale(yScale1).duration(duration),
            lines2 = nv.models.line().yScale(yScale2).duration(duration),

            scatters1 = nv.models.scatter().yScale(yScale1).duration(duration),
            scatters2 = nv.models.scatter().yScale(yScale2).duration(duration),

            bars1 = nv.models.multiBar().stacked(false).yScale(yScale1).duration(duration),
            bars2 = nv.models.multiBar().stacked(false).yScale(yScale2).duration(duration),

            stack1 = nv.models.stackedArea().yScale(yScale1).duration(duration),
            stack2 = nv.models.stackedArea().yScale(yScale2).duration(duration),

            xAxis = nv.models.axis().scale(x).orient('bottom').tickPadding(5).duration(duration),
            yAxis1 = nv.models.axis().scale(yScale1).orient('left').duration(duration),
            yAxis2 = nv.models.axis().scale(yScale2).orient('right').duration(duration),

            legend = nv.models.legend().height(30),
            tooltip = nv.models.tooltip(),
            dispatch = d3.dispatch();

        var charts = [lines1, lines2, scatters1, scatters2, bars1, bars2, stack1, stack2];

        function chart(selection) {
            selection.each(function(data) {
                var container = d3.select(this),
                    that = this;
                nv.utils.initSVG(container);

                chart.update = function() { container.transition().call(chart); };
                chart.container = this;

                var availableWidth = nv.utils.availableWidth(width, container, margin),
                    availableHeight = nv.utils.availableHeight(height, container, margin);

                var dataLines1 = data.filter(function(d) {return d.type == 'line' && d.yAxis == 1});
                var dataLines2 = data.filter(function(d) {return d.type == 'line' && d.yAxis == 2});
                var dataScatters1 = data.filter(function(d) {return d.type == 'scatter' && d.yAxis == 1});
                var dataScatters2 = data.filter(function(d) {return d.type == 'scatter' && d.yAxis == 2});
                var dataBars1 =  data.filter(function(d) {return d.type == 'bar'  && d.yAxis == 1});
                var dataBars2 =  data.filter(function(d) {return d.type == 'bar'  && d.yAxis == 2});
                var dataStack1 = data.filter(function(d) {return d.type == 'area' && d.yAxis == 1});
                var dataStack2 = data.filter(function(d) {return d.type == 'area' && d.yAxis == 2});

                // Display noData message if there's nothing to show.
                if (!data || !data.length || !data.filter(function(d) { return d.values.length }).length) {
                    nv.utils.noData(chart, container);
                    return chart;
                } else {
                    container.selectAll('.nv-noData').remove();
                }

                var series1 = data.filter(function(d) {return !d.disabled && d.yAxis == 1})
                    .map(function(d) {
                        return d.values.map(function(d,i) {
                            return { x: getX(d), y: getY(d) }
                        })
                    });

                var series2 = data.filter(function(d) {return !d.disabled && d.yAxis == 2})
                    .map(function(d) {
                        return d.values.map(function(d,i) {
                            return { x: getX(d), y: getY(d) }
                        })
                    });

                x   .domain(d3.extent(d3.merge(series1.concat(series2)), function(d) { return d.x }))
                    .range([0, availableWidth]);
                // .range([(availableWidth * padDataOuter +  availableWidth) / (2 *data[0].values.length), availableWidth - availableWidth * (1 + padDataOuter) / (2 * data[0].values.length)  ]);

                // x = lines1.xScale();
                var wrap = container.selectAll('g.wrap.multiChart').data([data]);
                var gEnter = wrap.enter().append('g').attr('class', 'wrap nvd3 multiChart').append('g');

                gEnter.append('g').attr('class', 'nv-x nv-axis');
                gEnter.append('g').attr('class', 'nv-y1 nv-axis');
                gEnter.append('g').attr('class', 'nv-y2 nv-axis');
                gEnter.append('g').attr('class', 'stack1Wrap');
                gEnter.append('g').attr('class', 'stack2Wrap');
                gEnter.append('g').attr('class', 'bars1Wrap');
                gEnter.append('g').attr('class', 'bars2Wrap');
                gEnter.append('g').attr('class', 'scatters1Wrap');
                gEnter.append('g').attr('class', 'scatters2Wrap');
                gEnter.append('g').attr('class', 'lines1Wrap');
                gEnter.append('g').attr('class', 'lines2Wrap');
                gEnter.append('g').attr('class', 'legendWrap');
                gEnter.append('g').attr('class', 'nv-interactive');

                var g = wrap.select('g');

                var color_array = data.map(function(d,i) {
                    return data[i].color || color(d, i);
                });

                // Legend
                if (!showLegend) {
                    g.select('.legendWrap').selectAll('*').remove();
                } else {
                    var legendWidth = legend.align() ? availableWidth / 2 : availableWidth;
                    var legendXPosition = legend.align() ? legendWidth : 0;

                    legend.width(legendWidth);
                    legend.color(color_array);

                    g.select('.legendWrap')
                        .datum(data.map(function(series) {
                            series.originalKey = series.originalKey === undefined ? series.key : series.originalKey;
                            series.key = series.originalKey + (series.yAxis == 1 ? '' : legendRightAxisHint);
                            return series;
                        }))
                        .call(legend);

                    if (!marginTop && legend.height() !== margin.top) {
                        margin.top = legend.height();
                        availableHeight = nv.utils.availableHeight(height, container, margin);
                    }

                    g.select('.legendWrap')
                        .attr('transform', 'translate(' + legendXPosition + ',' + (-margin.top) +')');
                }

                lines1
                    .width(availableWidth)
                    .height(availableHeight)
                    .interpolate(interpolate)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 1 && data[i].type == 'line'}));
                lines2
                    .width(availableWidth)
                    .height(availableHeight)
                    .interpolate(interpolate)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 2 && data[i].type == 'line'}));
                scatters1
                    .width(availableWidth)
                    .height(availableHeight)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 1 && data[i].type == 'scatter'}));
                scatters2
                    .width(availableWidth)
                    .height(availableHeight)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 2 && data[i].type == 'scatter'}));
                bars1
                    .width(availableWidth)
                    .height(availableHeight)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 1 && data[i].type == 'bar'}));
                bars2
                    .width(availableWidth)
                    .height(availableHeight)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 2 && data[i].type == 'bar'}));
                stack1
                    .width(availableWidth)
                    .height(availableHeight)
                    .interpolate(interpolate)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 1 && data[i].type == 'area'}));
                stack2
                    .width(availableWidth)
                    .height(availableHeight)
                    .interpolate(interpolate)
                    .color(color_array.filter(function(d,i) { return !data[i].disabled && data[i].yAxis == 2 && data[i].type == 'area'}));

                g.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

                var lines1Wrap = g.select('.lines1Wrap')
                    .datum(dataLines1.filter(function(d){return !d.disabled}));
                var scatters1Wrap = g.select('.scatters1Wrap')
                    .datum(dataScatters1.filter(function(d){return !d.disabled}));
                var bars1Wrap = g.select('.bars1Wrap')
                    .datum(dataBars1.filter(function(d){return !d.disabled}));
                var stack1Wrap = g.select('.stack1Wrap')
                    .datum(dataStack1.filter(function(d){return !d.disabled}));
                var lines2Wrap = g.select('.lines2Wrap')
                    .datum(dataLines2.filter(function(d){return !d.disabled}));
                var scatters2Wrap = g.select('.scatters2Wrap')
                    .datum(dataScatters2.filter(function(d){return !d.disabled}));
                var bars2Wrap = g.select('.bars2Wrap')
                    .datum(dataBars2.filter(function(d){return !d.disabled}));
                var stack2Wrap = g.select('.stack2Wrap')
                    .datum(dataStack2.filter(function(d){return !d.disabled}));

                var extraValue1 = dataStack1.length ? dataStack1.map(function(a){return a.values}).reduce(function(a,b){
                    return a.map(function(aVal,i){return {x: aVal.x, y: aVal.y + b[i].y}})
                }).concat([{x:0, y:0}]) : [];
                var extraValue2 = dataStack2.length ? dataStack2.map(function(a){return a.values}).reduce(function(a,b){
                    return a.map(function(aVal,i){return {x: aVal.x, y: aVal.y + b[i].y}})
                }).concat([{x:0, y:0}]) : [];

                yScale1 .domain(yDomain1 || d3.extent(d3.merge(series1).concat(extraValue1), function(d) { return d.y } ))
                    .range([0, availableHeight]);

                yScale2 .domain(yDomain2 || d3.extent(d3.merge(series2).concat(extraValue2), function(d) { return d.y } ))
                    .range([0, availableHeight]);

                lines1.yDomain(yScale1.domain());
                scatters1.yDomain(yScale1.domain());
                bars1.yDomain(yScale1.domain());
                stack1.yDomain(yScale1.domain());

                lines2.yDomain(yScale2.domain());
                scatters2.yDomain(yScale2.domain());
                bars2.yDomain(yScale2.domain());
                stack2.yDomain(yScale2.domain());

                if(dataStack1.length){d3.transition(stack1Wrap).call(stack1);}
                if(dataStack2.length){d3.transition(stack2Wrap).call(stack2);}

                if(dataBars1.length){d3.transition(bars1Wrap).call(bars1);}
                if(dataBars2.length){d3.transition(bars2Wrap).call(bars2);}

                if(dataLines1.length){d3.transition(lines1Wrap).call(lines1);}
                if(dataLines2.length){d3.transition(lines2Wrap).call(lines2);}

                if(dataScatters1.length){d3.transition(scatters1Wrap).call(scatters1);}
                if(dataScatters2.length){d3.transition(scatters2Wrap).call(scatters2);}

                // Set scale to padding the grid follow the line chart
                xAxis
                    .scale(lines1.xScale())
                    ._ticks( nv.utils.calcTicksX(availableWidth/100, data) )
                    .tickSize(-availableHeight, 0);

                g.select('.nv-x.nv-axis')
                    .attr('transform', 'translate(0,' + availableHeight + ')');
                d3.transition(g.select('.nv-x.nv-axis'))
                    .call(xAxis);

                yAxis1
                    ._ticks( nv.utils.calcTicksY(availableHeight/36, data) )
                    .tickSize( -availableWidth, 0);


                d3.transition(g.select('.nv-y1.nv-axis'))
                    .call(yAxis1);

                yAxis2
                    ._ticks( nv.utils.calcTicksY(availableHeight/36, data) )
                    .tickSize( -availableWidth, 0);

                d3.transition(g.select('.nv-y2.nv-axis'))
                    .call(yAxis2);

                g.select('.nv-y1.nv-axis')
                    .classed('nv-disabled', series1.length ? false : true)
                    .attr('transform', 'translate(' + x.range()[0] + ',0)');

                g.select('.nv-y2.nv-axis')
                    .classed('nv-disabled', series2.length ? false : true)
                    .attr('transform', 'translate(' + x.range()[1] + ',0)');

                legend.dispatch.on('stateChange', function(newState) {
                    chart.update();
                });

                if(useInteractiveGuideline){
                    interactiveLayer
                        .width(availableWidth)
                        .height(availableHeight)
                        .margin({left:margin.left, top:margin.top})
                        .svgContainer(container)
                        .xScale(lines1.xScale());
                    wrap.select(".nv-interactive").call(interactiveLayer);
                }

                // Variable save scope value of line1 to reuse in intertractive guide line
                var xScale = lines1.xScale();

                //============================================================
                // Event Handling/Dispatching
                //------------------------------------------------------------

                function mouseover_line(evt) {
                    var yaxis = data[evt.seriesIndex].yAxis === 2 ? yAxis2 : yAxis1;
                    evt.value = evt.point.x;
                    evt.series = {
                        value: evt.point.y,
                        color: evt.point.color,
                        key: evt.series.key
                    };
                    tooltip
                        .duration(0)
                        .headerFormatter(function(d, i) {
                            return xAxis.tickFormat()(d, i);
                        })
                        .valueFormatter(function(d, i) {
                            return yaxis.tickFormat()(d, i);
                        })
                        .data(evt)
                        .hidden(false);
                }

                function mouseover_scatter(evt) {
                    var yaxis = data[evt.seriesIndex].yAxis === 2 ? yAxis2 : yAxis1;
                    evt.value = evt.point.x;
                    evt.series = {
                        value: evt.point.y,
                        color: evt.point.color,
                        key: evt.series.key
                    };
                    tooltip
                        .duration(100)
                        .headerFormatter(function(d, i) {
                            return xAxis.tickFormat()(d, i);
                        })
                        .valueFormatter(function(d, i) {
                            return yaxis.tickFormat()(d, i);
                        })
                        .data(evt)
                        .hidden(false);
                }

                function mouseover_stack(evt) {
                    var yaxis = data[evt.seriesIndex].yAxis === 2 ? yAxis2 : yAxis1;
                    evt.point['x'] = stack1.x()(evt.point);
                    evt.point['y'] = stack1.y()(evt.point);
                    tooltip
                        .duration(0)
                        .headerFormatter(function(d, i) {
                            return xAxis.tickFormat()(d, i);
                        })
                        .valueFormatter(function(d, i) {
                            return yaxis.tickFormat()(d, i);
                        })
                        .data(evt)
                        .hidden(false);
                }

                function mouseover_bar(evt) {
                    var yaxis = data[evt.data.series].yAxis === 2 ? yAxis2 : yAxis1;

                    evt.value = bars1.x()(evt.data);
                    evt['series'] = {
                        value: bars1.y()(evt.data),
                        color: evt.color,
                        key: evt.data.key
                    };
                    tooltip
                        .duration(0)
                        .headerFormatter(function(d, i) {
                            return xAxis.tickFormat()(d, i);
                        })
                        .valueFormatter(function(d, i) {
                            return yaxis.tickFormat()(d, i);
                        })
                        .data(evt)
                        .hidden(false);
                }



                function clearHighlights() {
                    for(var i=0, il=charts.length; i < il; i++){
                        var chart = charts[i];
                        try {
                            chart.clearHighlights();
                        } catch(e){}
                    }
                }

                function highlightPoint(serieIndex, pointIndex, b){
                    for(var i=0, il=charts.length; i < il; i++){
                        var chart = charts[i];
                        try {
                            chart.highlightPoint(serieIndex, pointIndex, b);
                        } catch(e){}
                    }
                }

                if(useInteractiveGuideline){
                    interactiveLayer.dispatch.on('elementMousemove', function(e) {
                        clearHighlights();
                        var singlePoint, pointIndex, pointXLocation, allData = [];
                        data
                            .filter(function(series, i) {
                                series.seriesIndex = i;
                                return !series.disabled;
                            })
                            .forEach(function(series,i) {
                                var extent = x.domain();
                                var currentValues = series.values.filter(function(d,i) {
                                    return chart.x()(d,i) >= extent[0] && chart.x()(d,i) <= extent[1];
                                });

                                pointIndex = nv.interactiveBisect(currentValues, e.pointXValue, chart.x());
                                var point = currentValues[pointIndex];
                                var pointYValue = chart.y()(point, pointIndex);
                                if (pointYValue !== null) {
                                    highlightPoint(i, pointIndex, true);
                                }
                                if (point === undefined) return;
                                if (singlePoint === undefined) singlePoint = point;
                                if (pointXLocation === undefined) pointXLocation = xScale(chart.x()(point,pointIndex));
                                allData.push({
                                    key: series.key,
                                    value: pointYValue,
                                    color: color(series,series.seriesIndex),
                                    data: point,
                                    yAxis: series.yAxis == 2 ? yAxis2 : yAxis1
                                });
                            });

                        var defaultValueFormatter = function(d,i) {
                            var yAxis = allData[i].yAxis;
                            return d == null ? "N/A" : yAxis.tickFormat()(d);
                        };

                        interactiveLayer.tooltip
                            .headerFormatter(function(d, i) {
                                return xAxis.tickFormat()(d, i);
                            })
                            .valueFormatter(interactiveLayer.tooltip.valueFormatter() || defaultValueFormatter)
                            .data({
                                value: chart.x()( singlePoint,pointIndex ),
                                index: pointIndex,
                                series: allData
                            })();

                        interactiveLayer.renderGuideLine(pointXLocation);
                    });

                    interactiveLayer.dispatch.on("elementMouseout",function(e) {
                        clearHighlights();
                    });
                } else {
                    lines1.dispatch.on('elementMouseover.tooltip', mouseover_line);
                    lines2.dispatch.on('elementMouseover.tooltip', mouseover_line);
                    lines1.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });
                    lines2.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });

                    scatters1.dispatch.on('elementMouseover.tooltip', mouseover_scatter);
                    scatters2.dispatch.on('elementMouseover.tooltip', mouseover_scatter);
                    scatters1.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });
                    scatters2.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });

                    stack1.dispatch.on('elementMouseover.tooltip', mouseover_stack);
                    stack2.dispatch.on('elementMouseover.tooltip', mouseover_stack);
                    stack1.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });
                    stack2.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true)
                    });

                    bars1.dispatch.on('elementMouseover.tooltip', mouseover_bar);
                    bars2.dispatch.on('elementMouseover.tooltip', mouseover_bar);

                    bars1.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true);
                    });
                    bars2.dispatch.on('elementMouseout.tooltip', function(evt) {
                        tooltip.hidden(true);
                    });
                    bars1.dispatch.on('elementMousemove.tooltip', function(evt) {
                        tooltip();
                    });
                    bars2.dispatch.on('elementMousemove.tooltip', function(evt) {
                        tooltip();
                    });
                }
            });

            return chart;
        }

        //============================================================
        // Global getters and setters
        //------------------------------------------------------------

        chart.dispatch = dispatch;
        chart.legend = legend;
        chart.lines1 = lines1;
        chart.lines2 = lines2;
        chart.scatters1 = scatters1;
        chart.scatters2 = scatters2;
        chart.bars1 = bars1;
        chart.bars2 = bars2;
        chart.stack1 = stack1;
        chart.stack2 = stack2;
        chart.xAxis = xAxis;
        chart.yAxis1 = yAxis1;
        chart.yAxis2 = yAxis2;
        chart.tooltip = tooltip;
        chart.interactiveLayer = interactiveLayer;

        chart.options = nv.utils.optionsFunc.bind(chart);

        chart._options = Object.create({}, {
            // simple options, just get/set the necessary values
            width:      {get: function(){return width;}, set: function(_){width=_;}},
            height:     {get: function(){return height;}, set: function(_){height=_;}},
            showLegend: {get: function(){return showLegend;}, set: function(_){showLegend=_;}},
            yDomain1:      {get: function(){return yDomain1;}, set: function(_){yDomain1=_;}},
            yDomain2:    {get: function(){return yDomain2;}, set: function(_){yDomain2=_;}},
            noData:    {get: function(){return noData;}, set: function(_){noData=_;}},
            interpolate:    {get: function(){return interpolate;}, set: function(_){interpolate=_;}},
            legendRightAxisHint:    {get: function(){return legendRightAxisHint;}, set: function(_){legendRightAxisHint=_;}},

            // options that require extra logic in the setter
            margin: {get: function(){return margin;}, set: function(_){
                if (_.top !== undefined) {
                    margin.top = _.top;
                    marginTop = _.top;
                }
                margin.right  = _.right  !== undefined ? _.right  : margin.right;
                margin.bottom = _.bottom !== undefined ? _.bottom : margin.bottom;
                margin.left   = _.left   !== undefined ? _.left   : margin.left;
            }},
            color:  {get: function(){return color;}, set: function(_){
                color = nv.utils.getColor(_);
            }},
            x: {get: function(){return getX;}, set: function(_){
                getX = _;
                lines1.x(_);
                lines2.x(_);
                scatters1.x(_);
                scatters2.x(_);
                bars1.x(_);
                bars2.x(_);
                stack1.x(_);
                stack2.x(_);
            }},
            y: {get: function(){return getY;}, set: function(_){
                getY = _;
                lines1.y(_);
                lines2.y(_);
                scatters1.y(_);
                scatters2.y(_);
                stack1.y(_);
                stack2.y(_);
                bars1.y(_);
                bars2.y(_);
            }},
            useVoronoi: {get: function(){return useVoronoi;}, set: function(_){
                useVoronoi=_;
                lines1.useVoronoi(_);
                lines2.useVoronoi(_);
                stack1.useVoronoi(_);
                stack2.useVoronoi(_);
            }},

            useInteractiveGuideline: {get: function(){return useInteractiveGuideline;}, set: function(_){
                useInteractiveGuideline = _;
                if (useInteractiveGuideline) {
                    lines1.interactive(false);
                    lines1.useVoronoi(false);
                    lines2.interactive(false);
                    lines2.useVoronoi(false);
                    stack1.interactive(false);
                    stack1.useVoronoi(false);
                    stack2.interactive(false);
                    stack2.useVoronoi(false);
                    scatters1.interactive(false);
                    scatters2.interactive(false);
                }
            }},

            duration: {get: function(){return duration;}, set: function(_) {
                duration = _;
                [lines1, lines2, stack1, stack2, scatters1, scatters2, xAxis, yAxis1, yAxis2].forEach(function(model){
                    model.duration(duration);
                });
            }}
        });

        nv.utils.initOptions(chart);

        return chart;
    };

    nv.models.stackedArea = function() {
        "use strict";

        //============================================================
        // Public Variables with Default Settings
        //------------------------------------------------------------

        var margin = {top: 0, right: 0, bottom: 0, left: 0}
            , width = 960
            , height = 500
            , color = nv.utils.defaultColor() // a function that computes the color
            , id = Math.floor(Math.random() * 100000) //Create semi-unique ID incase user doesn't selet one
            , container = null
            , getX = function(d) { return d.x } // accessor to get the x value from a data point
            , getY = function(d) { return d.y } // accessor to get the y value from a data point
            , defined = function(d,i) { return !isNaN(getY(d,i)) && getY(d,i) !== null } // allows a line to be not continuous when it is not defined
            , style = 'stack'
            , offset = 'zero'
            , order = 'default'
            , interpolate = 'linear'  // controls the line interpolation
            , clipEdge = false // if true, masks lines within x and y scale
            , x //can be accessed via chart.xScale()
            , y //can be accessed via chart.yScale()
            , scatter = nv.models.scatter()
            , duration = 250
            , dispatch =  d3.dispatch('areaClick', 'areaMouseover', 'areaMouseout','renderEnd', 'elementClick', 'elementMouseover', 'elementMouseout')
        ;

        scatter
            .pointSize(2.2) // default size
            .pointDomain([2.2, 2.2]) // all the same size by default
        ;

        /************************************
         * offset:
         *   'wiggle' (stream)
         *   'zero' (stacked)
         *   'expand' (normalize to 100%)
         *   'silhouette' (simple centered)
         *
         * order:
         *   'inside-out' (stream)
         *   'default' (input order)
         ************************************/

        var renderWatch = nv.utils.renderWatch(dispatch, duration);

        function chart(selection) {
            renderWatch.reset();
            renderWatch.models(scatter);
            selection.each(function(data) {
                var availableWidth = width - margin.left - margin.right,
                    availableHeight = height - margin.top - margin.bottom;

                container = d3.select(this);
                nv.utils.initSVG(container);

                // Setup Scales
                x = scatter.xScale();
                y = scatter.yScale();

                var dataRaw = data;
                // Injecting point index into each point because d3.layout.stack().out does not give index
                data.forEach(function(aseries, i) {
                    aseries.seriesIndex = i;
                    aseries.values = aseries.values.map(function(d, j) {
                        d.index = j;
                        d.seriesIndex = i;
                        return d;
                    });
                });

                var dataFiltered = data.filter(function(series) {
                    return !series.disabled;
                });

                data = d3.layout.stack()
                    .order(order)
                    .offset(offset)
                    .values(function(d) { return d.values })  //TODO: make values customizeable in EVERY model in this fashion
                    .x(getX)
                    .y(getY)
                    .out(function(d, y0, y) {
                        d.display = {
                            y: y,
                            y0: y0
                        };
                    })
                    (dataFiltered);

                // Setup containers and skeleton of chart
                var wrap = container.selectAll('g.nv-wrap.nv-stackedarea').data([data]);
                var wrapEnter = wrap.enter().append('g').attr('class', 'nvd3 nv-wrap nv-stackedarea');
                var defsEnter = wrapEnter.append('defs');
                var gEnter = wrapEnter.append('g');
                var g = wrap.select('g');

                gEnter.append('g').attr('class', 'nv-areaWrap');
                gEnter.append('g').attr('class', 'nv-scatterWrap');

                wrap.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

                // If the user has not specified forceY, make sure 0 is included in the domain
                // Otherwise, use user-specified values for forceY
                if (scatter.forceY().length == 0) {
                    scatter.forceY().push(0);
                }

                scatter
                    .width(availableWidth)
                    .height(availableHeight)
                    .x(getX)
                    .y(function(d) {
                        if (d.display !== undefined) { return d.display.y + d.display.y0; }
                    })
                    .color(data.map(function(d,i) {
                        d.color = d.color || color(d, d.seriesIndex);
                        return d.color;
                    }));

                var scatterWrap = g.select('.nv-scatterWrap')
                    .datum(data);

                scatterWrap.call(scatter);

                defsEnter.append('clipPath')
                    .attr('id', 'nv-edge-clip-' + id)
                    .append('rect');

                wrap.select('#nv-edge-clip-' + id + ' rect')
                    .attr('width', availableWidth)
                    .attr('height', availableHeight);

                g.attr('clip-path', clipEdge ? 'url(#nv-edge-clip-' + id + ')' : '');

                var area = d3.svg.area()
                    .defined(defined)
                    .x(function(d,i)  { return x(getX(d,i)) })
                    .y0(function(d) {
                        return y(d.display.y0)
                    })
                    .y1(function(d) {
                        return y(d.display.y + d.display.y0)
                    })
                    .interpolate(interpolate);

                var zeroArea = d3.svg.area()
                    .defined(defined)
                    .x(function(d,i)  { return x(getX(d,i)) })
                    .y0(function(d) { return y(d.display.y0) })
                    .y1(function(d) { return y(d.display.y0) });

                var path = g.select('.nv-areaWrap').selectAll('path.nv-area')
                    .data(function(d) { return d });

                path.enter().append('path').attr('class', function(d,i) { return 'nv-area nv-area-' + i })
                    .attr('d', function(d,i){
                        return zeroArea(d.values, d.seriesIndex);
                    })
                    .on('mouseover', function(d,i) {
                        d3.select(this).classed('hover', true);
                        dispatch.areaMouseover({
                            point: d,
                            series: d.key,
                            pos: [d3.event.pageX, d3.event.pageY],
                            seriesIndex: d.seriesIndex
                        });
                    })
                    .on('mouseout', function(d,i) {
                        d3.select(this).classed('hover', false);
                        dispatch.areaMouseout({
                            point: d,
                            series: d.key,
                            pos: [d3.event.pageX, d3.event.pageY],
                            seriesIndex: d.seriesIndex
                        });
                    })
                    .on('click', function(d,i) {
                        d3.select(this).classed('hover', false);
                        dispatch.areaClick({
                            point: d,
                            series: d.key,
                            pos: [d3.event.pageX, d3.event.pageY],
                            seriesIndex: d.seriesIndex
                        });
                    });

                path.exit().remove();
                path.style('fill', function(d,i){
                    return d.color || color(d, d.seriesIndex)
                })
                    .style('stroke', function(d,i){ return d.color || color(d, d.seriesIndex) });
                path.watchTransition(renderWatch,'stackedArea path')
                    .attr('d', function(d,i) {
                        return area(d.values,i)
                    });

                //============================================================
                // Event Handling/Dispatching (in chart's scope)
                //------------------------------------------------------------

                scatter.dispatch.on('elementMouseover.area', function(e) {
                    g.select('.nv-chart-' + id + ' .nv-area-' + e.seriesIndex).classed('hover', true);
                });
                scatter.dispatch.on('elementMouseout.area', function(e) {
                    g.select('.nv-chart-' + id + ' .nv-area-' + e.seriesIndex).classed('hover', false);
                });

                //Special offset functions
                chart.d3_stackedOffset_stackPercent = function(stackData) {
                    var n = stackData.length,    //How many series
                        m = stackData[0].length,     //how many points per series
                        i,
                        j,
                        o,
                        y0 = [];

                    for (j = 0; j < m; ++j) { //Looping through all points
                        for (i = 0, o = 0; i < dataRaw.length; i++) { //looping through all series
                            o += getY(dataRaw[i].values[j]); //total y value of all series at a certian point in time.
                        }

                        if (o) for (i = 0; i < n; i++) { //(total y value of all series at point in time i) != 0
                            stackData[i][j][1] /= o;
                        } else { //(total y value of all series at point in time i) == 0
                            for (i = 0; i < n; i++) {
                                stackData[i][j][1] = 0;
                            }
                        }
                    }
                    for (j = 0; j < m; ++j) y0[j] = 0;
                    return y0;
                };

            });

            renderWatch.renderEnd('stackedArea immediate');
            return chart;
        }

        //============================================================
        // Global getters and setters
        //------------------------------------------------------------

        chart.dispatch = dispatch;
        chart.scatter = scatter;

        scatter.dispatch.on('elementClick', function(){ dispatch.elementClick.apply(this, arguments); });
        scatter.dispatch.on('elementMouseover', function(){ dispatch.elementMouseover.apply(this, arguments); });
        scatter.dispatch.on('elementMouseout', function(){ dispatch.elementMouseout.apply(this, arguments); });

        chart.interpolate = function(_) {
            if (!arguments.length) return interpolate;
            interpolate = _;
            return chart;
        };

        chart.duration = function(_) {
            if (!arguments.length) return duration;
            duration = _;
            renderWatch.reset(duration);
            scatter.duration(duration);
            return chart;
        };

        chart.dispatch = dispatch;
        chart.scatter = scatter;
        chart.options = nv.utils.optionsFunc.bind(chart);

        chart._options = Object.create({}, {
            // simple options, just get/set the necessary values
            width:      {get: function(){return width;}, set: function(_){width=_;}},
            height:     {get: function(){return height;}, set: function(_){height=_;}},
            defined: {get: function(){return defined;}, set: function(_){defined=_;}},
            clipEdge: {get: function(){return clipEdge;}, set: function(_){clipEdge=_;}},
            offset:      {get: function(){return offset;}, set: function(_){offset=_;}},
            order:    {get: function(){return order;}, set: function(_){order=_;}},
            interpolate:    {get: function(){return interpolate;}, set: function(_){interpolate=_;}},

            // simple functor options
            x:     {get: function(){return getX;}, set: function(_){getX = d3.functor(_);}},
            y:     {get: function(){return getY;}, set: function(_){getY = d3.functor(_);}},

            // options that require extra logic in the setter
            margin: {get: function(){return margin;}, set: function(_){
                margin.top    = _.top    !== undefined ? _.top    : margin.top;
                margin.right  = _.right  !== undefined ? _.right  : margin.right;
                margin.bottom = _.bottom !== undefined ? _.bottom : margin.bottom;
                margin.left   = _.left   !== undefined ? _.left   : margin.left;
            }},
            color:  {get: function(){return color;}, set: function(_){
                color = nv.utils.getColor(_);
            }},
            style: {get: function(){return style;}, set: function(_){
                style = _;
                switch (style) {
                    case 'stack':
                        chart.offset('zero');
                        chart.order('default');
                        break;
                    case 'stream':
                        chart.offset('wiggle');
                        chart.order('inside-out');
                        break;
                    case 'stream-center':
                        chart.offset('silhouette');
                        chart.order('inside-out');
                        break;
                    case 'expand':
                        chart.offset('expand');
                        chart.order('default');
                        break;
                    case 'stack_percent':
                        chart.offset(chart.d3_stackedOffset_stackPercent);
                        chart.order('default');
                        break;
                }
            }},
            duration: {get: function(){return duration;}, set: function(_){
                duration = _;
                renderWatch.reset(duration);
                scatter.duration(duration);
            }}
        });

        nv.utils.inheritOptions(chart, scatter);
        nv.utils.initOptions(chart);

        return chart;
    };


});
