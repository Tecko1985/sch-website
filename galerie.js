// Großansicht für Beitragsbilder (normale Beiträge, seiten/beitrag-*.html im neuen Aufbau):
// Klick auf Titelbild, Bild im Text oder Galeriebild öffnet die Großansicht; Pfeile, Wischen und Tastatur
// (←/→/Esc) blättern durch alle Bilder des Beitrags. Bildnachweis aus data-fotograf am Skript.
(function () {
  var skript = document.currentScript;
  var fotograf = (skript && skript.getAttribute('data-fotograf')) || 'SCH';
  var bilder = [].slice.call(document.querySelectorAll('.sp-neu .sp-titelfoto img, .sp-neu .sp-inhalt figure img, .sp-neu .sp-galerie img'))
    .filter(function (b) { return !b.closest('.sp-spieltag') && !/sponsorenleiste|logo/.test(b.getAttribute('src') || ''); });
  if (!bilder.length) return;

  var box = document.createElement('div');
  box.className = 'gl-box';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Bild in Großansicht');
  box.innerHTML = '<button type="button" class="gl-zu" aria-label="Schließen">×</button>' +
    '<button type="button" class="gl-pfeil gl-zurueck" aria-label="Vorheriges Bild"></button>' +
    '<figure class="gl-buehne"><img alt=""><figcaption></figcaption></figure>' +
    '<button type="button" class="gl-pfeil gl-weiter" aria-label="Nächstes Bild"></button>';
  document.body.appendChild(box);
  var img = box.querySelector('img'), text = box.querySelector('figcaption');
  var pos = 0, zuletzt = null;

  function zeige(i) {
    pos = (i + bilder.length) % bilder.length;
    img.src = bilder[pos].currentSrc || bilder[pos].src;
    img.alt = bilder[pos].alt || '';
    text.textContent = (bilder.length > 1 ? (pos + 1) + ' / ' + bilder.length + ' · ' : '') + 'Foto: ' + fotograf;
  }
  function auf(i) {
    zuletzt = document.activeElement;
    zeige(i);
    box.hidden = false;
    document.documentElement.classList.add('gl-offen');
    box.querySelector('.gl-zu').focus();
  }
  function zu() {
    box.hidden = true;
    document.documentElement.classList.remove('gl-offen');
    if (zuletzt && zuletzt.focus) zuletzt.focus();
  }
  bilder.forEach(function (b, i) {
    b.classList.add('gl-klickbar');
    b.setAttribute('tabindex', '0');
    b.setAttribute('role', 'button');
    b.setAttribute('aria-label', 'Bild ' + (i + 1) + ' von ' + bilder.length + ' groß anzeigen');
    b.addEventListener('click', function () { auf(i); });
    b.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); auf(i); } });
  });
  box.querySelector('.gl-zu').addEventListener('click', zu);
  box.querySelector('.gl-zurueck').addEventListener('click', function () { zeige(pos - 1); });
  box.querySelector('.gl-weiter').addEventListener('click', function () { zeige(pos + 1); });
  box.addEventListener('click', function (ev) { if (ev.target === box || ev.target.classList.contains('gl-buehne')) zu(); });
  document.addEventListener('keydown', function (ev) {
    if (box.hidden) return;
    if (ev.key === 'Escape') zu();
    if (ev.key === 'ArrowLeft') zeige(pos - 1);
    if (ev.key === 'ArrowRight') zeige(pos + 1);
    // Fokusfalle (Gesamtprüfung 22.11.2026 WS-3): Tab/Umschalt+Tab bleiben bei den Knöpfen der Großansicht
    if (ev.key === 'Tab') {
      var knoepfe = [].filter.call(box.querySelectorAll('button'), function (k) { return !k.hidden; });
      var i = knoepfe.indexOf(document.activeElement);
      if (ev.shiftKey ? i <= 0 : (i < 0 || i === knoepfe.length - 1)) {
        ev.preventDefault();
        knoepfe[ev.shiftKey ? knoepfe.length - 1 : 0].focus();
      }
    }
  });
  // Wischen auf dem Handy
  var x0 = null;
  box.addEventListener('touchstart', function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function (ev) {
    if (x0 === null) return;
    var dx = ev.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 45) zeige(pos + (dx < 0 ? 1 : -1));
    x0 = null;
  });
  if (bilder.length < 2) box.querySelectorAll('.gl-pfeil').forEach(function (p) { p.hidden = true; });
})();
