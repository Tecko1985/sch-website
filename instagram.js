// Instagram-Karten im Block "Social Media beim SCH".
// Die Daten stehen in instagram-daten.js (window.SCH_INSTAGRAM), geschrieben NUR von der
// GitHub Action (.github/instagram.py). So committet der Bot nie in index.html, und
// Handaenderungen an der Startseite geben keine Konflikte mehr (Bugjagd 07.10.2026, T5-11).
// Bilder liegen im Repo (assets/instagram/), beim Anschauen geht keine Anfrage an Meta.
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
 daten.forEach(b => {
  if (!b || !b.href || !b.bild || !/^https:\/\/(www\.)?instagram\.com\//.test(b.href) || !/^[0-9A-Za-z_]+\.webp$/.test(b.bild)) return;
  const kopf = el('span', {}, ['INSTAGRAM · ', el('time', { datetime: b.iso || '' }, [b.datum || ''])]);
  const caption = el('div', { class: 'sch-socialcaption' }, [kopf]);
  if (b.text) caption.append(el('p', { class: 'sch-igtext' }, [b.text]));
  caption.append(el('span', { class: 'sch-socialcta' }, ['Auf Instagram ansehen']));
  const bild = el('img', { src: 'assets/instagram/' + b.bild, alt: (b.art || 'Bild') + ' zum Instagram-Beitrag vom ' + (b.datum || ''), loading: 'lazy' });
  const fuss = el('div', { class: 'sch-socialfooter' }, [el('img', { src: 'assets/logo.png', alt: '' }), el('span', {}, ['sc1911heiligenstadt']), el('b', { 'aria-label': 'Instagram' }, ['◎'])]);
  track.append(el('a', { class: 'sch-socialcard sch-igpost', href: b.href }, [el('div', { class: 'sch-socialvisual' }, [bild, caption]), fuss]));
 });
})();
