// Menü, nächstes Spiel im Ticket, News-Schiene, vergangene Termine ausblenden.
(function () {
  var tz = 'Europe/Berlin';
  var jetzt = Date.now();
  var tagNummer = function (d) { return Math.floor(new Date(d.toLocaleString('en-US', { timeZone: tz })).setHours(0, 0, 0, 0) / 864e5); };

  // ---------- Menü ----------
  var knopf = document.querySelector('.menu');
  var nav = document.getElementById('nav');
  if (knopf && nav) {
    var zu = function () { nav.classList.remove('offen'); knopf.setAttribute('aria-expanded', 'false'); knopf.textContent = 'Menü'; };
    knopf.addEventListener('click', function () {
      var offen = nav.classList.toggle('offen');
      knopf.setAttribute('aria-expanded', String(offen));
      knopf.textContent = offen ? 'Schließen' : 'Menü';
    });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) zu(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('offen')) { zu(); knopf.focus(); } });
  }

  // ---------- Ticket: nächstes Spiel ----------
  var ticket = document.querySelector('[data-naechstes]');
  if (ticket) {
    var spiele = [];
    try { spiele = JSON.parse(ticket.querySelector('[data-n-spiele]').textContent); } catch (e) {}
    // Ein Spiel bleibt bis zwei Stunden nach Anpfiff das nächste.
    var s = spiele.find(function (x) { return new Date(x[0]).getTime() + 2 * 3600e3 > jetzt; });
    if (!s) { ticket.hidden = true; }
    else {
      var setze = function (sel, text) { var el = ticket.querySelector(sel); if (el) el.textContent = text; };
      var anpfiff = new Date(s[0]);
      var heim = s[2] === 'H';
      setze('[data-n-art]', heim ? 'Nächstes Heimspiel' : 'Nächstes Auswärtsspiel');
      setze('[data-n-mitte]', heim ? 'gegen' : 'zu Gast bei');
      setze('[data-n-b]', s[3]);
      setze('[data-n-ort]', s[4]);
      setze('[data-n-wettbewerb]', s[1]);
      var tag = anpfiff.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: tz });
      var std = anpfiff.toLocaleTimeString('de-DE', { hour: 'numeric', minute: '2-digit', timeZone: tz }).replace(':00', '');
      var zeit = ticket.querySelector('[data-n-zeit]');
      zeit.setAttribute('datetime', s[0]);
      zeit.textContent = tag + ', ' + std + ' Uhr';

      var tage = tagNummer(anpfiff) - tagNummer(new Date());
      if (anpfiff.getTime() <= jetzt) { setze('[data-n-zahl]', 'Live'); setze('[data-n-einheit]', 'läuft'); }
      else if (tage === 0) { setze('[data-n-zahl]', 'Heute'); setze('[data-n-einheit]', std + ' Uhr'); }
      else { setze('[data-n-zahl]', String(tage)); setze('[data-n-einheit]', tage === 1 ? 'Tag' : 'Tage'); }
    }
  }

  // ---------- News-Schiene ----------
  var spur = document.querySelector('[data-schiene-spur]');
  if (spur) {
    var knoepfe = document.querySelectorAll('[data-schiene]');
    var ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var stand = function () {
      knoepfe[0].disabled = spur.scrollLeft < 4;
      knoepfe[1].disabled = spur.scrollLeft + spur.clientWidth >= spur.scrollWidth - 4;
    };
    knoepfe.forEach(function (b) {
      b.addEventListener('click', function () {
        var schritt = spur.firstElementChild.getBoundingClientRect().width + 20;
        spur.scrollBy({ left: schritt * Number(b.dataset.schiene), behavior: ruhig ? 'auto' : 'smooth' });
      });
    });
    spur.addEventListener('scroll', stand, { passive: true });
    window.addEventListener('resize', stand, { passive: true });
    stand();
  }

  // ---------- Vergangene Termine ausblenden ----------
  document.querySelectorAll('[data-demnaechst] li[data-zeit]').forEach(function (li) {
    if (new Date(li.dataset.zeit).getTime() + 2 * 3600e3 < jetzt) li.hidden = true;
  });
})();
