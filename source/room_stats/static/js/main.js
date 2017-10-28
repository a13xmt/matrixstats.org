function search_by_term(){
  var target = document.getElementById('search_term')
  window.location = "/rooms/search/" + target.value
}
