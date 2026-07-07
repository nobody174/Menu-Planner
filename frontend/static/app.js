// ── CSRF protection (added 2026-07-05) ────────────────────────────────────────
// Wrap the global fetch() so every same-origin, state-changing request
// (POST/PUT/PATCH/DELETE) automatically carries the X-CSRFToken header that
// Flask-WTF's CSRFProtect checks server-side. This covers the whole app's
// existing fetch() calls without needing to edit each one individually.
(function() {
    var originalFetch = window.fetch;
    var CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function isSameOrigin(url) {
        try {
            return new URL(url, window.location.href).origin === window.location.origin;
        } catch (e) {
            return true; // relative URLs resolve fine above; default to same-origin
        }
    }

    window.fetch = function(input, init) {
        init = init || {};
        var method = (init.method || 'GET').toUpperCase();
        var url = typeof input === 'string' ? input : (input && input.url) || '';

        if (CSRF_METHODS.indexOf(method) !== -1 && isSameOrigin(url)) {
            init.headers = init.headers || {};
            if (init.headers instanceof Headers) {
                init.headers.set('X-CSRFToken', getCsrfToken());
            } else {
                init.headers['X-CSRFToken'] = getCsrfToken();
            }
        }
        return originalFetch.call(this, input, init);
    };
})();

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

