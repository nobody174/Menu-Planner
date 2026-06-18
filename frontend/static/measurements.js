//
// Menu Planner - Weekly Meal Planner
// Creator: nobody174 (nobodylearn174@gmail.com)
// GitHub: https://github.com/nobody174/Menu-Planner
// License: MIT
//

// Measurement conversion table: metric to imperial/US
const UNIT_CONVERSIONS = {
  // Weight
  "g": { "oz": 0.035274, "name_no": "gram", "name_en": "gram" },
  "kg": { "lb": 2.20462, "name_no": "kilogram", "name_en": "kilogram" },

  // Volume
  "ml": { "fl oz": 0.033814, "cup": 0.004227, "tbsp": 0.067628, "tsp": 0.202884, "name_no": "milliliter", "name_en": "milliliter" },
  "dl": { "cup": 0.4227, "tbsp": 6.7628, "tsp": 20.2884, "name_no": "deciliter", "name_en": "deciliter" },
  "l": { "gallon": 0.264172, "cup": 4.227, "tbsp": 67.628, "name_no": "liter", "name_en": "liter" },

  // Teaspoon/Tablespoon (already in US)
  "tsp": { "ml": 4.92892, "name_no": "teskje", "name_en": "teaspoon" },
  "tbsp": { "ml": 14.7868, "name_no": "spiseskje", "name_en": "tablespoon" },
  "cup": { "ml": 236.588, "dl": 2.36588, "name_no": "kopp", "name_en": "cup" },

  // Count
  "stk": { "name_no": "stykk", "name_en": "piece" },
  "fedd": { "name_no": "fedd", "name_en": "clove" }
};

class MeasurementConverter {
  constructor() {
    this.currentLanguage = localStorage.getItem('menu-planner-language') || 'no';
  }

  setLanguage(lang) {
    this.currentLanguage = lang;
  }

  convertUnit(quantity, fromUnit, toUnit) {
    if (fromUnit === toUnit) {
      return { quantity: quantity, unit: fromUnit };
    }

    const conversions = UNIT_CONVERSIONS[fromUnit];
    if (!conversions || !conversions[toUnit]) {
      // Can't convert, return original
      return { quantity: quantity, unit: fromUnit };
    }

    const factor = conversions[toUnit];
    const convertedQuantity = (quantity * factor).toFixed(2);

    return {
      quantity: parseFloat(convertedQuantity),
      unit: toUnit
    };
  }

  getLocalizedUnit(unit) {
    const conversions = UNIT_CONVERSIONS[unit];
    if (!conversions) return unit;

    const key = this.currentLanguage === 'en' ? 'name_en' : 'name_no';
    return conversions[key] || unit;
  }

  formatMeasurement(quantity, unit, language = null) {
    const lang = language || this.currentLanguage;
    const key = lang === 'en' ? 'name_en' : 'name_no';
    const conversions = UNIT_CONVERSIONS[unit];

    if (conversions && conversions[key]) {
      return `${quantity} ${conversions[key]}`;
    }

    return `${quantity} ${unit}`;
  }

  shouldConvertByDefault(unit) {
    // Units that should be converted from metric to imperial by default in English
    const metricUnits = ['g', 'kg', 'ml', 'dl', 'l'];
    return this.currentLanguage === 'en' && metricUnits.includes(unit);
  }
}

// Global instance
window.measurementConverter = new MeasurementConverter();

// Listen for language changes
window.addEventListener('languageChanged', (event) => {
  if (window.measurementConverter) {
    window.measurementConverter.setLanguage(event.detail.language);
  }
});
