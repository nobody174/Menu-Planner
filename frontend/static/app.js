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
    document.getElementById('pm-modal-icon').textContent  = icon;
    document.getElementById('pm-modal-title').textContent = title;
    document.getElementById('pm-modal-msg').textContent   = message;
    var btns = document.getElementById('pm-modal-btns');
    btns.innerHTML = [
        '<button class="pm-btn pm-btn-secondary" id="pm-cancel">Avbryt</button>',
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
    document.querySelectorAll('.tc-day-btn').forEach((btn, i) => {
        btn.classList.toggle('tc-day-active', i === index);
    });
    const card = document.querySelector(`.tc-card[data-day-index="${index}"]`);
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Category dropdown ─────────────────────────────────────────────────────────

function toggleCategoryDropdown(event) {
    event.stopPropagation();
    const menu = document.getElementById('categoryDropdownMenu');
    if (menu) menu.classList.toggle('open');
}

document.addEventListener('click', function(e) {
    const wrapper = document.getElementById('categoryDropdownWrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        const menu = document.getElementById('categoryDropdownMenu');
        if (menu) menu.classList.remove('open');
    }
});

function getSelectedCategories() {
    // Try localStorage first, fall back to current checkboxes
    var saved = localStorage.getItem('selectedCategories');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch(e) {}
    }
    var selected = [];
    document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
        if (cb.checked) selected.push(cb.value);
    });
    return selected;
}

function applyCategories() {
    // Save selected categories to localStorage, then close dropdown
    var cats = [];
    document.querySelectorAll('#categoryDropdownMenu input[type="checkbox"]').forEach(function(cb) {
        if (cb.checked) cats.push(cb.value);
    });
    localStorage.setItem('selectedCategories', JSON.stringify(cats));

    var menu = document.getElementById('categoryDropdownMenu');
    if (menu) menu.classList.remove('open');

    pmAlert('✅', 'Kategorier lagret', 'Valgte kategorier er lagret. Velg "Generer ny meny" når du er klar.');
}

// ── Menu generation ───────────────────────────────────────────────────────────

function refreshMenu() {
    const categories = getSelectedCategories();
    console.log('Regenerating with categories:', categories);

    if (categories.length === 0) {
        pmAlert('⚠️', 'Ingen kategori valgt', 'Velg minst én kategori før du genererer ny meny.');
        return;
    }

    pmConfirm(
        '🍽️',
        'Generer ny ukemeny?',
        'Dette vil erstatte den eksisterende menyen med nye oppskrifter.',
        'Generer',
        'pm-btn-primary'
    ).then(function(confirmed) {
        if (!confirmed) return;

        var navLink = document.querySelector('a[onclick="refreshMenu()"]');
        if (navLink) { navLink.textContent = 'Genererer…'; navLink.style.opacity = '.6'; }

        fetch('/api/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ categories: categories })
        })
        .then(r => r.json())
        .then(function(data) {
            if (data.status === 'success') {
                pmAlert('✅', 'Ny meny klar!', 'Ukemenyen er oppdatert med nye oppskrifter.').then(function() {
                    location.reload();
                });
            } else {
                pmAlert('❌', 'Noe gikk galt', 'Feil ved generering: ' + (data.message || 'ukjent feil'));
                if (navLink) { navLink.textContent = 'Generer ny meny'; navLink.style.opacity = ''; }
            }
        })
        .catch(function() {
            pmAlert('❌', 'Serverfeil', 'Kunne ikke kontakte serveren. Prøv igjen.');
            if (navLink) { navLink.textContent = 'Generer ny meny'; navLink.style.opacity = ''; }
        });
    });
}

// ── Category selection persistence ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    // Load saved category selection
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
    const favKey = 'favorite-' + recipeId;
    const isFavorited = localStorage.getItem(favKey) === 'true';

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
    // Restore favorite star state
    const favBtn = document.getElementById('favoriteBtn');
    if (favBtn) {
        const recipeId = favBtn.getAttribute('onclick').match(/'([^']+)'/)[1];
        if (localStorage.getItem('favorite-' + recipeId) === 'true') {
            favBtn.textContent = '★';
            favBtn.style.color = 'var(--color-primary, #d97706)';
        }
    }
});

function getFavoriteRecipes() {
    const favorites = [];
    for (let key in localStorage) {
        if (key.startsWith('favorite-')) {
            favorites.push(key.replace('favorite-', ''));
        }
    }
    return favorites;
}

// ── Settings Menu (Cogwheel) ────────────────────────────────────────────────

function toggleSettingsMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('settings-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
}

function openThemeMenu(event) {
    event.preventDefault();
    event.stopPropagation();
    const submenu = document.getElementById('theme-submenu');
    if (submenu) {
        submenu.style.display = submenu.style.display === 'none' ? 'block' : 'none';
    }
}

function switchTheme(theme, event) {
    event.preventDefault();
    event.stopPropagation();
    // Trigger theme change through existing theme manager if available
    const themeOption = document.querySelector(`.theme-option[data-theme="${theme}"]`);
    if (themeOption) {
        themeOption.click && themeOption.click();
    }
    // Close menu after selection
    document.getElementById('settings-dropdown').classList.remove('open');
}

// Close settings menu when clicking outside
document.addEventListener('click', function(e) {
    const settingsMenu = document.querySelector('.nav-settings-menu');
    const dropdown = document.getElementById('settings-dropdown');
    if (settingsMenu && dropdown && !settingsMenu.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// ── Shopping list persistence ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('.shopping-checkbox');
    checkboxes.forEach(checkbox => {
        const key = 'shopping-' + checkbox.parentElement.textContent.trim();
        checkbox.addEventListener('change', function() {
            localStorage.setItem(key, this.checked);
        });
        if (localStorage.getItem(key) === 'true') {
            checkbox.checked = true;
        }
    });
});
