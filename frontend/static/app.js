// ── i18n helper ───────────────────────────────────────────────────────────────
// Safe wrapper: always returns a string, never exposes missing key names.
function _t(key) {
    // window.T is injected by base.html (server-rendered, always available synchronously)
    if (window.T && window.T[key] !== undefined) return window.T[key];
    if (window.languageManager && window.languageManager.translations) {
        var val = window.languageManager.t(key);
        if (val && val !== key) return val;
    }
    return key;
}

// ── Custom modal (replaces browser alert/confirm) ─────────────────────────────

var _modalResolve = null;

function _ensureModal() {
    if (document.getElementById('pm-modal')) return;

    var el = document.createElement('div');
    el.innerHTML = [
        '<div id="pm-modal" role="dialog" aria-modal="true" style="display:none;position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;">',
        '  <div id="pm-modal-backdrop" style="position:absolute;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(2px);"></div>',
        '  <div id="pm-modal-box" style="position:relative;background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.25);padding:32px 28px 24px;max-width:380px;width:100%;animation:pmSlideIn .18s ease;">',
        '    <div id="pm-modal-icon" style="font-size:2rem;margin-bottom:12px;text-align:center;"></div>',
        '    <div id="pm-modal-title" style="font-size:1.1rem;font-weight:700;color:#1a1a1a;margin-bottom:8px;text-align:center;"></div>',
        '    <div id="pm-modal-msg"   style="font-size:.95rem;color:#555;line-height:1.5;text-align:center;margin-bottom:24px;"></div>',
        '    <div id="pm-modal-btns"  style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;"></div>',
        '  </div>',
        '</div>',
        '<style>',
        '@keyframes pmSlideIn{from{opacity:0;transform:translateY(-14px)}to{opacity:1;transform:translateY(0)}}',
        '#pm-modal[data-hidden]{display:none!important}',
        '#pm-modal-box .pm-btn{padding:10px 24px;border:none;border-radius:9px;font-size:.95rem;font-weight:600;cursor:pointer;transition:transform .1s,box-shadow .1s}',
        '#pm-modal-box .pm-btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}',
        '#pm-modal-box .pm-btn-primary{background:var(--color-primary,#d97706);color:#fff}',
        '#pm-modal-box .pm-btn-secondary{background:#f1f1f1;color:#333}',
        '#pm-modal-box .pm-btn-danger{background:#ef4444;color:#fff}',
        '</style>'
    ].join('');
    document.body.appendChild(el.firstChild);
    document.body.appendChild(el.lastChild);

    document.getElementById('pm-modal-backdrop').addEventListener('click', function() {
        _closeModal(false);
    });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') _closeModal(false);
    });
}

function _closeModal(value) {
    var modal = document.getElementById('pm-modal');
    if (modal) modal.style.display = 'none';
    if (_modalResolve) { _modalResolve(value); _modalResolve = null; }
}

function pmAlert(icon, title, message) {
    _ensureModal();
    document.getElementById('pm-modal-icon').textContent  = icon;
    document.getElementById('pm-modal-title').textContent = title;
    document.getElementById('pm-modal-msg').textContent   = message;
    var btns = document.getElementById('pm-modal-btns');
    btns.innerHTML = '<button class="pm-btn pm-btn-primary" id="pm-ok">OK</button>';
    document.getElementById('pm-modal').style.display = 'flex';
    document.getElementById('pm-ok').focus();
    return new Promise(function(resolve) {
        _modalResolve = resolve;
        document.getElementById('pm-ok').onclick = function() { _closeModal(true); };
    });
}

function pmConfirm(icon, title, message, okLabel, okClass) {
    _ensureModal();
    okClass = okClass || 'pm-btn-primary';
    var cancelLabel = _t('cancel');
    document.getElementById('pm-modal-icon').textContent  = icon;
    document.getElementById('pm-modal-title').textContent = title;
    document.getElementById('pm-modal-msg').textContent   = message;
    var btns = document.getElementById('pm-modal-btns');
    btns.innerHTML = [
        '<button class="pm-btn pm-btn-secondary" id="pm-cancel">' + cancelLabel + '</button>',
        '<button class="pm-btn ' + okClass + '" id="pm-ok">' + (okLabel || 'OK') + '</button>'
    ].join('');
    document.getElementById('pm-modal').style.display = 'flex';
    document.getElementById('pm-ok').focus();
    return new Promise(function(resolve) {
        _modalResolve = resolve;
        document.getElementById('pm-ok').onclick     = function() { _closeModal(true); };
        document.getElementById('pm-cancel').onclick = function() { _closeModal(false); };
    });
}

