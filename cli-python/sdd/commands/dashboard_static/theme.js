// Theme: defaults to Auto (follows OS/browser prefers-color-scheme via the
// CSS media query). An explicit Light/Dark pick sets data-theme on <html>,
// which the CSS above gives higher specificity than the media query, and
// persists to localStorage so it survives reloads and doesn't depend on
// the OS signal reaching this page correctly.
const THEME_KEY = 'sdd-dashboard-theme';

function applyTheme(theme) {
  if (theme === 'light' || theme === 'dark') {
    document.documentElement.setAttribute('data-theme', theme);
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  document.querySelectorAll('[data-theme-choice]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.themeChoice === theme);
  });
}

(function initTheme() {
  applyTheme(localStorage.getItem(THEME_KEY) || 'auto');
  document.querySelectorAll('[data-theme-choice]').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.themeChoice;
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    });
  });
})();