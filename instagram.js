// Instagram-Karten im Block "Social Media beim SCH".
// Die Daten stehen in instagram-daten.js (window.SCH_INSTAGRAM), geschrieben NUR von der
// GitHub Action (.github/instagram.py). So committet der Bot nie in index.html, und
// Handaenderungen an der Startseite geben keine Konflikte mehr (Bugjagd 07.10.2026, T5-11).
// Daten und Bilder (assets/instagram/) kommen nur beim Pages-Bau ins Artefakt, nie ins Repo (Abnahme
// 07.10.2026, AB3-2); im Repo ist instagram-daten.js leer. Beim Anschauen geht keine Anfrage an Meta.
// Muss VOR sections.js laufen (die Pfeile messen die Breite der Spur).
(() => {
 const daten = Array.isArray(window.SCH_INSTAGRAM) ? window.SCH_INSTAGRAM : [];
 const track = document.querySelector('.sch-social .sch-socialtrack');
 if (!track || !daten.length) return;
 const el = (tag, attrs, kinder) => {
  const e = document.createElement(tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  (kinder || []).forEach(c => e.append(c));
  return e;
 };
 // Abnahme 07.10.2026 (AB3-5): Alt-Text = gekuerzter Beitragstext (sonst "Instagram-Beitrag vom ..."),
 // der Link hat einen eigenen, verstaendlichen Namen, das Zierzeichen ist fuer Vorleser ausgeblendet.
 const kuerzen = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length <= n ? t : t.slice(0, n).replace(/\s+\S*$/, '') + ' …'; };
 daten.forEach(b => {
  if (!b || !b.href || !b.bild || !/^https:\/\/(www\.)?instagram\.com\//.test(b.href) || !/^[0-9A-Za-z_]+\.webp$/.test(b.bild)) return;
  const kopf = el('span', {}, ['INSTAGRAM · ', el('time', { datetime: b.iso || '' }, [b.datum || ''])]);
  const caption = el('div', { class: 'sch-socialcaption' }, [kopf]);
  if (b.text) caption.append(el('p', { class: 'sch-igtext' }, [b.text]));
  caption.append(el('span', { class: 'sch-socialcta' }, ['Auf Instagram ansehen']));
  const vom = 'Instagram-Beitrag vom ' + (b.datum || '');
  const kurz = kuerzen(b.text, 100);
  const bild = el('img', { src: 'assets/instagram/' + b.bild, alt: (b.art && b.art !== 'Bild' ? b.art + ': ' : '') + (kurz || vom), loading: 'lazy' });
  const fuss = el('div', { class: 'sch-socialfooter' }, [el('img', { src: 'assets/logo.png', alt: '' }), el('span', {}, ['sc1911heiligenstadt']), el('b', { class: 'sch-ig-logo', 'aria-hidden': 'true' }, [])]);
  track.append(el('a', { class: 'sch-socialcard sch-igpost', href: b.href, 'aria-label': vom + ' auf Instagram ansehen' + (kurz ? ': ' + kurz : '') }, [el('div', { class: 'sch-socialvisual' }, [bild, caption]), fuss]));
 });
})();

// Nachwuchs-Konto (window.SCH_INSTAGRAM_NACHWUCHS) im Block "Neu auf Instagram" auf seiten/nachwuchs.html.
// Ohne Daten bleibt der Block verborgen (hidden).
(() => {
 const daten = Array.isArray(window.SCH_INSTAGRAM_NACHWUCHS) ? window.SCH_INSTAGRAM_NACHWUCHS : [];
 const block = document.querySelector('.nw-insta');
 const raster = block && block.querySelector('.nw-instaraster');
 if (!raster || !daten.length) return;
 const pfad = block.getAttribute('data-pfad') || '';
 const el = (tag, attrs, kinder) => {
  const e = document.createElement(tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  (kinder || []).forEach(c => e.append(c));
  return e;
 };
 const kuerzen = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length <= n ? t : t.slice(0, n).replace(/\s+\S*$/, '') + ' …'; };
 let anzahl = 0;
 daten.forEach(b => {
  if (!b || !b.href || !b.bild || !/^https:\/\/(www\.)?instagram\.com\//.test(b.href) || !/^[0-9A-Za-z_]+\.webp$/.test(b.bild)) return;
  const vom = 'Instagram-Beitrag vom ' + (b.datum || '');
  const kurz = kuerzen(b.text, 100);
  const bild = el('img', { src: pfad + 'assets/instagram/' + b.bild, alt: (b.art && b.art !== 'Bild' ? b.art + ': ' : '') + (kurz || vom), loading: 'lazy' });
  const text = el('span', { class: 'nw-instatext' }, [el('time', { datetime: b.iso || '' }, [b.datum || ''])]);
  if (b.text) text.append(el('span', {}, [kuerzen(b.text, 90)]));
  raster.append(el('a', { class: 'nw-instakarte', href: b.href, rel: 'noopener', 'aria-label': vom + ' auf Instagram ansehen' + (kurz ? ': ' + kurz : '') }, [bild, text]));
  anzahl++;
 });
 if (anzahl) block.hidden = false;
})();
