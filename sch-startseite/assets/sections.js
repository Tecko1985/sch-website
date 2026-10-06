(() => {
 document.querySelectorAll('.sch-social').forEach(section => {
  const track=section.querySelector('.sch-socialtrack');
  if(track){
   const buttons=[...section.querySelectorAll('[data-social-direction]')];
   const update=()=>{buttons.forEach(b=>{b.disabled=Number(b.dataset.socialDirection)<0?track.scrollLeft<2:track.scrollLeft+track.clientWidth>=track.scrollWidth-2})};
   buttons.forEach(b=>b.addEventListener('click',()=>track.scrollBy({left:(track.firstElementChild.getBoundingClientRect().width+24)*Number(b.dataset.socialDirection),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})));
   track.addEventListener('scroll',update,{passive:true});window.addEventListener('resize',update,{passive:true});update();
  }
  section.querySelectorAll('.sch-facebook-load').forEach(button=>button.addEventListener('click',()=>{
   const frame=document.createElement('iframe');frame.title='Aktuelle Facebook-Beiträge des SCH';frame.src='https://www.facebook.com/plugins/page.php?href='+encodeURIComponent(button.dataset.facebook)+'&tabs=timeline&width=280&height=430&small_header=true&adapt_container_width=true&hide_cover=false&show_facepile=false';frame.loading='lazy';frame.allow='encrypted-media';button.closest('.sch-socialvisual').replaceChildren(frame);
  }));
 });
})();