// Themed replacement for the browser's native prompt(). Resolves with the
// entered text, or null if cancelled - same contract as window.prompt(), so
// existing `var x = prompt(...); if (x) {...}` call sites only need to
// become `pmPrompt(...).then(function(x) { if (x) {...} })`.
function pmPrompt(icon, title, message, defaultValue, okLabel) {
    _ensureModal();
    var cancelLabel = _t('cancel');
    document.getElementById('pm-modal-icon').textContent  = icon;
    document.getElementById('pm-modal-title').textContent = title;
    document.getElementById('pm-modal-msg').textContent   = message || '';
    document.getElementById('pm-modal-msg').style.display = message ? '' : 'none';
    var btns = document.getElementById('pm-modal-btns');
    btns.innerHTML = [
        '<input type="text" id="pm-prompt-input" value="" autocomplete="off"',
        '  style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:9px;font-size:.95rem;margin-bottom:14px;box-sizing:border-box;order:-1;flex-basis:100%;">',
        '<button class="pm-btn pm-btn-secondary" id="pm-cancel">' + cancelLabel + '</button>',
        '<button class="pm-btn pm-btn-primary" id="pm-ok">' + (okLabel || 'OK') + '</button>'
    ].join('');
    var input = document.getElementById('pm-prompt-input');
    input.value = defaultValue || '';
    document.getElementById('pm-modal').style.display = 'flex';
    input.focus();
    input.select();

    return new Promise(function(resolve) {
        _modalResolve = resolve;
        function submit() { _closeModal(input.value); }
        document.getElementById('pm-ok').onclick     = submit;
        document.getElementById('pm-cancel').onclick = function() { _closeModal(null); };
        input.onkeydown = function(e) { if (e.key === 'Enter') submit(); };
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

    // Handle both array and object with 'categories' key
    var catList = Array.isArray(cats) ? cats : (cats.categories || []);

    // Get saved categories, but validate them against what actually exists in
    // the current pack structure - stale saved values from a previous pack
    // scheme would match nothing and generate an empty menu.
    var saved = localStorage.getItem('selectedCategories');
    var savedCats = saved ? JSON.parse(saved) : [];
    var availableValues = catList.map(function(c) { return c.name_en || c.name || c.value || ''; });
    var validSaved = savedCats.filter(function(c) { return availableValues.indexOf(c) !== -1; });

    // If nothing saved, or saved list is entirely stale, use a sensible default.
    if (validSaved.length === 0) {
        validSaved = ['Fish & Seafood', 'Soups & Stews', 'Beef & Red Meat', 'Chicken', 'Pasta & Noodles'];
    }
    var savedCats = validSaved;

    catList.forEach(function(cat) {
        var label = document.createElement('label');
        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        // Use name_en as the value (the English category name for the menu generator)
        var categoryValue = cat.name_en || cat.name || cat.value || '';
        checkbox.value = categoryValue;
        checkbox.checked = savedCats.includes(categoryValue);
        // Ticking a category IS the "select it" action - saving on every
        // change means there's nothing left for a separate "Apply" button
        // to do, so checking a box takes effect immediately instead of
        // requiring a second confirm click.
        checkbox.addEventListener('change', applyCategories);

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
    // No more explicit "Apply" button - this now fires on every checkbox/day
    // count change instead (see the .addEventListener('change', ...) calls
    // above and below), so ticking a category saves it immediately rather
    // than requiring a separate confirm click. Deliberately does NOT close
    // the dropdown anymore, since the user is likely still ticking more
    // boxes - it closes normally via the existing outside-click handler
    // once they're done.
    var cats = [];
    document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
        if (cb.checked) cats.push(cb.value);
    });
    localStorage.setItem('selectedCategories', JSON.stringify(cats));

    var daySelect = document.getElementById('dayCountSelect');
    if (daySelect) localStorage.setItem('selectedDayCount', daySelect.value);
}

function getSelectedDayCount() {
    var saved = localStorage.getItem('selectedDayCount');
    var n = saved ? parseInt(saved, 10) : 6;
    return (n >= 1 && n <= 6) ? n : 6;
}

document.addEventListener('DOMContentLoaded', function() {
    var daySelect = document.getElementById('dayCountSelect');
    if (daySelect) {
        daySelect.value = String(getSelectedDayCount());
        // Same as the category checkboxes above - changing the day count
        // saves immediately instead of waiting for a separate "Apply" click.
        daySelect.addEventListener('change', applyCategories);
    }
});

// B53: show the "generated a shorter menu than requested" notice, if any,
// left behind by refreshMenu() before its redirect. Shown once, then
// cleared - a manual reload of the dashboard won't keep re-showing it.
// Both dashboard layouts (standard + rich/warm-terracotta) have their own
// copy of this banner markup (only one is visible per theme at a time), so
// this populates whichever one(s) actually exist in the current layout.
document.addEventListener('DOMContentLoaded', function() {
    var raw = sessionStorage.getItem('menu-shortfall-warning');
    sessionStorage.removeItem('menu-shortfall-warning');
    if (!raw) return;

    var warning;
    try { warning = JSON.parse(raw); } catch (e) { return; }
    if (!warning || !warning.actual_dinners || !warning.requested_dinners) return;

    var text = _t('generate_shortfall_msg')
        .replace(/\{actual\}/g, warning.actual_dinners)
        .replace(/\{requested\}/g, warning.requested_dinners);

    [
        { banner: 'shortfall-banner', text: 'shortfall-banner-text', dismiss: 'shortfall-banner-dismiss' },
        { banner: 'shortfall-banner-rich', text: 'shortfall-banner-rich-text', dismiss: 'shortfall-banner-rich-dismiss' }
    ].forEach(function(ids) {
        var banner = document.getElementById(ids.banner);
        if (!banner) return;
        document.getElementById(ids.text).textContent = text;
        banner.style.display = 'flex';
        var dismiss = document.getElementById(ids.dismiss);
        if (dismiss) dismiss.onclick = function() { banner.style.display = 'none'; };
    });
});

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
            body: JSON.stringify({ categories: categories, favorite_recipe_ids: getFavoriteRecipes(), num_dinners: getSelectedDayCount() })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'success') {
                // B53: if fewer recipes matched than requested, the menu was
                // generated short rather than failing outright - stash the
                // warning so it survives the redirect below and shows once
                // as a dismissible banner on the dashboard.
                if (data.warning) {
                    try {
                        sessionStorage.setItem('menu-shortfall-warning', JSON.stringify(data.warning));
                    } catch (e) { /* sessionStorage unavailable - skip silently */ }
                }
                // Redirect to main page to show newly generated menu
                var stored = localStorage.getItem('menu-planner-language');
                if (stored) {
                    document.cookie = 'pi_language=' + stored + '; path=/; max-age=31536000; SameSite=Lax';
                }
                location.href = '/';
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
        var opening = !dropdown.classList.contains('open');
        dropdown.classList.toggle('open');
        if (opening) {
            // A fixed CSS max-height can't know how far down the button
            // actually sits (varies by theme/viewport), so the dropdown's
            // bottom could still render past the visible screen with no way
            // to reach it. Cap it to the real remaining space instead.
            var rect = dropdown.getBoundingClientRect();
            var available = window.innerHeight - rect.top - 12;
            dropdown.style.maxHeight = Math.max(120, available) + 'px';

            // The dropdown is right-aligned to its button by default
            // (CSS `right: 0`), expanding leftward - fine when the button
            // sits on the right side of the nav, but if the button ends up
            // near the left edge (narrow viewport, wrapped nav, browser
            // zoom/text scaling), that leftward expansion runs off the left
            // of the screen with no way to reach those items either. Clamp
            // it back onto the screen if that happens.
            if (rect.left < 8) {
                dropdown.style.right = 'auto';
                dropdown.style.left = '8px';
            } else {
                dropdown.style.right = '';
                dropdown.style.left = '';
            }
        }
    }
}

function toggleSettingsSubmenu(submenuId, event) {
    event.preventDefault();
    event.stopPropagation();
    var submenu = document.getElementById(submenuId);
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
