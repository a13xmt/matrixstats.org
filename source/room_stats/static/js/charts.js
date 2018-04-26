function display_members_graph(data){
  data = data['result']
  var svg = dimple.newSvg('.room-members-graph', '100%', 300);
  var chart = new dimple.chart(svg, data);
  svg.append("text")
    .attr("x", chart._xPixels() + chart._widthPixels() / 2)
    .attr("y", chart._yPixels() - 20)
    .style("text-anchor", "middle")
    .style("font-size", "14px")
    .style("color", "#444")
    .text("Members total");
  var x = chart.addTimeAxis('x', 'date', '%Y-%m-%d', '%b, %Y');
  x.title = ""
  x.addOrderRule('Date');
  x.timePeriod = d3.timeMonth;
  x.timeInterval = 1;
  x.floatingBarWidth = 1;
  x.showGridlines = true;
  var y = chart.addMeasureAxis('y', 'members_count');
  y.title = ""
  var s = chart.addSeries(null, dimple.plot.line);
  s.barGap = 0;
  s.getTooltipText = function (e) {
    return [
      (new Date(e.x)).toLocaleDateString("en-us", {year: "numeric", month: "long", day: "numeric"}),
      e.y + " members"
    ];
  };
  chart.draw();
  adjust_colors();
}

function display_room_stats_graph(data){
  var periods = ['d', 'w', 'm']
  var settings = {
    'd': {
      'period': d3.timeDay,
      'ticks': 10,
      'label': 'Daily activity',
      'colors': [
        new dimple.color("#bccad6"),
        new dimple.color("#8d9db6"),
      ]
    },
    'w': {
      'period': d3.timeMonday,
      'ticks': 5,
      'label': 'Weekly activity',
      'colors': [
        new dimple.color("#c0d5d7"),
        new dimple.color("#7fa298"),
      ]
    },
    'm': {
      'period': d3.timeMonth,
      'ticks': 5,
      'label': 'Monthly activity',
      'colors': [
        new dimple.color("#b1cbbb"),
        new dimple.color("#92aaa1"),
      ]
    }
  }

  for (var i = 0; i < 3; i++){
    var period = periods[i]
    var d = data[period]
    var svg = dimple.newSvg('.room-stats-graph-' + period, '100%', 300);
    var chart = new dimple.chart(svg)
    svg.append("text")
      .attr("x", chart._xPixels() + chart._widthPixels() / 2)
      .attr("y", chart._yPixels() - 20)
      .style("text-anchor", "middle")
      .style("font-size", "14px")
      .style("color", "#444")
      .text(settings[period]['label']);
    chart.defaultColors = settings[period]['colors']
    var x = chart.addTimeAxis('x', 'date', '%Y-%m-%d', '%b, %d');
    x.title = ""
    x.addOrderRule('Date');
    x.timePeriod = settings[period]['period'],
    x.timeInterval = 1,
    x.floatingBarWidth = 15;
    x.showGridlines = true;

    var y1 = chart.addMeasureAxis('y', 'value')
    y1.title = ""
    y1.overrideMax = d['ovdmx_messages']
    y1.ticks = settings[period]['ticks']

    var y2 = chart.addMeasureAxis('y', 'value')
    y2.title = ""
    y2.overrideMax = d['ovdmx_senders']
    y2.ticks = settings[period]['ticks']

    var s1 = chart.addSeries('index', dimple.plot.area, [x, y1])
    s1.data = d['messages']
    s1.getTooltipText = function(e){
      return [
        (new Date(e.x)).toLocaleDateString("en-us", {year: "numeric", month: "long", day: "numeric"}),
        e.y + " messages"
      ]
    }

    var s2 = chart.addSeries('index', dimple.plot.area, [x, y2])
    s2.data = d['senders']
    s2.getTooltipText = function(e){
      return [
        (new Date(e.x)).toLocaleDateString("en-us", {year: "numeric", month: "long", day: "numeric"}),
        e.y + " active members"
      ]
    }

    chart.draw();
  }
  adjust_colors();
}

function adjust_colors(){
  d3.selectAll("text").attr("fill", "#444");
  d3.selectAll("path.dimple-custom-axis-line").style("stroke", "#aaa");
  d3.selectAll(".dimple-custom-axis-line").style("stroke", "#aaa");
}


$(document).ready(function(){
  if($('.room-members-graph').length){
    $.ajax({
      url: '/stats/' + $('.room-graphs').attr('data-room-id'),
      success: display_members_graph,
      error: function(error,text){ console.log(error,text)}
    })
  };

  if($('.room-stats-graph-d').length){
    $.ajax({
      url: '/rstats/' + $('.room-graphs').attr('data-room-id'),
      success: display_room_stats_graph,
      error: function(error,text){ console.log(error,text)}
    })
  };
})

