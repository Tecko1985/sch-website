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

  // ---------- Galerie: Raster im Reiter, Großansicht über den ganzen Bildschirm ----------
  // Pfeile, Bildleiste unten, Zoom, Wischen auf dem Handy, Tastatur (← → Esc).
  var bilder = Array.prototype.slice.call(seite.querySelectorAll('.sb-galerie button'));
  if (!bilder.length) return;
  var fenster = document.createElement('dialog');
  fenster.className = 'sb-bildfenster';
  fenster.setAttribute('aria-label', 'Bildergalerie');
  fenster.innerHTML =
    '<div class="sb-bf-kopf"><span class="sb-bf-zahl" aria-live="polite"></span><div>' +
    '<button type="button" class="sb-bf-zoom" aria-label="Bild vergrößern" aria-pressed="false"></button>' +
    '<button type="button" class="sb-bf-zu" aria-label="Galerie schließen"></button></div></div>' +
    '<div class="sb-bf-buehne"><figure><img alt=""><figcaption>Foto: SCH</figcaption></figure></div>' +
    '<button type="button" class="sb-bf-pfeil sb-bf-zurueck" aria-label="Vorheriges Bild"></button>' +
    '<button type="button" class="sb-bf-pfeil sb-bf-weiter" aria-label="Nächstes Bild"></button>' +
    '<div class="sb-bf-leiste"></div>';
  document.body.appendChild(fenster);
  var gross = fenster.querySelector('.sb-bf-buehne img');
  var buehne = fenster.querySelector('.sb-bf-buehne');
  var zoom = fenster.querySelector('.sb-bf-zoom');
  var leiste = fenster.querySelector('.sb-bf-leiste');
  bilder.forEach(function (b, i) {
    var k = document.createElement('button');
    k.type = 'button';
    k.setAttribute('aria-label', 'Bild ' + (i + 1));
    var mini = document.createElement('img');
    mini.src = b.querySelector('img').src; mini.alt = '';
    k.appendChild(mini);
    k.addEventListener('click', function () { oeffne(i); });
    leiste.appendChild(k);
  });
  var nr = 0;
  function zoomen(an) {
    fenster.classList.toggle('sb-bf-gezoomt', an);
    zoom.setAttribute('aria-pressed', an ? 'true' : 'false');
    zoom.setAttribute('aria-label', an ? 'Bild verkleinern' : 'Bild vergrößern');
  }
  function oeffne(i) {
    nr = (i + bilder.length) % bilder.length;
    var img = bilder[nr].querySelector('img');
    zoomen(false);
    gross.src = bilder[nr].dataset.gross || img.src;
    gross.alt = img.alt;
    fenster.querySelector('.sb-bf-zahl').textContent = (nr + 1) + ' / ' + bilder.length;
    Array.prototype.forEach.call(leiste.children, function (k, j) {
      k.classList.toggle('aktiv', j === nr);
      if (j === nr) k.setAttribute('aria-current', 'true'); else k.removeAttribute('aria-current');
    });
    var aktiv = leiste.children[nr];
    leiste.scrollTo({ left: aktiv.offsetLeft - (leiste.clientWidth - aktiv.offsetWidth) / 2, behavior: 'smooth' });
    if (!fenster.open) {
      fenster.showModal();
      document.documentElement.classList.add('sb-bf-offen');
    }
  }
  bilder.forEach(function (b, i) { b.addEventListener('click', function () { oeffne(i); }); });
  fenster.querySelector('.sb-bf-zurueck').addEventListener('click', function () { oeffne(nr - 1); });
  fenster.querySelector('.sb-bf-weiter').addEventListener('click', function () { oeffne(nr + 1); });
  fenster.querySelector('.sb-bf-zu').addEventListener('click', function () { fenster.close(); });
  zoom.addEventListener('click', function () { zoomen(!fenster.classList.contains('sb-bf-gezoomt')); });
  gross.addEventListener('click', function () { zoomen(!fenster.classList.contains('sb-bf-gezoomt')); });
  buehne.addEventListener('click', function (e) { if (e.target === buehne) fenster.close(); });
  fenster.addEventListener('close', function () {
    document.documentElement.classList.remove('sb-bf-offen');
    zoomen(false);
    bilder[nr].focus();
  });
  fenster.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); oeffne(nr + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); oeffne(nr - 1); }
  });
  // Wischen (nur ohne Zoom)
  var startX = null;
  buehne.addEventListener('touchstart', function (e) { startX = e.touches.length === 1 ? e.touches[0].clientX : null; }, { passive: true });
  buehne.addEventListener('touchend', function (e) {
    if (startX === null || fenster.classList.contains('sb-bf-gezoomt')) return;
    var dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 50) oeffne(nr + (dx < 0 ? 1 : -1));
    startX = null;
  });
})();
