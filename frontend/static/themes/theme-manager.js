// Themes that use the "rich" full-layout index (images, day-nav, summary bar)
const RICH_LAYOUT_THEMES = new Set(['warm-terracotta']);

// No hardcoded builtin themes — all themes load from CSS files in previews/
const BUILTIN_THEMES = new Set([]);

class ThemeManager {
  constructor() {
    this.currentTheme = localStorage.getItem('pi-menu-theme') || 'warm-modern';
    this.applyTheme(this.currentTheme);
    this.setupEventListeners();
    this.markActiveTheme();
  }

  setupEventListeners() {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    const dropdown = document.getElementById('theme-dropdown');
    if (!toggleBtn || !dropdown) return;

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('open', !dropdown.classList.contains('open'));
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.theme-switcher')) {
        dropdown.classList.remove('open');
      }
    });

    document.querySelectorAll('.theme-option').forEach((option) => {
      option.addEventListener('click', () => {
        const name = option.dataset.theme;
        this.applyTheme(name);
        localStorage.setItem('pi-menu-theme', name);
        this.markActiveTheme();
        dropdown.classList.remove('open');
      });
    });
  }

  applyTheme(name) {
    const root = document.documentElement;

    if (BUILTIN_THEMES.has(name)) {
      // Built-in theme: apply via JS color variables (existing behaviour)
      const theme = getTheme(name);
      if (!theme) return;
      const camel2kebab = (s) => s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
      Object.entries(theme.colors).forEach(([key, val]) => {
        root.style.setProperty(`--color-${camel2kebab(key)}`, val);
      });
      // Remove any injected preview CSS link so it doesn't conflict
      this._removePreviewThemeLink();
    } else {
      // Preview theme: inject the scoped CSS file and let CSS variables do the work
      this.loadPreviewTheme(name);
    }

    root.setAttribute('data-theme', name);
    this.currentTheme = name;
    this._switchLayout(name);
  }

  /**
   * Inject (or update) a <link> tag that loads the preview theme CSS file.
   * The CSS file uses [data-theme="foo"] selectors so it only activates
   * when the matching data-theme attribute is set on <html>.
   *
   * @param {string} themeId  e.g. "glass-kitchen"
   */
  loadPreviewTheme(themeId) {
    const href = `/static/themes/previews/theme-${themeId}.css`;
    let link = document.getElementById('preview-theme-css');
    if (link) {
      // Already exists — just update the href
      link.href = href;
    } else {
      link = document.createElement('link');
      link.id = 'preview-theme-css';
      link.rel = 'stylesheet';
      link.href = href;
      document.head.appendChild(link);
    }
  }

  /**
   * Remove the injected preview CSS link (used when switching back to a built-in theme).
   */
  _removePreviewThemeLink() {
    const link = document.getElementById('preview-theme-css');
    if (link) {
      link.remove();
    }
  }

  /**
   * Fetch the theme registry JSON and return the array of preview theme entries.
   * Returns an empty array on failure.
   *
   * @returns {Promise<Array<{id:string, name:string, file:string, preview_color:string}>>}
   */
  async loadThemeRegistry() {
    try {
      const res = await fetch('/static/themes/previews/theme-registry.json');
      if (!res.ok) {
        console.warn(`[ThemeManager] Could not load theme registry: HTTP ${res.status}`);
        return [];
      }
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.warn('[ThemeManager] Failed to fetch theme registry:', err);
      return [];
    }
  }

  _switchLayout(name) {
    const standard = document.getElementById('layout-standard');
    const rich = document.getElementById('layout-rich');
    if (!standard || !rich) return;
    const useRich = RICH_LAYOUT_THEMES.has(name);
    standard.style.display = useRich ? 'none' : '';
    rich.style.display = useRich ? '' : 'none';
  }

  markActiveTheme() {
    document.querySelectorAll('.theme-option').forEach((opt) => {
      opt.classList.toggle('active', opt.dataset.theme === this.currentTheme);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.themeManager = new ThemeManager();
});
