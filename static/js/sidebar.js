(() => {
 'use strict';
 const sidebar = document.getElementById('sidebar'), toggle = document.querySelector('.menu-toggle'), overlay = document.querySelector('.sidebar-overlay');
 if (!sidebar || !toggle) return;
 const mobile = matchMedia('(max-width: 1024px)');
 let collapsed = false; try { collapsed = localStorage.getItem('academe-sidebar') === 'collapsed'; } catch {}
 const sync = () => {
   document.body.classList.toggle('sidebar-collapsed', collapsed && !mobile.matches);
   toggle.setAttribute('aria-expanded', String(mobile.matches ? sidebar.classList.contains('open') : !collapsed));
   if (mobile.matches && !sidebar.classList.contains('open')) sidebar.inert = true; else sidebar.inert = false;
 };
 const close = () => { sidebar.classList.remove('open'); document.body.style.overflow = ''; sync(); };
 toggle.addEventListener('click', () => {
   if (mobile.matches) {sidebar.classList.toggle('open'); document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';}
   else {collapsed = !collapsed; try { localStorage.setItem('academe-sidebar', collapsed ? 'collapsed' : 'expanded'); } catch {}}
   sync(); if (mobile.matches && sidebar.classList.contains('open')) sidebar.querySelector('a').focus();
 });
 overlay?.addEventListener('click', () => {close(); toggle.focus();});
 document.addEventListener('keydown', event => {
   if (!mobile.matches || !sidebar.classList.contains('open')) return;
   if (event.key === 'Escape') {close(); toggle.focus();}
   if (event.key === 'Tab') {
     const links = [...sidebar.querySelectorAll('a,button')].filter(item => item.getClientRects().length);
     const first = links[0], last = links.at(-1);
     if (event.shiftKey && document.activeElement === first) {event.preventDefault();last.focus();}
     else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first.focus();}
   }
 });
 mobile.addEventListener('change', close); sync();
})();
