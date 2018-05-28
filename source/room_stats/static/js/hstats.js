function fetch_healthmap_data(){
  $.ajax({
    url: '/homeserver/matrix.org/stats/',
    success: handle_healthmap_data,
    error: function(error,text){ console.log(error,text)}
  })
}

function handle_healthmap_data(data, status){
  var dates = Object.keys(data)
  dates.forEach(function(date){
    var id = "healthmap-" + date
    $(".healthmap").append("<div id='" + id + "'></div>")
    render_healthmap(data[date], date, id)
  })
}

function render_healthmap(data, date, id){
  border = 1.25
  cols = 24
  rows = 6
  box_h =16
  box_w =16
  margin_top = 50;
  margin_left = 40;
  height = cols * (box_h + border) + margin_top
  width = rows * (box_w + border) + margin_left

  color_map = [
    "#dd776e", "#dd776e", "#dd776e", "#dd776e",
    "#e2886c", "#f5ce62", "#d4c86a", "#c4c56d",
    "#b0be6e", "#94bd77", "seagreen",
  ]

  heatmap = function(obj){
    r = obj['r']
    if (r == null){ return "#a9a9a9" }
    else { return color_map[
      Math.floor(r / (color_map.length - 1))
    ]}
  }

  xScale = d3.scaleBand()
    .domain(d3.range(0, rows, 1))
    .range([0, (box_w + border) * rows])

  yScale = d3.scaleBand()
    .domain(d3.range(0, cols, 1))
    .range([0, (box_h + border) * cols])

  chart = d3.select("#" + id)
    .append('svg')
    .attr('class', 'chart')
    .attr('width', width)
    .attr('height', height)

  chart.selectAll("rect")
    .data(data)
    .enter().append("rect")
    .attr("width", box_w)
    .attr("height", box_h)
    .attr("fill", heatmap)
    .attr("transform", function(obj, ii){
      dx = xScale(ii % rows)  + margin_left
      dy = yScale(Math.floor(ii / rows)) + margin_top
      return "translate(" + dx + "," + dy + ")"
    })
    .append("svg:title")
    .text(function(obj){
      if (obj['r'] == null){ return "No data" }
      var ratio = Math.round(obj['r']) + "%"
      return ratio + " (successful: " + obj['s'] + ", failed: " + obj['e'] + ")"
    })

  var mFormat = d3.timeFormat("%M")
  var step = Math.floor(60 / rows)
  xAxis = d3.axisTop()
    .scale(xScale)
    .tickSizeOuter(0)
    .tickFormat(function(d) { return mFormat(new Date(1970, 0, 0, 0, step * d + (step/2))) })

  var hFormat = d3.timeFormat("%H")
  yAxis = d3.axisLeft()
    .scale(yScale)
    .tickSizeOuter(0)
    .tickFormat(function(d) { return hFormat(new Date(1970, 0, 0, d, 0)) })

  chart.append("g")
    .attr("class", "y axis")
    .attr("transform", "translate(" + margin_left + "," + margin_top + ")")
    .attr("fill", "#666666")
    .call(yAxis)

  chart.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(" + margin_left + "," + margin_top + ")")
    .attr("fill", "#666666")
    .call(xAxis)

  chart.append("text")
    .attr("font-size", "14")
    .attr("fill", "#333")
    .attr("transform", "translate(" + (margin_left + 18)  + ",25)")
    .text(date)
}


$(document).ready(function(){
  fetch_healthmap_data()
})
