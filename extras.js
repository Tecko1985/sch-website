// Sanftes Einblenden beim Scrollen.
(function () {
  // ---------- Einblenden beim Scrollen ----------
  var ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (ruhig || !('IntersectionObserver' in window)) return;
  var ziele = document.querySelectorAll('.sch-sectionhead, .sch-morecard, .sch-socialcard, .club, .lower>div, .nl-innen, .partners>h2');
  if (!ziele.length) return;
  document.documentElement.classList.add('sch-reveal-on');
  var io = new IntersectionObserver(function (eintraege) {
    eintraege.forEach(function (e) {
      if (!e.isIntersecting) return;
      var el = e.target;
      el.classList.add('is-visible');
      io.unobserve(el);
      // Nach dem Einblenden aufräumen, damit Hover-Effekte wieder ihr eigenes Tempo haben.
      setTimeout(function () { el.classList.remove('sch-reveal', 'is-visible'); el.style.transitionDelay = ''; }, 900);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  ziele.forEach(function (el, i) {
    // Was beim Laden schon sichtbar ist, nicht verstecken.
    if (el.getBoundingClientRect().top < window.innerHeight) return;
    el.classList.add('sch-reveal');
    if (el.classList.contains('sch-morecard')) el.style.transitionDelay = (i % 3) * 70 + 'ms';
    io.observe(el);
  });
})();
