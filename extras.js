// Nächstes Spiel mit Countdown und sanftes Einblenden beim Scrollen.
(function () {
  // ---------- Nächstes Spiel ----------
  var box = document.querySelector('[data-next-game]');
  if (box) {
    var data = [];
    try { data = JSON.parse(box.querySelector('[data-ng-fixtures]').textContent); } catch (e) {}
    var now = Date.now();
    // Ein Spiel gilt bis 2 Stunden nach Anpfiff als „nächstes Spiel“.
    var next = data.find(function (f) { return new Date(f[0]).getTime() + 2 * 3600e3 > now; });
    if (!next) {
      box.closest('.sch-matchday').classList.add('ohne-naechstes');
      box.hidden = true;
    } else {
      var kick = new Date(next[0]);
      var home = next[2] === 'H';
      var sch = '<img src="assets/logo.png" alt="" width="827" height="945"><b>1. SC 1911 Heiligenstadt</b>';
      var opp = '<span class="sch-teammark" aria-hidden="true">' + next[4] + '</span><b>' + next[3] + '</b>';
      box.querySelector('[data-ng-home]').innerHTML = home ? sch : opp;
      box.querySelector('[data-ng-away]').innerHTML = home ? opp : sch;
      box.querySelector('[data-ng-comp]').textContent = next[1].toUpperCase();
      box.querySelector('[data-ng-venue]').textContent = next[5];
      var t = box.querySelector('[data-ng-time]');
      t.setAttribute('datetime', next[0]);
      var tag = kick.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Europe/Berlin' });
      var uhr = kick.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Berlin' });
      t.textContent = tag + ' · ' + uhr + ' Uhr';

      var cd = box.querySelector('[data-ng-countdown]');
      var tagNr = function (d) { return Math.floor(new Date(d.toLocaleString('en-US', { timeZone: 'Europe/Berlin' })).setHours(0, 0, 0, 0) / 864e5); };
      var diffTage = tagNr(kick) - tagNr(new Date());
      if (kick.getTime() <= now) cd.textContent = 'Läuft gerade';
      else if (diffTage === 0) cd.textContent = 'Heute · ' + uhr + ' Uhr';
      else if (diffTage === 1) cd.textContent = 'Morgen';
      else cd.textContent = 'Noch ' + diffTage + ' Tage';
    }
  }

  // ---------- Einblenden beim Scrollen ----------
  var ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (ruhig || !('IntersectionObserver' in window)) return;
  var ziele = document.querySelectorAll('.sch-matchday>*, .sch-sectionhead, .sch-morecard, .sch-socialcard, .club, .lower>div, .nl-innen, .partners>h2');
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
