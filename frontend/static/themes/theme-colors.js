const THEME_DEFINITIONS = {

  'warm-modern': {
    name: 'Warm & Modern',
    description: 'Varm oransje/amber design',
    colors: {
      primary: '#2c3e50',
      secondary: '#d97706',
      accent: '#d97706',
      background: '#faf9f7',
      surface: '#ffffff',
      textPrimary: '#1f2937',
      textSecondary: '#6b7280',
      textLight: '#9ca3af',
      chipFamily: '#d1fae5',
      chipPopular: '#dbeafe',
      chipQuick: '#fed7aa',
      border: '#e5e7eb',
      divider: '#f3f4f6',
    },
    preview: '#d97706',
  },

  // To add a new theme:
  // 1. Copy a block above, give it a new key and colors
  // 2. Add a .theme-option entry in base.html
  // 3. If you need component-level overrides beyond color vars,
  //    add [data-theme="your-key"] rules at the bottom of style.css
};

function getTheme(name) {
  return THEME_DEFINITIONS[name] || THEME_DEFINITIONS['warm-modern'];
}

function getAllThemes() {
  return Object.entries(THEME_DEFINITIONS).map(([id, def]) => ({ id, ...def }));
}
