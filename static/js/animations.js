(() => {
 'use strict';
 document.addEventListener('click', event => {
   const button = event.target.closest('.button,.nav-item'); if (!button || Academe.reduced()) return;
   const r = button.getBoundingClientRect(), size = Math.max(r.width,r.height), dot = Academe.el('span',{class:'ripple-dot','aria-hidden':'true'});
   const x = event.detail ? event.clientX-r.left : r.width/2, y = event.detail ? event.clientY-r.top : r.height/2;
   Object.assign(dot.style,{width:`${size}px`,height:`${size}px`,left:`${x-size/2}px`,top:`${y-size/2}px`});
   button.append(dot);dot.addEventListener('animationend',()=>dot.remove(),{once:true});
 });
 if (!Academe.reduced() && 'IntersectionObserver' in window) {
   const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) {entry.target.classList.add('in-view');observer.unobserve(entry.target);} }), {threshold:.08});
   document.querySelectorAll('[data-reveal]').forEach(element => {element.classList.add('reveal-ready');observer.observe(element);});
 }
})();
