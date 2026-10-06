(() => {
  document.querySelectorAll('.sch-matches').forEach(section => {
    const tabs = [...section.querySelectorAll('[role=tab]')];
    const panels = [...section.querySelectorAll('[role=tabpanel]')];
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function layout(panel, initial = false) {
      const track = panel.querySelector('.sch-gametrack');
      const cards = [...track.children];
      if (!cards.length) return;
      const step = cards.length > 1 ? cards[1].offsetLeft - cards[0].offsetLeft : cards[0].offsetWidth;
      if (initial && !panel.dataset.positioned) {
        track.scrollLeft = step * Number(track.dataset.initial || 0);
        panel.dataset.positioned = 'true';
      }
      const controls = panel.querySelectorAll('[data-direction]');
      controls[0].disabled = track.scrollLeft < 2;
      controls[1].disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
      return {track, step};
    }
    function select(index, focus = false) {
      tabs.forEach((tab, i) => {
        tab.setAttribute('aria-selected', String(i === index));
        tab.tabIndex = i === index ? 0 : -1;
        panels[i].hidden = i !== index;
      });
      section.querySelector('.sch-allgames').href = panels[index].dataset.allUrl;
      layout(panels[index], true);
      if (focus) tabs[index].focus();
    }
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(index));
      tab.addEventListener('keydown', e => {
        let next = index;
        if (e.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (e.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (e.key === 'Home') next = 0;
        else if (e.key === 'End') next = tabs.length - 1;
        else return;
        e.preventDefault(); select(next, true);
      });
    });
    panels.forEach(panel => {
      const track = panel.querySelector('.sch-gametrack');
      track.addEventListener('scroll', () => layout(panel), {passive:true});
      panel.querySelectorAll('[data-direction]').forEach(button => button.addEventListener('click', () => {
        const info = layout(panel);
        info.track.scrollBy({left:info.step * Number(button.dataset.direction), behavior:reduced ? 'auto' : 'smooth'});
      }));
    });
    select(0);
    window.addEventListener('resize', () => panels.filter(p => !p.hidden).forEach(p => layout(p)), {passive:true});
  });
})();