// ── Terracotta theme: day selector ────────────────────────────────────────────

function tcSelectDay(index) {
    document.querySelectorAll('.tc-day-btn').forEach(function(btn, i) {
        btn.classList.toggle('tc-day-active', i === index);
    });
    var card = document.querySelector('.tc-card[data-day-index="' + index + '"]');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Category dropdown ─────────────────────────────────────────────────────────

// Default categories (fallback if API fails)
var DEFAULT_CATEGORIES = [
    { value: 'Quick Dinners', i18n_key: 'quick_dinners' },
    { value: 'Pasta & Noodles', i18n_key: 'pasta_noodles' },
    { value: 'Chicken', i18n_key: 'chicken' },
    { value: 'Ground Meat & Sausages', i18n_key: 'ground_meat' },
    { value: 'Fish & Seafood', i18n_key: 'fish_seafood' },
    { value: 'Taco & Tex-Mex', i18n_key: 'taco_texmex' },
    { value: 'Grill', i18n_key: 'grill' },
    { value: 'Soups & Stews', i18n_key: 'soups_stews' },
    { value: 'Vegetarian', i18n_key: 'vegetarian' },
    { value: 'Homemade', i18n_key: 'homemade' }
];

async function loadCategories() {
    try {
        var resp = await fetch('/api/categories');
        if (!resp.ok) throw new Error('Failed to load categories');
        var cats = await resp.json();
        renderCategories(cats);
    } catch (err) {
        console.error('Error loading categories:', err);
        // Fallback to default categories
        renderCategories(DEFAULT_CATEGORIES);
    }
}

function renderCategories(cats) {
    var container = document.getElementById('dynamicCategoriesList');
    if (!container) return;
    container.innerHTML = '';

    // Get saved categories
    var saved = localStorage.getItem('selectedCategories');
    var savedCats = saved ? JSON.parse(saved) : ['Quick Dinners', 'Pasta & Noodles', 'Chicken', 'Ground Meat & Sausages', 'Fish & Seafood'];

    // Handle both array and object with 'categories' key
    var catList = Array.isArray(cats) ? cats : (cats.categories || []);

    catList.forEach(function(cat) {
        var label = document.createElement('label');
        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        // Use name_en as the value (the English category name for the menu generator)
        var categoryValue = cat.name_en || cat.name || cat.value || '';
        checkbox.value = categoryValue;
        checkbox.checked = savedCats.includes(categoryValue);

        // Display the translated name with icon
        var displayName = cat.name || cat.name_en || categoryValue;
        var icon = cat.icon || '';
        label.appendChild(checkbox);
        if (icon) {
            label.appendChild(document.createTextNode(' ' + icon + ' '));
        } else {
            label.appendChild(document.createTextNode(' '));
        }
        label.appendChild(document.createTextNode(displayName));
        container.appendChild(label);
    });
}

function toggleCategoryDropdown(event) {
    event.stopPropagation();
    var menu = document.getElementById('categoryDropdownMenu');
    if (menu) menu.classList.toggle('open');
}

document.addEventListener('click', function(e) {
    var wrapper = document.getElementById('categoryDropdownWrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        var menu = document.getElementById('categoryDropdownMenu');
        if (menu) menu.classList.remove('open');
    }
});

function getSelectedCategories() {
    var saved = localStorage.getItem('selectedCategories');
    if (saved) {
        try { return JSON.parse(saved); } catch(e) {}
    }
    var selected = [];
    document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
        if (cb.checked) selected.push(cb.value);
    });
    return selected;
}

function applyCategories() {
    var cats = [];
    document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
        if (cb.checked) cats.push(cb.value);
    });
    localStorage.setItem('selectedCategories', JSON.stringify(cats));

    var menu = document.getElementById('categoryDropdownMenu');
    if (menu) menu.classList.remove('open');

    pmAlert('✅', _t('categories_saved_title'), _t('categories_saved_msg'));
}

// ── Menu generation ───────────────────────────────────────────────────────────

