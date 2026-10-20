// Menü auf dem Handy, nächstes Spiel im Plakat, vergangene Termine ausblenden.
(function () {
  // ---------- Menü ----------
  var knopf = document.querySelector('.menuknopf');
  var nav = document.getElementById('hauptnav');
  if (knopf && nav) {
    var schliessen = function () { nav.classList.remove('offen'); knopf.setAttribute('aria-expanded', 'false'); knopf.textContent = 'Menü'; };
    knopf.addEventListener('click', function () {
      var offen = nav.classList.toggle('offen');
      knopf.setAttribute('aria-expanded', String(offen));
      knopf.textContent = offen ? 'Schließen' : 'Menü';
    });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) schliessen(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('offen')) { schliessen(); knopf.focus(); } });
  }

  var jetzt = Date.now();
  var tz = 'Europe/Berlin';
  var tagNummer = function (d) { return Math.floor(new Date(d.toLocaleString('en-US', { timeZone: tz })).setHours(0, 0, 0, 0) / 864e5); };

  // ---------- Nächstes Spiel ----------
  var plakat = document.querySelector('[data-naechstes]');
  if (plakat) {
    var spiele = [];
    try { spiele = JSON.parse(plakat.querySelector('[data-n-spiele]').textContent); } catch (e) {}
    // Ein Spiel bleibt bis zwei Stunden nach Anpfiff das „nächste“.
    var s = spiele.find(function (x) { return new Date(x[0]).getTime() + 2 * 3600e3 > jetzt; });
    if (s) {
      var anpfiff = new Date(s[0]);
      var heim = s[2] === 'H';
      var setze = function (sel, text) { var el = plakat.querySelector(sel); if (el) el.textContent = text; };
      setze('[data-n-art]', heim ? 'Nächstes Heimspiel' : 'Nächstes Auswärtsspiel');
      setze('[data-n-erst]', 'SCH');
      setze('[data-n-mitte]', heim ? 'gegen' : 'zu Gast bei');
      setze('[data-n-zweit]', s[3]);
      setze('[data-n-ort]', s[4]);
      setze('[data-n-wettbewerb]', s[1]);
      var tag = anpfiff.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: tz });
      var std = anpfiff.toLocaleTimeString('de-DE', { hour: 'numeric', minute: '2-digit', timeZone: tz }).replace(':00', '');
      var zeit = plakat.querySelector('[data-n-zeit]');
      zeit.setAttribute('datetime', s[0]);
      zeit.textContent = tag + ', ' + std + ' Uhr';

      var tage = tagNummer(anpfiff) - tagNummer(new Date());
      var cd = anpfiff.getTime() <= jetzt ? 'läuft gerade' : tage === 0 ? 'heute' : tage === 1 ? 'morgen' : 'in ' + tage + ' Tagen';
      setze('[data-n-countdown]', cd);
    }
  }

  // ---------- Vergangene Termine ausblenden ----------
  document.querySelectorAll('[data-demnaechst] li[data-zeit]').forEach(function (li) {
    if (new Date(li.dataset.zeit).getTime() + 2 * 3600e3 < jetzt) li.hidden = true;
  });
})();
