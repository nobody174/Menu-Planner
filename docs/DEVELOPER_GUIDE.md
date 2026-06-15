# Pi-Menu Developer Guide

This guide is for developers who want to contribute to Pi-Menu or extend it with custom features.

## Project Structure

```
Pi-Menu-Public/
├── core/                     # Core application logic
│   ├── __init__.py
│   ├── error_handler.py      # Centralized error handling
│   ├── ingredient_deduplicator.py
│   ├── menu_generator.py
│   ├── pantry_staples.json
│   └── todo_sync.py
├── pi-deployment/            # Flask web application
│   ├── app.py               # Entry point
│   ├── flask_app.py         # Routes & API endpoints
│   ├── auth.py              # Microsoft authentication
│   ├── email_notifier.py
│   └── scheduler.py
├── frontend/                 # Web interface
│   ├── static/
│   │   ├── app.js           # Main application logic
│   │   ├── style.css        # Styling
│   │   ├── i18n.json        # Translations
│   │   ├── language-manager.js
│   │   ├── measurements.js
│   │   ├── manifest.json    # PWA manifest
│   │   ├── sw.js            # Service worker
│   │   └── themes/          # Theme files
│   └── templates/           # Jinja2 templates
├── scripts/                  # Utility scripts
│   ├── pi-menu-cli.py       # CLI interface
│   ├── category-editor.py   # Category management
│   ├── import_recipes.py    # Recipe importer
│   └── test-local.py        # Local test suite
├── data/                     # Application data
│   ├── sample_recipes.json
│   ├── categories.json
│   └── weekly_menu.json
├── docs/                     # Documentation
├── config.py                # Configuration
├── requirements.txt          # Python dependencies
└── README.md
```

## Development Setup

### 1. Clone & Environment

```bash
git clone https://github.com/nobody174/Pi-Menu-Public.git
cd Pi-Menu-Public
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.template .env
# Edit .env with your settings (optional for local dev)
```

### 3. Run Locally

```bash
python3 pi-deployment/app.py
# Open http://localhost:5000
```

## Architecture

### Menu Generation Pipeline

```
1. Load recipes from JSON
   ↓
2. Filter by category & allergens
   ↓
3. Select 5-6 recipes with variety
   ↓
4. Deduplicate ingredients
   ↓
5. Categorize by type
   ↓
6. Save to weekly_menu.json
```

### Data Flow

```
Frontend (HTML/JS)
     ↓
Flask Routes (pi-deployment/flask_app.py)
     ↓
Core Logic (core/)
     ↓
Data Files (data/*.json)
```

## Key Modules

### MenuGenerator (core/menu_generator.py)

Generates weekly menus from recipes.

```python
from core.menu_generator import MenuGenerator

gen = MenuGenerator(selected_categories=['familie', 'rask'])
gen.load_recipes()
gen.filter_recipes()
menu = gen.generate_menu(num_dinners=5)
menu.save()
```

### ErrorHandler (core/error_handler.py)

Centralized error handling with custom exceptions.

```python
from core.error_handler import (
    PIMenuError, RecipeLoadError,
    handle_error, validate_recipe
)

try:
    # Your code
except PIMenuError as e:
    result = handle_error(e, "context")
```

### LanguageManager (frontend/static/language-manager.js)

Client-side language switching.

```javascript
window.languageManager.setLanguage('en');
window.languageManager.applyLanguage();
const text = window.languageManager.t('menu_en');
```

### MeasurementConverter (frontend/static/measurements.js)

Unit conversion (metric ↔ imperial).

```javascript
const converted = window.measurementConverter.convertUnit(
    500, 'g', 'oz'
);  // {quantity: 17.64, unit: 'oz'}
```

## Common Tasks

### Add a New API Endpoint

1. Add route in `pi-deployment/flask_app.py`:

