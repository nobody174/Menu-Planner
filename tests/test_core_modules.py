import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_error_handler_imports():
    """Test that error handler module imports successfully"""
    from core.error_handler import MenuPlannerError, RecipeLoadError, CategoryLoadError
    assert MenuPlannerError is not None
    assert RecipeLoadError is not None
    assert CategoryLoadError is not None

def test_menu_generator_imports():
    """Test that menu generator module imports successfully"""
    from core.menu_generator import MenuGenerator
    assert MenuGenerator is not None

def test_ingredient_deduplicator_imports():
    """Test that ingredient deduplicator module imports successfully"""
    from core.ingredient_deduplicator import IngredientDeduplicator
    assert IngredientDeduplicator is not None

def test_json_files_valid():
    """Test that all JSON data files are valid"""
    import json

    json_files = [
        'data/sample_recipes.json',
        'data/categories.json',
        'frontend/static/i18n.json',
        'frontend/static/themes/previews/theme-registry.json',
        'pantry_staples.json'
    ]

    for json_file in json_files:
        with open(PROJECT_ROOT / json_file, encoding='utf-8') as f:
            data = json.load(f)
            assert data is not None, f"{json_file} should not be empty"

def test_theme_registry_completeness():
    """Test that theme registry has all required themes"""
    import json

    with open(PROJECT_ROOT / 'frontend/static/themes/previews/theme-registry.json', encoding='utf-8') as f:
        registry = json.load(f)

    assert len(registry) == 9, "Should have 9 themes"
    required_fields = ['id', 'name', 'file', 'preview_color']

    for theme in registry:
        for field in required_fields:
            assert field in theme, f"Theme {theme.get('id')} missing field {field}"

def test_i18n_translations_paired():
    """Test that i18n translations are properly paired (EN/NO)"""
    import json

    with open(PROJECT_ROOT / 'frontend/static/i18n.json', encoding='utf-8') as f:
        i18n = json.load(f)

    base_keys = set()
    for key in i18n.keys():
        if key.endswith('_en'):
            base_keys.add(key[:-3])
        elif key.endswith('_no'):
            base_keys.add(key[:-3])

    for key in base_keys:
        assert f'{key}_en' in i18n, f"Missing English translation for {key}"
        assert f'{key}_no' in i18n, f"Missing Norwegian translation for {key}"
