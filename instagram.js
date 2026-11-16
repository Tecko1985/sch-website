// Instagram-Karten: Startseite (Block "Social Media beim SCH") und seiten/nachwuchs.html ("Neu auf Instagram").
// Die Daten stehen in instagram-daten.js (window.SCH_INSTAGRAM = Vereinskonto, window.SCH_INSTAGRAM_NACHWUCHS =
// Nachwuchskonto), geschrieben NUR von der GitHub Action (.github/instagram.py). So committet der Bot nie in
// index.html (Bugjagd 07.10.2026, T5-11). Daten und Bilder (assets/instagram/) kommen nur beim Pages-Bau ins
// Artefakt, nie ins Repo (Abnahme 07.10.2026, AB3-2); im Repo ist instagram-daten.js leer.
// Beim Anschauen geht keine Anfrage an Meta. Klick auf eine Karte oeffnet die Grossansicht (ganzer Text, Teilen);
// Strg-/Cmd-Klick oeffnet wie gewohnt den Beitrag auf Instagram.
// Muss VOR sections.js laufen (die Pfeile messen die Breite der Spur).
(() => {
 const VEREIN = 'sc1911heiligenstadt', NACHWUCHS = 'sc1911heiligenstadt_nachwuchs';
 const el = (tag, attrs, kinder) => {
  const e = document.createElement(tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  (kinder || []).forEach(c => c != null && e.append(c));
  return e;
 };
 const kuerzen = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length <= n ? t : t.slice(0, n).replace(/\s+\S*$/, '') + ' …'; };
 const gueltig = b => b && b.href && b.bild && /^https:\/\/(www\.)?instagram\.com\//.test(b.href) && /^[0-9A-Za-z_]+\.webp$/.test(b.bild);
 const liste = (v, konto) => (Array.isArray(v) ? v : []).filter(gueltig).map(b => Object.assign({}, b, { konto }));
 // "vor 2 Stunden", "gestern", "vor 3 Tagen", danach das Datum
 const wann = b => {
  const t = Date.parse(b.iso || '');
  if (!t) return b.datum || '';
  const min = Math.round((Date.now() - t) / 60000);
  if (min < 60) return min <= 1 ? 'gerade eben' : 'vor ' + min + ' Minuten';
  const std = Math.round(min / 60);
  if (std < 24) return std === 1 ? 'vor 1 Stunde' : 'vor ' + std + ' Stunden';
  const tage = Math.round(std / 24);
  if (tage === 1) return 'gestern';
  if (tage < 7) return 'vor ' + tage + ' Tagen';
  return b.datum || '';
 };
 const igLogo = () => el('b', { class: 'sch-ig-logo', 'aria-hidden': 'true' }, []);

 // ---------- Grossansicht (ein <dialog> fuer alle Karten der Seite)
 let dialog, aktuelleListe = [], pos = 0, pfadGlobal = '';
 const baueDialog = () => {
  dialog = el('dialog', { class: 'sch-igdialog', 'aria-label': 'Instagram-Beitrag' });
  dialog.innerHTML = '<div class="sch-igbox"><div class="sch-igbild"></div><div class="sch-iginfo"><div class="sch-igkopf"></div>' +
   '<div class="sch-igvoll"></div><div class="sch-igteilen"><span>Teile diesen Beitrag</span><div class="sch-igknoepfe"></div></div></div>' +
   '<button type="button" class="sch-igzu" aria-label="Schließen">×</button>' +
   '<button type="button" class="sch-igpfeil sch-igzurueck" aria-label="Vorheriger Beitrag">‹</button>' +
   '<button type="button" class="sch-igpfeil sch-igweiter" aria-label="Nächster Beitrag">›</button></div>';
  document.body.append(dialog);
  dialog.querySelector('.sch-igzu').addEventListener('click', () => dialog.close());
  dialog.querySelector('.sch-igzurueck').addEventListener('click', () => zeige(pos - 1));
  dialog.querySelector('.sch-igweiter').addEventListener('click', () => zeige(pos + 1));
  // Klick neben die Box schliesst
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener('keydown', e => {
   if (e.key === 'ArrowLeft') zeige(pos - 1);
   if (e.key === 'ArrowRight') zeige(pos + 1);
  });
  dialog.addEventListener('close', () => document.documentElement.classList.remove('sch-igoffen'));
 };
 const zeige = i => {
  if (!aktuelleListe.length) return;
  pos = (i + aktuelleListe.length) % aktuelleListe.length;
  const b = aktuelleListe[pos];
  const bildBox = dialog.querySelector('.sch-igbild');
  const bild = el('img', { src: pfadGlobal + 'assets/instagram/' + b.bild, alt: (b.art && b.art !== 'Bild' ? b.art + ': ' : '') + (kuerzen(b.voll || b.text, 120) || 'Instagram-Beitrag') });
  const teile = [bild];
  if (b.art === 'Video') teile.push(el('a', { class: 'sch-igplay', href: b.href, target: '_blank', rel: 'noopener', 'aria-label': 'Video auf Instagram abspielen' }, []));
  if (b.art === 'Bilderserie') teile.push(el('span', { class: 'sch-igserie' }, ['Bilderserie · alle Bilder auf Instagram']));
  bildBox.replaceChildren(...teile);
  dialog.querySelector('.sch-igkopf').replaceChildren(
   el('img', { src: pfadGlobal + 'assets/logo.png', alt: '' }),
   el('div', {}, [el('b', {}, [b.konto]), el('time', { datetime: b.iso || '' }, [wann(b)])]),
   igLogo());
  dialog.querySelector('.sch-igvoll').replaceChildren(
   el('p', {}, [b.voll || b.text || '']),
   el('a', { class: 'sch-igauf', href: b.href, target: '_blank', rel: 'noopener' }, [b.art === 'Video' ? 'Video auf Instagram ansehen' : 'Auf Instagram ansehen']));
  dialog.querySelector('.sch-igvoll').scrollTop = 0;
  const url = encodeURIComponent(b.href);
  const knopf = (name, href) => el('a', { class: 'sch-igteil', href, target: '_blank', rel: 'noopener' }, [name]);
  const kopieren = el('button', { type: 'button', class: 'sch-igteil' }, ['Link kopieren']);
  kopieren.addEventListener('click', () => {
   const fertig = () => { kopieren.textContent = 'Kopiert ✓'; setTimeout(() => { kopieren.textContent = 'Link kopieren'; }, 2000); };
   if (navigator.clipboard) navigator.clipboard.writeText(b.href).then(fertig, () => prompt('Link kopieren:', b.href));
   else prompt('Link kopieren:', b.href);
  });
  dialog.querySelector('.sch-igknoepfe').replaceChildren(
   knopf('WhatsApp', 'https://wa.me/?text=' + url),
   knopf('Facebook', 'https://www.facebook.com/sharer/sharer.php?u=' + url),
   knopf('X', 'https://x.com/intent/post?url=' + url),
   kopieren);
  const mehrere = aktuelleListe.length > 1;
  dialog.querySelectorAll('.sch-igpfeil').forEach(p => { p.hidden = !mehrere; });
 };
 const oeffne = (listeDaten, i, pfad) => {
  if (!dialog) baueDialog();
  if (typeof dialog.showModal !== 'function') { location.href = listeDaten[i].href; return; }
  aktuelleListe = listeDaten; pfadGlobal = pfad;
  zeige(i);
  document.documentElement.classList.add('sch-igoffen');
  if (!dialog.open) dialog.showModal();
  dialog.querySelector('.sch-igzu').focus();
 };
 const klickOeffnet = (a, listeDaten, i, pfad) => a.addEventListener('click', e => {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
  e.preventDefault();
  oeffne(listeDaten, i, pfad);
 });

 // ---------- Startseite: beide Konten gemischt (Gemeinschaftsbeitraege liefert die Schnittstelle nur dem
 // Konto, das sie erstellt hat), ohne Doppelte, neueste zuerst. Die festen Profil-Karten waren nur Platzhalter
 // und verschwinden, sobald echte Beitraege da sind; ohne Daten bleiben sie stehen.
 const track = document.querySelector('.sch-social .sch-socialtrack');
 if (track) {
  const gesehen = new Set();
  const daten = liste(window.SCH_INSTAGRAM, VEREIN).concat(liste(window.SCH_INSTAGRAM_NACHWUCHS, NACHWUCHS))
   .filter(b => { const k = b.href.replace(/[?#].*$/, ''); if (gesehen.has(k)) return false; gesehen.add(k); return true; })
   .sort((a, b) => String(b.iso || '').localeCompare(String(a.iso || '')))
   .slice(0, 9);
  if (daten.length) {
   track.querySelectorAll('.sch-socialcard:not(.sch-igpost)').forEach(k => k.remove());
   daten.forEach((b, i) => {
    const vom = 'Instagram-Beitrag vom ' + (b.datum || '');
    const kurz = kuerzen(b.text, 100);
    const bild = el('img', { src: 'assets/instagram/' + b.bild, alt: (b.art && b.art !== 'Bild' ? b.art + ': ' : '') + (kurz || vom), loading: 'lazy' });
    const visual = el('div', { class: 'sch-socialvisual' }, [bild]);
    if (b.art === 'Video') visual.append(el('span', { class: 'sch-igplay', 'aria-hidden': 'true' }, []));
    if (b.art === 'Bilderserie') visual.append(el('span', { class: 'sch-igstapel', 'aria-hidden': 'true' }, []));
    if (b.text) visual.append(el('div', { class: 'sch-igzitat', 'aria-hidden': 'true' }, [el('p', {}, [kuerzen(b.text, 120)]), el('span', {}, ['mehr'])]));
    const fuss = el('div', { class: 'sch-socialfooter' }, [
     el('img', { src: 'assets/logo.png', alt: '' }), el('span', {}, [b.konto]),
     el('time', { class: 'sch-igwann', datetime: b.iso || '' }, [wann(b)]), igLogo()]);
    const a = el('a', { class: 'sch-socialcard sch-igpost', href: b.href, 'aria-label': vom + (kurz ? ': ' + kurz : '') + ' – Großansicht öffnen' }, [visual, fuss]);
    klickOeffnet(a, daten, i, '');
    track.append(a);
   });
  }
 }

 // ---------- Nachwuchs-Seite: nur das Nachwuchskonto, Block bleibt ohne Daten verborgen
 const block = document.querySelector('.nw-insta');
 const raster = block && block.querySelector('.nw-instaraster');
 if (raster) {
  const daten = liste(window.SCH_INSTAGRAM_NACHWUCHS, NACHWUCHS).slice(0, 6);
  const pfad = block.getAttribute('data-pfad') || '';
  daten.forEach((b, i) => {
   const vom = 'Instagram-Beitrag vom ' + (b.datum || '');
   const kurz = kuerzen(b.text, 100);
   const bild = el('img', { src: pfad + 'assets/instagram/' + b.bild, alt: (b.art && b.art !== 'Bild' ? b.art + ': ' : '') + (kurz || vom), loading: 'lazy' });
   const text = el('span', { class: 'nw-instatext' }, [el('time', { datetime: b.iso || '' }, [wann(b)])]);
   if (b.text) text.append(el('span', {}, [kuerzen(b.text, 90)]));
   const a = el('a', { class: 'nw-instakarte' + (b.art === 'Video' ? ' nw-video' : ''), href: b.href, 'aria-label': vom + (kurz ? ': ' + kurz : '') + ' – Großansicht öffnen' }, [bild, text]);
   klickOeffnet(a, daten, i, pfad);
   raster.append(a);
  });
  if (daten.length) block.hidden = false;
 }
})();
