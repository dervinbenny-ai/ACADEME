(() => {
 'use strict';
 const el = (tag, attrs = {}, text = '') => {
   const element = document.createElement(tag);
   for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
   if (text) element.textContent = text;
   return element;
 };
 const toast = (message, type = 'info') => {
   const stack = document.querySelector('.toast-stack'); if (!stack) return;
   const note = el('div', {class: `notice ${type}`, 'data-toast': ''});
   note.append(el('i', {class: `bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'}`}), el('span', {}, message), el('button', {type:'button', class:'notice-close', 'aria-label':'Dismiss notification'}, '×'));
   stack.append(note); if (type === 'success') setTimeout(() => note.remove(), 8000);
 };
 window.Academe = {el, toast, csrf: () => document.querySelector('meta[name=csrf-token]')?.content || '', reduced: () => matchMedia('(prefers-reduced-motion: reduce)').matches};
 document.addEventListener('click', event => { if (event.target.closest('.notice-close')) event.target.closest('.notice')?.remove(); });
 document.querySelectorAll('.toast-stack .success').forEach(note => setTimeout(() => note.remove(), 8000));
 try { const message = sessionStorage.getItem('academe-flash'); if (message) { sessionStorage.removeItem('academe-flash'); toast(message, 'success'); } } catch {}
 document.querySelectorAll('[data-avatar]').forEach(avatar => {
   let hash = 0; for (const char of avatar.dataset.avatar) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
   avatar.style.setProperty('--avatar-hue', String(190 + Math.abs(hash) % 110));
 });
 document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { const input = document.getElementById('assistant-prompt'); if (input) {input.value = button.dataset.prompt; input.focus();} }));
 const classPicker = document.querySelector('[data-class-teachers]');
 if (classPicker) {
   const teacherPicker = document.getElementById('teacher_id');
   if (teacherPicker) {
     const options = Array.from(teacherPicker.options).map(option => option.cloneNode(true));
     const update = () => teacherPicker.replaceChildren(...options.filter(option => !option.value || option.dataset.class === classPicker.value).map(option => option.cloneNode(true)));
     classPicker.addEventListener('change', update); update(); if (teacherPicker.dataset.selected) teacherPicker.value = teacherPicker.dataset.selected;
   }
 }
 document.addEventListener('click', event => { document.querySelectorAll('.account-menu[open]').forEach(menu => { if (!menu.contains(event.target)) menu.open = false; }); });
 document.addEventListener('keydown', event => { if (event.key === 'Escape') document.querySelectorAll('.account-menu[open]').forEach(menu => {menu.open = false; menu.querySelector('summary').focus();}); });
})();
