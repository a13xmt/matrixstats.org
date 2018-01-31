function InitScrollWidget() {
  wrappers = document.querySelectorAll('.scroll-wrapper');
  wrappers.forEach(function(e){
	  scroll = new IScroll(e, {
		  scrollX: true,
		  scrollY: false,
		  momentum: false,
		  snap: true,
		  snapSpeed: 400,
		  keyBindings: true,
      mouseWheel: true,
	  });
  })
}

document.addEventListener('touchmove', function (e) { e.preventDefault(); }, isPassive() ? {
	capture: false,
	passive: false
} : false);
