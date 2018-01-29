console.log("imported")


function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

var csrftoken = getCookie('csrftoken');

function change_room_category(room_id, category_id){
  $.ajax({
    type: "POST",
    url: "/admin/room/" + room_id + "/setcategory/" + category_id,
    beforeSend: function(xhr, settings) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    },
    success: function(){
      toastr.success('Category changed')
    },
  });
}
$('document').ready(function(){
  toastr.options.timeOut = 2000;
  $('.category_widget').on('change', function(){
    room_id = $(this).prop('id')
    category_id = this.value
    change_room_category(room_id, category_id)
  })
});
