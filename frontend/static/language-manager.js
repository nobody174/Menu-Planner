//
// Pi-Menu - Weekly Meal Planner
// Creator: nobody174 (nobodylearn174@gmail.com)
// GitHub: https://github.com/nobody174/Pi-Menu-Public
// License: MIT
//

class LanguageManager {
    constructor(defaultLanguage = 'en') {
        this.defaultLanguage = defaultLanguage;
        this.currentLanguage = this.getLanguage();
        this.translations = {};
        this.loadTranslations();
    }

    getLanguage() {
        const stored = localStorage.getItem('pi-menu-language');
        return stored || this.defaultLanguage;
    }

    setLanguage(lang) {
        if (lang === 'no' || lang === 'en') {
            localStorage.setItem('pi-menu-language', lang);
            this.currentLanguage = lang;
            return true;
        }
        return false;
    }

    async loadTranslations() {
        try {
            const response = await fetch('/static/i18n.json');
            if (response.ok) {
                this.translations = await response.json();
            }
        } catch (error) {
            console.error('Failed to load translations:', error);
        }
    }

    t(key, lang = null) {
        const langToUse = lang || this.currentLanguage;
        const fullKey = `${key}_${langToUse}`;
        return this.translations[fullKey] || key;
    }

    getAll(lang = null) {
        const langToUse = lang || this.currentLanguage;
        const result = {};
        for (let [key, value] of Object.entries(this.translations)) {
            if (key.endsWith(`_${langToUse}`)) {
                const baseKey = key.replace(`_${langToUse}`, '');
                result[baseKey] = value;
            }
        }
        return result;
    }

    applyLanguage(lang = null) {
        const langToUse = lang || this.currentLanguage;
        document.documentElement.lang = langToUse;

        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translated = this.t(key, langToUse);
            if (element.tagName === 'INPUT' && element.type === 'placeholder') {
                element.placeholder = translated;
            } else if (element.tagName === 'INPUT' && element.type === 'button') {
                element.value = translated;
            } else if (element.tagName === 'IMG' || element.tagName === 'BUTTON') {
                element.alt = translated;
                element.title = translated;
            } else {
                element.textContent = translated;
            }
        });

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: langToUse } }));
    }

    toggleLanguage() {
        const newLang = this.currentLanguage === 'no' ? 'en' : 'no';
        this.setLanguage(newLang);
        this.applyLanguage();
        location.reload();
    }
}

// Global instance
window.languageManager = new LanguageManager();
