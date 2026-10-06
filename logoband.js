// Logo-Band anhalten und weiterlaufen lassen (WCAG 2.2.2: bewegte Inhalte müssen anhaltbar sein, auch am Handy).
(function () {
  var band = document.querySelector('.sch-logoband');
  var knopf = document.querySelector('.sch-logopause');
  if (!band || !knopf) return;
  knopf.addEventListener('click', function () {
    var an = band.classList.toggle('pausiert');
    knopf.setAttribute('aria-pressed', an ? 'true' : 'false');
    knopf.textContent = an ? 'Logos weiterlaufen lassen' : 'Logos anhalten';
  });
})();