function refreshMenu() {
    var categories = getSelectedCategories();

    if (categories.length === 0) {
        pmAlert('⚠️', _t('no_category_title'), _t('no_category_msg'));
        return;
    }

    pmConfirm(
        '🍽️',
        _t('generate_confirm_title'),
        _t('generate_confirm_msg'),
        _t('generate_label'),
        'pm-btn-primary'
    ).then(function(confirmed) {
        if (!confirmed) return;

        var navLink = document.querySelector('a[onclick="refreshMenu()"]');
        if (navLink) { navLink.textContent = _t('generating'); navLink.style.opacity = '.6'; }

        fetch('/api/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ categories: categories })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'success') {
                pmAlert('✅', _t('menu_ready'), _t('menu_updated')).then(function() {
                    // Ensure language cookie is synced before reload
                    var stored = localStorage.getItem('menu-planner-language');
                    if (stored) {
                        document.cookie = 'pi_language=' + stored + '; path=/; max-age=31536000; SameSite=Lax';
                    }
                    location.reload();
                });
            } else {
                pmAlert('❌', _t('generation_failed'), _t('generation_error') + ': ' + (data.message || ''));
                if (navLink) { navLink.textContent = _t('generate_menu'); navLink.style.opacity = ''; }
            }
        })
        .catch(function() {
            pmAlert('❌', _t('server_error'), _t('server_error_msg'));
            if (navLink) { navLink.textContent = _t('generate_menu'); navLink.style.opacity = ''; }
        });
    });
}

// ── Category selection persistence ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    var saved = localStorage.getItem('selectedCategories');
    if (saved) {
        try {
            var selectedCats = JSON.parse(saved);
            document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
                cb.checked = selectedCats.includes(cb.value);
            });
        } catch(e) {}
    }
});

// ── Favorite/Star system ─────────────────────────────────────────────────────

function toggleFavorite(recipeId, btn) {
    var favKey = 'favorite-' + recipeId;
    var isFavorited = localStorage.getItem(favKey) === 'true';

    if (isFavorited) {
        localStorage.removeItem(favKey);
        btn.textContent = '☆';
        btn.style.color = '';
    } else {
        localStorage.setItem(favKey, 'true');
        btn.textContent = '★';
        btn.style.color = 'var(--color-primary, #d97706)';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    var favBtn = document.getElementById('favoriteBtn');
    if (favBtn) {
        var match = favBtn.getAttribute('onclick').match(/'([^']+)'/);
        if (match) {
            var recipeId = match[1];
            if (localStorage.getItem('favorite-' + recipeId) === 'true') {
                favBtn.textContent = '★';
                favBtn.style.color = 'var(--color-primary, #d97706)';
            }
        }
    }
});

function getFavoriteRecipes() {
    var favorites = [];
    for (var key in localStorage) {
        if (key.startsWith('favorite-')) {
            favorites.push(key.replace('favorite-', ''));
        }
    }
    return favorites;
}

// ── Settings Menu (Cogwheel) ────────────────────────────────────────────────

function toggleSettingsMenu(event) {
    event.stopPropagation();
    var dropdown = document.getElementById('settings-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
}

function openThemeMenu(event) {
    event.preventDefault();
    event.stopPropagation();
    var submenu = document.getElementById('theme-submenu');
    if (submenu) {
        submenu.style.display = submenu.style.display === 'none' ? 'block' : 'none';
    }
}

function switchTheme(theme, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (window.themeManager) {
        window.themeManager.applyTheme(theme);
        localStorage.setItem('menu-planner-theme', theme);
        window.themeManager.markActiveTheme();
    }
    var dropdown = document.getElementById('settings-dropdown');
    if (dropdown) dropdown.classList.remove('open');
}

document.addEventListener('click', function(e) {
    var settingsMenu = document.querySelector('.nav-settings-menu');
    var dropdown = document.getElementById('settings-dropdown');
    if (settingsMenu && dropdown && !settingsMenu.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// ── Shopping list persistence ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    var checkboxes = document.querySelectorAll('.shopping-checkbox');
    checkboxes.forEach(function(checkbox) {
        var key = 'shopping-' + checkbox.parentElement.textContent.trim();
        checkbox.addEventListener('change', function() {
            localStorage.setItem(key, this.checked);
        });
        if (localStorage.getItem(key) === 'true') {
            checkbox.checked = true;
        }
    });
});

// ── Language switching ────────────────────────────────────────────────────────

function switchLanguage(lang) {
    if (window.languageManager) {
        window.languageManager.setLanguage(lang);
        // Set a cookie so Flask can read it server-side
        document.cookie = 'pi_language=' + lang + '; path=/; max-age=31536000; SameSite=Lax';
        location.reload();
    }
}
