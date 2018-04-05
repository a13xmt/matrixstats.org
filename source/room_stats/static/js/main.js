function search_by_term(){
  var target = document.getElementById('search_term')
  window.location = "/rooms/search/" + target.value
}

function search_text_changed(e){
  if (e.keyCode == 13){
    search_by_term();
    return false;
  }
}

$(".room-container").each(function(){
  $(this).hover(
    function(){
      var el = $(this).find('.room-description')
      var curHeight = el.height()
      var autoHeight = el.css('height', 'initial').height()
      if (autoHeight > 56){
        el.height(curHeight).animate({height: autoHeight}, 300)
      } else {
        var curHeight = el.height(56)
      }
    },
    function(){
      var el = $(this).find('.room-description')
      el.animate({height: 56}, 300)
    }
  );
})

/*
 *
 * Copy room id / Open room in client
 *
 */

function copy_to_clipboard(text){
  var $temp = $("<input>");
  $("body").append($temp);
  $temp.val(text).select();
  document.execCommand("copy");
  $temp.remove();
}

function copy_room_id(element){
  text = $(element).attr('data-id')
  copy_to_clipboard(text)
  toastr.info("Room id was copied to clipboard", "", {timeOut: 2000})
}

/* toggle submenu on click */
$('#room-details-submenu').click(function(){
  $('.room-details-subitem').slideToggle();
})

/* copy join command on click */
$(".room-details-subitem").click(function(event){
  $('.room-details-subitem').slideToggle();
  if ($(event.target).attr('href') != "#") {
    return
  }
  text = "/join " + $('#room-details-submenu').attr('data-alias')
  copy_to_clipboard(text)
  toastr.info("Command was copied to clipboard", "", {timeOut: 2000})
})

$('.room-details-subitem').hide();

function open_modal(){
  $('.modal').fadeIn(300)
}

$('.modal').click(function(e){
  if (e.target == this){
    $('.modal').fadeOut(300)
  }
});

function promotion_success(data){
  grecaptcha.reset();
  var premoderation = data['premoderation']
  var success = data['success']

  if (success && premoderation){
    $('.modal-content').html('<div class="success">Thank you for submission. The room would be reviewed and added to catalog soon.</span>')
  }
  else if(success){
    $('.modal-content').html('<div class="success">Thank you for submission. The room was successfully added to catalog.</span>')
  }
  else if(data['message'] == 'ALREADY_PROMOTED'){
    $('.modal-content').html('<div class="success">Thank you for submission. However, this room was already promoted.</span>')
  }
}

function promotion_error(data){
  $('.modal-content').append('<div class="error">An error occured. Please, try again.</span>')
}

function reSubmit(response){
  $.post({
    url: '/promote/',
    data: $('#promote-form').serialize(),
    success: promotion_success,
    error: promotion_error
  })
}

/*
 *
 * Endless scroll for room list
 *
 */

if($('.rlist-infinite').length){
  $('.rlist-infinite').infiniteScroll({
    path: '.pagination__next',
    append: '.rlist-item',
    history: 'replace',
    prefill: true
  });
  $('.rlist-infinite').on('append.infiniteScroll', function(event, response, path, items){
    var current = $('.pagination__current').text()
    $('.pagination__current').text(parseInt(current) + 1)
  })
};


/*
 *
 * Room members statistics graph
 *
 */

function display_members_graph(data){
  data = data['result']

  var svg = dimple.newSvg('.room-graph', '100%', 400);
  var chart = new dimple.chart(svg, data);
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
}

if($('.room-graph').length){
  $.ajax({
    url: '/stats/' + $('.room-graph').attr('data-room-id'),
    success: display_members_graph,
    error: function(error,text){ console.log(error,text)}
  })
};
