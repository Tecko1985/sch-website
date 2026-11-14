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

  // Welche Spiele sind gerade interessant? Live; vor Anpfiff (bis 60 Min. vorher); bis 90 Min. nach Abpfiff.
  function relevant(d) {
    if (!d || !d.spiele) return [];
    var jetzt = Date.now(), stand_ = new Date(d.aktualisiert).getTime();
    return d.spiele.filter(function (sp) {
      var a = new Date(sp.anstoss).getTime();
      if (sp.status === 'live') return jetzt - stand_ < 30 * 60000;
      if (sp.status === 'vor') return a - jetzt < 60 * 60000 && jetzt - a < 150 * 60000;
      return jetzt - stand_ < 90 * 60000;
    });
  }

  function wappen(t) {
    return '<img src="' + esc(basis + t.wappen) + '" alt="" width="40" height="40" loading="lazy">';
  }

  // ---------------------------------------------------------------- Startseite
  function zeigeLeiste(d) {
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

  function zeigeSeite(d) {
    var alle = relevant(d);
    if (!alle.length && d && d.spiele) {
      // Letztes Spiel noch zeigen, wenn jemand über einen Link kommt
      alle = d.spiele.filter(function (sp) { return sp.slug === gewaehlt; });
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
    seite.innerHTML = wahl + tafel +
      '<div class="sb-ticker"><div class="sb-tickerkopf">' + kopfzeile + '</div>' +
      (li ? '<ol class="sb-ereignisse">' + li + '</ol>' : '<p class="lv-noch-nichts">Noch keine Einträge – der Ticker startet in Kürze.</p>') +
      '<p class="sb-quelle">Liveticker von FuPa, aktualisiert ' + esc(uhr(d.aktualisiert)) + ' Uhr. Die Seite lädt sich jede Minute selbst neu. ' +
      '<a href="' + esc(sp.fupa) + '" rel="noopener">Spiel bei FuPa</a></p></div>';
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
