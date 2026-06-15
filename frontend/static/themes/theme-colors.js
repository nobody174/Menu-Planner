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

  'default': {
    name: 'Original Design',
    description: 'Klassisk blå design',
    colors: {
      primary: '#2c3e50',
      secondary: '#3498db',
      accent: '#3498db',
      background: '#f8f9fa',
      surface: '#ffffff',
      textPrimary: '#2c3e50',
      textSecondary: '#6b7280',
      textLight: '#9ca3af',
      chipFamily: '#e8f4f8',
      chipPopular: '#e3f2fd',
      chipQuick: '#fff3e0',
      border: '#bdc3c7',
      divider: '#ecf0f1',
    },
    preview: '#3498db',
  },

  'nordic-modern': {
    name: 'Nordic Modern',
    description: 'Skandinavisk, ren og romslig',
    colors: {
      primary: '#0f172a',
      secondary: '#2563eb',
      accent: '#2563eb',
      background: '#f8fafc',
      surface: '#ffffff',
      textPrimary: '#0f172a',
      textSecondary: '#64748b',
      textLight: '#94a3b8',
      chipFamily: '#dbeafe',
      chipPopular: '#e0e7ff',
      chipQuick: '#d1fae5',
      border: '#e2e8f0',
      divider: '#f1f5f9',
    },
    preview: '#2563eb',
  },

  'warm-terracotta': {
    name: 'Terracotta & Sage',
    description: 'Jordnær og varm med urte-grønt',
    colors: {
      primary: '#5c2d1e',
      secondary: '#527f57',
      accent: '#d97b36',
      background: '#faf7f2',
      surface: '#ffffff',
      textPrimary: '#1e1b18',
      textSecondary: '#524b41',
      textLight: '#8a8070',
      chipFamily: '#d1fae5',
      chipPopular: '#fde8d0',
      chipQuick: '#c8dfc9',
      border: '#e2ddd4',
      divider: '#f2ede6',
    },
    preview: '#d97b36',
  },

  'warm-modernist': {
    name: 'Warm Modernist',
    description: 'Kull & terrakotta — varm og lesbar',
    colors: {
      primary: '#222933',
      secondary: '#a56158',
      accent: '#a56158',
      background: '#faf9f6',
      surface: '#ffffff',
      textPrimary: '#1a1a2e',
      textSecondary: '#6f7680',
      textLight: '#9ca3af',
      chipFamily: '#d4edda',
      chipPopular: '#fdebd4',
      chipQuick: '#dff0e3',
      border: '#e8e4df',
      divider: '#f0ece6',
    },
    preview: '#a56158',
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
