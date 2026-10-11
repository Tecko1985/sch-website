// Newsletter: Anmelden, Bestaetigen und Abmelden. Redet mit dem Vereins-Gateway
// (Aktionen newsletter-* in ToolsUebersicht/admin-worker.js). Laeuft auf der
// Startseite (Formular #newsletter) und auf newsletter.html.
// ⚠️ Die Adresse von newsletter.html steht ein zweites Mal im Worker (NL_SEITE_URL).
(function () {
  var GATEWAY = 'https://sch-gateway.clubdach.de';

  function rufe(daten) {
    return fetch(GATEWAY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(daten)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (!r.ok) throw new Error((b && b.error) || 'Das hat nicht geklappt. Bitte versuch es später noch einmal.');
        return b;
      });
    });
  }

  function text(el, inhalt, fehler) {
    if (!el) return;
    el.textContent = inhalt;
    el.hidden = !inhalt;
    el.classList.toggle('nl-fehler', !!fehler);
  }

  // Formulare: data-nl="anmelden" oder data-nl="abmelden"
  document.querySelectorAll('form[data-nl]').forEach(function (form) {
    var art = form.getAttribute('data-nl');
    var meldung = form.querySelector('.nl-meldung');
    var knopf = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var email = (form.elements.email.value || '').trim();
      if (art === 'anmelden' && !form.elements.datenschutz.checked) {
        text(meldung, 'Bitte setz den Haken bei den Datenschutz-Hinweisen.', true);
        return;
      }
      var daten = art === 'anmelden'
        ? { action: 'newsletter-anmelden', email: email, vorname: (form.elements.vorname && form.elements.vorname.value) || '', datenschutz: true }
        : { action: 'newsletter-abmelden-anfordern', email: email };
      knopf.disabled = true;
      text(meldung, 'Einen Moment …', false);
      rufe(daten).then(function () {
        form.reset();
        text(meldung, art === 'anmelden'
          ? 'Fast geschafft! Schau in dein Postfach und klick auf den Link in unserer Mail. Erst dann bist du angemeldet.'
          : 'Wenn diese Adresse angemeldet ist, bekommst du gleich eine Mail mit dem Abmeldelink.', false);
      }).catch(function (e) {
        text(meldung, e.message, true);
      }).then(function () { knopf.disabled = false; });
    });
  });

  // Gutschein-Hinweis: welche Partner geben gerade etwas zur Anmeldung dazu?
  var hinweis = document.querySelector('[data-nl-gutscheine]');
  if (hinweis) {
    rufe({ action: 'newsletter-oeffentlich' }).then(function (b) {
      var liste = (b && b.gutscheine) || [];
      if (!liste.length) return;
      var ul = document.createElement('ul');
      liste.forEach(function (g) {
        var li = document.createElement('li');
        var strong = document.createElement('strong');
        strong.textContent = g.firma;
        li.appendChild(strong);
        if (g.text) li.appendChild(document.createTextNode(' – ' + g.text));
        ul.appendChild(li);
      });
      hinweis.querySelector('.nl-gutscheinliste').replaceChildren(ul);
      hinweis.hidden = false;
    }).catch(function () { /* ohne Hinweis geht die Anmeldung trotzdem */ });
  }

  // newsletter.html?bestaetigen=… und ?abmelden=… (Links aus den Mails)
  var ergebnis = document.getElementById('nl-ergebnis');
  if (!ergebnis) return;
  var p = new URLSearchParams(location.search);
  var token = p.get('bestaetigen') || p.get('abmelden');
  if (!token) return;
  var bestaetigen = !!p.get('bestaetigen');
  // Token nicht in der Adresszeile stehen lassen (Verlauf, Teilen-Knopf).
  try { history.replaceState(null, '', location.pathname); } catch (_) {}
  var titel = ergebnis.querySelector('h2');
  var absatz = ergebnis.querySelector('p');
  var codes = ergebnis.querySelector('.nl-codes');
  ergebnis.hidden = false;
  titel.textContent = bestaetigen ? 'Anmeldung wird bestätigt …' : 'Abmeldung läuft …';
  absatz.textContent = '';
  rufe({ action: bestaetigen ? 'newsletter-bestaetigen' : 'newsletter-abmelden', token: token }).then(function (b) {
    if (!bestaetigen) {
      titel.textContent = 'Du bist abgemeldet';
      absatz.textContent = 'Wir haben deine Adresse gelöscht. Du bekommst keinen Newsletter mehr von uns.';
      return;
    }
    titel.textContent = 'Danke! Du bist angemeldet.';
    absatz.textContent = b.schonBestaetigt
      ? 'Deine Anmeldung war schon bestätigt. Alles ist gut.'
      : 'Ab jetzt bekommst du Neuigkeiten vom SCH per Mail. Wir haben dir eine Willkommensmail geschickt.';
    var liste = b.gutscheine || [];
    if (!liste.length) return;
    var h = document.createElement('h3');
    h.textContent = 'Deine Gutscheine';
    codes.appendChild(h);
    liste.forEach(function (g) {
      var k = document.createElement('div');
      k.className = 'nl-code';
      var f = document.createElement('strong'); f.textContent = g.firma; k.appendChild(f);
      if (g.text) { var t = document.createElement('span'); t.textContent = g.text; k.appendChild(t); }
      var c = document.createElement('code'); c.textContent = g.code; k.appendChild(c);
      codes.appendChild(k);
    });
    var n = document.createElement('p');
    n.className = 'nl-klein';
    n.textContent = 'Die Codes stehen auch in deiner Willkommensmail.';
    codes.appendChild(n);
  }).catch(function (e) {
    titel.textContent = 'Das hat nicht geklappt';
    absatz.textContent = e.message;
  });
})();
