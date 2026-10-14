(() => {
 'use strict';
 const permitted = matchMedia('(hover: hover) and (pointer: fine) and (min-width: 769px) and (prefers-reduced-motion: no-preference)');
 const glow = document.querySelector('.cursor-glow');
 let frame = 0, x = -500, y = -500, targetX = -500, targetY = -500, card = null, button = null;
 const reset = () => {
   cancelAnimationFrame(frame); frame = 0; if (glow) glow.style.opacity = '0';
   if (card?.hasAttribute('data-tilt')) card.style.transform = ''; if (button) button.style.transform = ''; card = button = null;
 };
 const tick = () => {
   frame = 0; if (!permitted.matches || document.hidden) return;
   x += (targetX-x) * .13; y += (targetY-y) * .13;
   if (glow) {glow.style.transform = `translate3d(${x-170}px,${y-170}px,0)`; glow.style.opacity = '1';}
   if (card) {
     const rect = card.getBoundingClientRect(), localX = targetX - rect.left, localY = targetY - rect.top;
     card.style.setProperty('--mouse-x', `${localX}px`);card.style.setProperty('--mouse-y', `${localY}px`);
     if (card.hasAttribute('data-tilt')) card.style.transform = `perspective(1000px) rotateX(${(0.5-localY/rect.height)*4}deg) rotateY(${(localX/rect.width-0.5)*4}deg)`;
   }
   if (button) {const r = button.getBoundingClientRect();button.style.transform = `translate(${Math.max(-3,Math.min(3,(targetX-r.left-r.width/2)*.07))}px,${Math.max(-3,Math.min(3,(targetY-r.top-r.height/2)*.07))}px)`;}
   if (Math.abs(targetX-x) + Math.abs(targetY-y) > .5) frame = requestAnimationFrame(tick);
 };
 document.addEventListener('pointermove', event => {
   if (!permitted.matches) return;
   targetX = event.clientX;targetY = event.clientY;
   const nextCard = event.target.closest('[data-spotlight],[data-tilt]'), nextButton = event.target.closest('[data-magnetic]');
   if (card && card !== nextCard && card.hasAttribute('data-tilt')) card.style.transform = '';
   if (button && button !== nextButton) button.style.transform = '';
   card = nextCard;button = nextButton;if (!frame) frame = requestAnimationFrame(tick);
 }, {passive:true});
 document.documentElement.addEventListener('pointerleave', reset);document.addEventListener('visibilitychange', () => {if(document.hidden) reset();});permitted.addEventListener('change', reset);
})();
