(() => {
  'use strict';
  const media = matchMedia('(prefers-color-scheme: dark)');
  let choice; try { choice = localStorage.getItem('academe-theme'); } catch {}
  const apply = theme => {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
      button.setAttribute('title', button.getAttribute('aria-label'));
      const icon = button.querySelector('i'); if (icon) icon.className = `bi bi-${theme === 'dark' ? 'sun' : 'moon'}`;
    });
    document.dispatchEvent(new CustomEvent('academe:theme'));
  };
  apply(choice === 'dark' || choice === 'light' ? choice : media.matches ? 'dark' : 'light');
  document.addEventListener('DOMContentLoaded', () => {
    apply(document.documentElement.dataset.theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(button => button.addEventListener('click', () => {
      choice = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('academe-theme', choice); } catch {}
      apply(choice);
    }));
  });
  media.addEventListener('change', event => { if (!choice) apply(event.matches ? 'dark' : 'light'); });
})();
