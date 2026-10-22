// Spielbericht: Reiter (mit #adresse), Bildergalerie mit Großansicht, Statistik-Balken.
(function () {
  var seite = document.querySelector('.sb');
  if (!seite) return;
  var reiter = Array.prototype.slice.call(seite.querySelectorAll('[role=tab]'));
  var titel = seite.querySelector('[data-sb-titel]');

  function zeige(tab, fokus, adresse) {
    reiter.forEach(function (t) {
      var an = t === tab;
      t.setAttribute('aria-selected', String(an));
      t.tabIndex = an ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !an;
    });
    if (titel) titel.textContent = tab.textContent;
    if (fokus) tab.focus();
    if (adresse) history.replaceState(null, '', '#' + tab.dataset.name);
    tab.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    if (tab.dataset.name === 'statistiken') balken();
  }

  reiter.forEach(function (tab, i) {
    tab.addEventListener('click', function () {
      zeige(tab, false, true);
      var band = seite.querySelector('.sb-reiter-band');
      if (band.getBoundingClientRect().top < 0) band.scrollIntoView();
    });
    tab.addEventListener('keydown', function (e) {
      var n = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: reiter.length - 1 }[e.key];
      if (n === undefined) return;
      e.preventDefault();
      zeige(reiter[(n + reiter.length) % reiter.length], true, true);
    });
  });
  seite.querySelectorAll('[data-sb-zu]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var t = reiter.filter(function (r) { return r.dataset.name === a.dataset.sbZu; })[0];
      if (!t) return;
      e.preventDefault();
      zeige(t, true, true);
      seite.querySelector('.sb-reiter-band').scrollIntoView();
    });
  });

  function ausAdresse() {
    var name = location.hash.slice(1);
    var t = reiter.filter(function (r) { return r.dataset.name === name; })[0];
    if (t) zeige(t, false, false);
  }
  window.addEventListener('hashchange', ausAdresse);
  ausAdresse();

  // ---------- Statistik-Balken ----------
  function balken() {
    seite.querySelectorAll('.sb-stat').forEach(function (s) {
      var a = parseFloat(s.dataset.a), b = parseFloat(s.dataset.b), max = Math.max(a, b) || 1;
      s.querySelector('.links i').style.width = (a / max * 100) + '%';
      s.querySelector('.rechts i').style.width = (b / max * 100) + '%';
    });
  }

  // ---------- Galerie ----------
  var bilder = Array.prototype.slice.call(seite.querySelectorAll('.sb-galerie button'));
  if (!bilder.length) return;
  var fenster = document.createElement('dialog');
  fenster.className = 'sb-bildfenster';
  fenster.setAttribute('aria-label', 'Bild in groß');
  fenster.innerHTML = '<div class="sb-bildfenster-leiste"><span></span><div>' +
    '<button type="button" data-schritt="-1" aria-label="Vorheriges Bild">←</button>' +
    '<button type="button" data-schritt="1" aria-label="Nächstes Bild">→</button>' +
    '<button type="button" data-zu>Schließen</button></div></div><img alt="">';
  seite.appendChild(fenster);
  var nr = 0;
  function oeffne(i) {
    nr = (i + bilder.length) % bilder.length;
    var img = bilder[nr].querySelector('img');
    var gross = fenster.querySelector('img');
    gross.src = bilder[nr].dataset.gross || img.src;
    gross.alt = img.alt;
    fenster.querySelector('span').textContent = 'Bild ' + (nr + 1) + ' von ' + bilder.length;
    if (!fenster.open) fenster.showModal();
  }
  bilder.forEach(function (b, i) { b.addEventListener('click', function () { oeffne(i); }); });
  fenster.querySelectorAll('[data-schritt]').forEach(function (b) {
    b.addEventListener('click', function () { oeffne(nr + Number(b.dataset.schritt)); });
  });
  fenster.querySelector('[data-zu]').addEventListener('click', function () { fenster.close(); });
  fenster.addEventListener('click', function (e) { if (e.target === fenster) fenster.close(); });
  fenster.addEventListener('close', function () { bilder[nr].focus(); });
  fenster.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') oeffne(nr + 1);
    if (e.key === 'ArrowLeft') oeffne(nr - 1);
  });
})();
