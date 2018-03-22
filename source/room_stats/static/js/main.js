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

function copy_room_id(element){
  var $temp = $("<input>");
  $("body").append($temp);
  $temp.val($(element).attr('data-id')).select();
  document.execCommand("copy");
  $temp.remove();
}