```python
@app.route('/api/my-endpoint')
def my_endpoint():
    try:
        data = request.get_json()
        # Process
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

2. Call from frontend:

```javascript
fetch('/api/my-endpoint', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({key: 'value'})
})
.then(r => r.json())
.then(data => console.log(data));
```

### Add a Translation

1. Edit `frontend/static/i18n.json`:

```json
{
  "my_key_no": "Norsk tekst",
  "my_key_en": "English text"
}
```

2. Use in template:

```html
<span data-i18n="my_key">Loading...</span>
```

Or in JavaScript:

```javascript
const text = window.languageManager.t('my_key');
```

### Add a New Category

Option 1: CLI tool

```bash
python3 scripts/category-editor.py --add
```

Option 2: Edit `data/categories.json` directly:

```json
{
  "code": "new-category",
  "name_no": "Ny Kategori",
  "name_en": "New Category",
  "icon": "🍕",
  "color": "#FF6B6B"
}
```

### Add Sample Recipes

Edit `data/sample_recipes.json` or import via Excel:

```bash
python3 scripts/import_recipes.py your_recipes.xlsx
```

## Testing

### Run Local Test Suite

```bash
python3 scripts/test-local.py
```

Tests:
- Configuration loading
- Recipe & category loading
- Menu generation
- Language manager
- Measurement conversion
- Error handling
- Static assets

### Manual Testing

```bash
# List recipes
python3 scripts/pi-menu-cli.py recipes list

# Count recipes
python3 scripts/pi-menu-cli.py recipes count

# Validate config
python3 scripts/pi-menu-cli.py validate

# Generate menu
python3 scripts/pi-menu-cli.py menu generate
```

## Code Style

### Python

- PEP 8 compliant
- Type hints for new code
- Docstrings for public functions
- Error handling with custom exceptions

### JavaScript

- Vanilla JS (no frameworks)
- Camel case for functions/variables
- Comments for complex logic

### HTML/CSS

- Semantic HTML
- BEM-like class naming
- CSS custom properties for theming
- Mobile-first responsive design

## Debugging

### Enable Debug Mode

Edit `pi-deployment/flask_app.py`:

```python
app.config['DEBUG'] = True
```

### Check Logs

```bash
tail -f logs/flask_app.log
tail -f logs/pi-menu.log
```

### Browser Console

Press F12 to open developer tools and check:
- Console for JavaScript errors
- Network tab for API calls
- Application tab for localStorage

## Git Workflow

1. Create feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make changes and test:
   ```bash
   python3 scripts/test-local.py
   ```

3. Commit with clear message:
   ```bash
   git commit -m "feature: add new feature

   Description of what was added.
   Why it's useful.
   ```

4. Push and create PR:
   ```bash
   git push origin feature/my-feature
   ```

## Performance Tips

1. **Lazy load data**: Load recipes only when needed
2. **Cache JSON**: Use localStorage for categories, language
3. **Minimize API calls**: Batch requests when possible
4. **Optimize images**: Keep theme images small
5. **Use service worker**: Already implemented for offline support

## Security Checklist

- [ ] No hardcoded credentials
- [ ] Environment variables for secrets
- [ ] Input validation on forms
- [ ] SQL injection prevention (N/A - no DB)
- [ ] XSS prevention (escape HTML)
- [ ] CSRF tokens on POST
- [ ] HTTPS in production

## Deployment

### Development
```bash
python3 pi-deployment/app.py
```

### Production (Raspberry Pi)
```bash
# Create systemd service
sudo systemctl enable pi-menu
sudo systemctl start pi-menu
```

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions
- **Code Comments**: Complex logic needs explanation
- **Documentation**: Keep docs up-to-date

## Contribution Checklist

- [ ] Tests pass locally
- [ ] Code follows style guide
- [ ] No hardcoded secrets
- [ ] Documentation updated
- [ ] Commit message is clear

## Useful Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [Git Workflow](https://git-scm.com/book/en/v2)

---

Happy coding! 🍽️
