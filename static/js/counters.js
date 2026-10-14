(() => {
 'use strict';
 const animate = element => {
   if (element.dataset.counted) return; element.dataset.counted = 'true';
   const original = element.dataset.count, match = original.match(/^([\d,.]+)(%?)$/); if (!match || Academe.reduced()) return;
   const target = Number(match[1].replaceAll(',',''));if(!Number.isFinite(target)) return;
   const start = performance.now(), duration = 650;
   const update = time => {const progress = Math.min(1,(time-start)/duration);element.textContent = Math.round(target*(1-(1-progress)**3)).toLocaleString()+match[2];if(progress<1)requestAnimationFrame(update);else element.textContent=original;};
   requestAnimationFrame(update);
 };
 if ('IntersectionObserver' in window) {const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){animate(entry.target);observer.unobserve(entry.target);}}));document.querySelectorAll('[data-count]').forEach(el=>observer.observe(el));}
 else document.querySelectorAll('[data-count]').forEach(animate);
})();
