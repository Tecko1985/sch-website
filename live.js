// Live-Ticker im SCH-Design (Daten: FuPa-Liveticker, von .github/workflows/live.yml minütlich als
// ticker.json auf den Branch "live" gelegt). Der Browser fragt nur bei GitHub an, nie bei FuPa.
// Startseite: <div id="sch-live">  ->  Live-Leiste mit Spielstand und Link zum Ticker
// seiten/live.html: <div id="sch-live-seite"> -> kompletter Ticker
(function () {
  var skript = document.currentScript;
  var basis = (skript && skript.getAttribute('data-basis')) || '';
  var leiste = document.getElementById('sch-live');
  var seite = document.getElementById('sch-live-seite');
  if (!leiste && !seite) return;

  var API = 'https://api.github.com/repos/Tecko1985/sch-website/contents/ticker.json?ref=live';
  var ROH = 'https://raw.githubusercontent.com/Tecko1985/sch-website/live/ticker.json';
  var TAKT = 60000;
  var apiGesperrt = false;

  function holen() {
    var roh = function () { return fetch(ROH).then(function (r) { if (!r.ok) throw r.status; return r.json(); }); };
    if (apiGesperrt) return roh();
    return fetch(API, { headers: { Accept: 'application/vnd.github.raw' } }).then(function (r) {
      if (r.status === 404) return null;           // noch nie ein Live-Spiel
      if (!r.ok) { apiGesperrt = true; return roh(); } // z. B. Abruf-Grenze erreicht: Rohdatei (bis 5 Min. alt)
      return r.json();
    }).catch(function () { apiGesperrt = true; return roh().catch(function () { return null; }); });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function uhr(iso) {
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Berlin' });
  }
  function tag(iso) {
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Europe/Berlin' });
  }
  function stand(sp) {
    return sp.tore && sp.tore[0] != null && sp.tore[1] != null ? sp.tore[0] + ':' + sp.tore[1] : '–:–';
  }
  function zustand(sp) {
    if (sp.status === 'live') return '<span class="lv-punkt" aria-hidden="true"></span>Live' + (sp.minute ? ' · ' + esc(sp.minute) + '\'' : '');
    if (sp.status === 'ende') return 'Abpfiff';
    return 'Anpfiff ' + esc(uhr(sp.anstoss)) + ' Uhr';
  }

  // Welche Spiele sind gerade interessant? Live oder bis 60 Min. vor Anpfiff. Nach Abpfiff verschwindet der Ticker.
  function relevant(d) {
    if (!d || !d.spiele) return [];
    var jetzt = Date.now(), stand_ = new Date(d.aktualisiert).getTime();
    return d.spiele.filter(function (sp) {
      var a = new Date(sp.anstoss).getTime();
      if (sp.status === 'live') return jetzt - stand_ < 30 * 60000;
      if (sp.status === 'vor') return a - jetzt < 60 * 60000 && jetzt - a < 150 * 60000;
      return false;
    });
  }
  // Abgepfiffene Spiele von heute (für die Spielkarten, bis die Karten mit dem Ergebnis neu gebaut sind)
  function heuteVorbei(d) {
    if (!d || !d.spiele) return [];
    var heute = new Date().toLocaleDateString('de-DE', { timeZone: 'Europe/Berlin' });
    return d.spiele.filter(function (sp) {
      return sp.status === 'ende' && new Date(sp.anstoss).toLocaleDateString('de-DE', { timeZone: 'Europe/Berlin' }) === heute;
    });
  }

  function wappen(t) {
    return '<img src="' + esc(basis + t.wappen) + '" alt="" width="40" height="40" loading="lazy">';
  }

  // ---------------------------------------------------------------- Startseite
  // Spielkarten unter „Aktuelle Spiele“: Live-Stand und Link zum Ticker an die passende Karte hängen
  var karten = {};
  function karte(slug) {
    if (!(slug in karten)) karten[slug] = document.querySelector('.sch-game[data-spiel="' + slug.replace(/"/g, '') + '"]');
    return karten[slug];
  }
  function zeigeKarten(d) {
    relevant(d).concat(heuteVorbei(d)).forEach(function (sp) {
      var k = karte(sp.slug);
      if (!k) return;
      var ergebnis = k.querySelector('.sch-result'), link = k.querySelector('.sch-matchlink');
      if (!k.dataset.vorher) { k.dataset.vorher = k.getAttribute('href'); k.dataset.vorherText = link ? link.innerHTML : ''; }
      var marke = k.querySelector('.lv-marke');
      if (!marke) {
        marke = document.createElement('span');
        marke.className = 'lv-marke';
        k.insertBefore(marke, k.firstChild);
      }
      k.classList.remove('lv-karte-live', 'lv-karte-vor', 'lv-karte-ende');
      k.classList.add('lv-karte-' + sp.status);
      if (sp.status === 'ende') {
        // Nach Abpfiff: Endstand zeigen, Link wieder wie vorher (Spielbericht bzw. FuPa)
        marke.innerHTML = k.classList.contains('sch-finished') ? '' : 'Abpfiff';
        if (ergebnis) ergebnis.textContent = stand(sp).replace(':', ' : ');
        k.setAttribute('href', k.dataset.vorher);
        if (link) link.innerHTML = k.dataset.vorherText;
        return;
      }
      marke.innerHTML = zustand(sp);
      if (ergebnis && sp.status === 'live') ergebnis.textContent = stand(sp).replace(':', ' : ');
      k.setAttribute('href', basis + 'seiten/live.html#' + sp.slug);
      if (link) link.innerHTML = 'Zum Liveticker <span aria-hidden="true">→</span>';
    });
  }

  function zeigeLeiste(d) {
    zeigeKarten(d);
    var liste = relevant(d);
    if (!liste.length) { leiste.hidden = true; return false; }
    leiste.innerHTML = '<div class="lv-leiste-innen">' + liste.map(function (sp) {
      return '<a class="lv-spiel lv-' + sp.status + '" href="' + basis + 'seiten/live.html#' + esc(sp.slug) + '">' +
        '<span class="lv-zustand">' + zustand(sp) + '</span>' +
        '<span class="lv-wer"><small>' + esc(sp.mannschaft) + '</small>' +
        '<span class="lv-paar">' + wappen(sp.heim) + '<b>' + esc(sp.heim.kurz) + '</b>' +
        '<strong class="lv-stand" aria-live="polite">' + stand(sp) + '</strong>' +
        '<b>' + esc(sp.gast.kurz) + '</b>' + wappen(sp.gast) + '</span></span>' +
        '<span class="lv-mehr">Zum Liveticker <span aria-hidden="true">→</span></span></a>';
    }).join('') + '</div>';
    leiste.hidden = false;
    return liste.some(function (sp) { return sp.status !== 'ende'; });
  }

  // ---------------------------------------------------------------- Live-Seite
  var gewaehlt = decodeURIComponent((location.hash || '').slice(1));
  var ZEICHEN = {
    wechsel: '<span class="sb-wechsel" aria-hidden="true">⇄</span> ',
    karte: '<span class="sb-karte" aria-hidden="true"></span>',
    gelb: '<span class="sb-karte gelb" aria-hidden="true"></span>'
  };
  var KLASSE = { tor: 'tor', pfiff: 'pfiff', wechsel: 'wechsel', karte: 'karte', gelb: 'karte' };

  // Aufstellungen (von FuPa, mit Toren, Karten und Wechseln aus dem Ticker)
  function spielerZeile(x, bank) {
    var zeichen = '';
    if (x.tore) zeichen += '<span class="lv-ball" title="Tor" aria-label="' + x.tore + (x.tore > 1 ? ' Tore' : ' Tor') + '">⚽' +
      (x.tore > 1 ? '<sub>' + x.tore + '</sub>' : '') + '</span>';
    if (x.karte) zeichen += '<span class="sb-karte' + (x.karte === 'gelb' ? ' gelb' : '') + '" aria-label="' +
      ({ gelb: 'Gelbe Karte', gelbrot: 'Gelb-Rote Karte', rot: 'Rote Karte' }[x.karte] || 'Karte') + '"></span>';
    var wechsel = '';
    if (x.ein) wechsel += '<span class="sb-wechsel" aria-label="eingewechselt">⇄</span> ' + esc(x.ein) + '\'';
    if (x.aus) wechsel += (wechsel ? ' · ' : '') + '<span class="lv-raus" aria-label="ausgewechselt">⇄</span> ' + esc(x.aus) + '\'';
    return '<li' + (bank && !x.ein ? ' class="lv-ungenutzt"' : '') + '><span>' +
      (x.nr ? '<i class="lv-nr">' + esc(x.nr) + '</i>' : '') + esc(x.name) +
      (x.kap ? ' <abbr class="lv-zusatz" title="Kapitän">(C)</abbr>' : '') +
      (x.tw ? ' <abbr class="lv-zusatz" title="Torwart">(TW)</abbr>' : '') + zeichen + '</span>' +
      '<small>' + wechsel + '</small></li>';
  }
  function elf(t, s) {
    if (!s || !(s.start || []).length) return '';
    return '<section class="sb-elf"><header>' + wappen(t) + '<h3 class="stitel">' + esc(t.kurz || t.name) + '</h3></header>' +
      '<ol>' + s.start.map(function (x) { return spielerZeile(x, false); }).join('') + '</ol>' +
      ((s.bank || []).length ? '<p class="lv-bank">Auf der Bank</p><ol>' +
        s.bank.map(function (x) { return spielerZeile(x, true); }).join('') + '</ol>' : '') + '</section>';
  }
  function aufstellung(sp) {
    var a = sp.aufstellung;
    if (!a) return '';
    var bloecke = elf(sp.heim, a.heim) + elf(sp.gast, a.gast);
    return bloecke ? '<div class="lv-aufstellung" id="aufstellung"><h2 class="sb-h2 stitel">Aufstellungen</h2>' +
      '<div class="sb-aufstellung">' + bloecke + '</div>' +
      '<p class="sb-hinweis">Aufstellungen von FuPa. Tore, Karten und Wechsel kommen aus dem Liveticker.</p></div>' : '';
  }

  function zeigeSeite(d) {
    var alle = relevant(d);
    if (d && d.spiele) {
      // Ein abgepfiffenes Spiel bleibt erreichbar, wenn jemand direkt darauf verlinkt (z. B. von der Spielkarte)
      alle = alle.concat(d.spiele.filter(function (sp) { return sp.slug === gewaehlt && alle.indexOf(sp) < 0; }));
    }
    if (!alle.length) {
      seite.innerHTML = '<div class="lv-leer"><h2 class="stitel">Gerade läuft kein Spiel mit Liveticker</h2>' +
        '<p>Sobald ein SCH-Spiel bei FuPa live getickert wird, erscheint es hier und auf der Startseite – etwa 45 Minuten vor dem Anpfiff.</p>' +
        '<p><a class="lv-knopf" href="termine.html">Zu den Terminen</a></p></div>';
      return false;
    }
    var sp = alle.filter(function (x) { return x.slug === gewaehlt; })[0] || alle[0];
    var wahl = alle.length > 1 ? '<div class="lv-wahl" role="tablist" aria-label="Spiele">' + alle.map(function (x) {
      return '<a role="tab" aria-selected="' + (x === sp) + '" href="#' + esc(x.slug) + '">' + esc(x.mannschaft) +
        ' <span>' + stand(x) + '</span></a>';
    }).join('') + '</div>' : '';
    var tafel = '<div class="lv-tafel lv-' + sp.status + '">' +
      '<p class="lv-meta">' + esc(sp.mannschaft) + (sp.wettbewerb ? ' · ' + esc(sp.wettbewerb) : '') + ' · ' + esc(tag(sp.anstoss)) + '</p>' +
      '<div class="lv-tafel-paar">' +
      '<div class="lv-team">' + wappen(sp.heim) + '<span>' + esc(sp.heim.name) + '</span></div>' +
      '<div class="lv-mitte"><strong aria-live="polite">' + stand(sp) + '</strong><span class="lv-zustand">' + zustand(sp) + '</span></div>' +
      '<div class="lv-team">' + wappen(sp.gast) + '<span>' + esc(sp.gast.name) + '</span></div>' +
      '</div></div>';
    var li = (sp.ereignisse || []).map(function (e) {
      var kopf = e.kopf ? '<h3 class="stitel">' + (ZEICHEN[e.art] || '') + esc(e.kopf) + '</h3>' : '';
      var text = e.text ? '<p>' + esc(e.text) + '</p>' : '';
      return '<li class="' + (KLASSE[e.art] || '') + '"><span class="sb-minute">' + esc(e.min) + '\'</span><div>' + kopf + text +
        '</div><span class="stand">' + esc(e.stand) + '</span></li>';
    }).join('');
    var kopfzeile = sp.status === 'ende' ? '<b>Abpfiff</b><span>Endstand ' + stand(sp) + '</span>'
      : sp.status === 'live' ? '<b>Liveticker</b><span>' + zustand(sp) + '</span>'
      : '<b>Liveticker</b><span>Anpfiff ' + esc(uhr(sp.anstoss)) + ' Uhr</span>';
    var elfen = aufstellung(sp);
    var sprung = elfen && sp.status !== 'vor' ? '<p class="lv-sprung"><a href="#aufstellung" data-lv-sprung>Zu den Aufstellungen <span aria-hidden="true">↓</span></a></p>' : '';
    // Vor dem Anpfiff ist die Aufstellung das Spannendste: dann steht sie über dem Ticker
    seite.innerHTML = wahl + tafel + (sp.status === 'vor' ? elfen : sprung) +
      '<div class="sb-ticker"><div class="sb-tickerkopf">' + kopfzeile + '</div>' +
      (li ? '<ol class="sb-ereignisse">' + li + '</ol>' : '<p class="lv-noch-nichts">Noch keine Einträge – der Ticker startet in Kürze.</p>') +
      '<p class="sb-quelle">Liveticker von FuPa, aktualisiert ' + esc(uhr(d.aktualisiert)) + ' Uhr. Die Seite lädt sich jede Minute selbst neu. ' +
      '<a href="' + esc(sp.fupa) + '" rel="noopener">Spiel bei FuPa</a></p></div>' +
      (sp.status === 'vor' ? '' : elfen);
    return alle.some(function (x) { return x.status !== 'ende'; });
  }

  var daten = null, zeitgeber = null;
  function runde() {
    holen().then(function (d) {
      daten = d;
      var weiter = seite ? zeigeSeite(d) : zeigeLeiste(d);
      clearTimeout(zeitgeber);
      // Nur weiter abfragen, solange ein Spiel ansteht oder läuft
      if (weiter) zeitgeber = setTimeout(runde, TAKT);
    });
  }
  if (seite) {
    // Der Sprung zur Aufstellung darf den gewählten Spiel-Reiter (#slug) nicht ändern
    seite.addEventListener('click', function (ev) {
      var a = ev.target.closest && ev.target.closest('[data-lv-sprung]');
      if (!a) return;
      ev.preventDefault();
      var ziel = document.getElementById('aufstellung');
      if (ziel) ziel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    window.addEventListener('hashchange', function () {
      gewaehlt = decodeURIComponent(location.hash.slice(1));
      if (daten) zeigeSeite(daten);
    });
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') runde();
  });
  runde();
})();
