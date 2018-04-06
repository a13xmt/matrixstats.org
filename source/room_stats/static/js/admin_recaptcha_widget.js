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

function upload_captcha_response(server_id, captcha){
  var data = {
    server_id: server_id,
    captcha: captcha
  }
  $.ajax({
    type: "POST",
    contentType: 'application/json; charset=utf-8',
    processData: false,
    data: JSON.stringify(data),
    url: "/admin/update_server_recaptcha/",
    beforeSend: function(xhr, settings) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    },
    success: function(){
      toastr.success('Category changed')
    },
  });
}

function onloadCallback(){
  $(".recaptcha").each(function(){
    var site_key = $(this).data("sitekey")
    var server_id = $(this).data("server-id")
    grecaptcha.render(this, {
      'sitekey': site_key,
      'callback': upload_captcha_response.bind(null, server_id)
    })
  })
}
