// Besucherzähler (statistik/zaehlen.php): meldet je Seitenaufruf den Pfad, ob man von außen kommt
// (= ein Besuch) und den Namen der Herkunftsseite (z. B. google.com). Keine Cookies, nichts im Browser
// gespeichert, keine Kennung. Wer im Browser „Do Not Track“ oder „Global Privacy Control“ an hat, wird
// nicht gezählt. Nur auf der echten Seite eingebunden (werkzeuge/umzug_schalter.py).
(function () {
  try {
    if (navigator.globalPrivacyControl || navigator.doNotTrack === '1' || navigator.webdriver) return;
    var eigen = location.hostname.replace(/^www\./, '');
    var quelle = '';
    try { quelle = document.referrer ? new URL(document.referrer).hostname : ''; } catch (e) { quelle = ''; }
    var vonAussen = !quelle || quelle.replace(/^www\./, '') !== eigen;
    var daten = new URLSearchParams();
    daten.set('p', location.pathname);
    daten.set('e', vonAussen ? '1' : '0');
    daten.set('q', vonAussen ? quelle : '');
    var ziel = '/statistik/zaehlen.php';
    if (navigator.sendBeacon) navigator.sendBeacon(ziel, daten);
    else fetch(ziel, { method: 'POST', body: daten, keepalive: true, credentials: 'omit' });
  } catch (e) { /* Zählen ist nie wichtiger als die Seite */ }
})();
