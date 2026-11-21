// theme.js -- loaded from <head>, before the stylesheets. Not needed to theme the page: class="theme-dark" on <html> already does that, with or without
// JavaScript. This only restores a theme the visitor picked before, ahead of first paint so it never flashes.
(function () {
  var saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) { /* storage blocked */ }
  if (/^[a-z]+$/.test(saved)) document.documentElement.classList.replace('theme-dark', 'theme-' + saved);
  document.documentElement.classList.add('js');
})();
