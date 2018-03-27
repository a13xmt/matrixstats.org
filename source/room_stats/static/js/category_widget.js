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

function set_room_categories(room_id, categories_ids){
  $.ajax({
    type: "POST",
    url: "/admin/room/" + room_id + "/setcategories/",
    beforeSend: function(xhr, settings) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    },
    data: JSON.stringify(categories_ids),
    success: function(){
      toastr.success('Category changed')
    },
    error: function(e, status, error){
      toastr.error(status, error)
    }
  });
}


$(document).ready(function(){
  $(".categories-multiselect").multiselect({
    header: false,
    selectedList: 10,
    buttonWidth: 400,
    click: function(e, ui){
      $(this).data('changed', true)
    },
    close: function(){
      if ($(this).data('changed')){
        room_id = $(this).prop('id')
        checked = $(this).multiselect('getChecked')
        categories_ids = []
        for(var i=0; i < checked.length; i++){
          categories_ids.push(checked[i].value)
        }
        set_room_categories(room_id, categories_ids)
      }
    }
  });
});
