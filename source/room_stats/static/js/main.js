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
  });
};
