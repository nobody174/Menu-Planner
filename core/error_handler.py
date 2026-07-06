#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

"""
Centralized Error Handling & Logging

Provides consistent error handling across the application.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MenuPlannerError(Exception):
    """Base exception for Menu Planner"""

    def __init__(self, message: str, code: str = "UNKNOWN", details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)


class RecipeLoadError(MenuPlannerError):
    """Error loading recipes"""

    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "RECIPE_LOAD_ERROR", details)


class CategoryLoadError(MenuPlannerError):
    """Error loading categories"""

    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "CATEGORY_LOAD_ERROR", details)


class MenuGenerationError(MenuPlannerError):
    """Error generating menu"""

    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "MENU_GENERATION_ERROR", details)


class ValidationError(MenuPlannerError):
    """Data validation error"""

    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)


def handle_error(
    error: Exception, context: str = "", log_level: str = "error"
) -> Dict[str, Any]:
    """
    Centralized error handler.

    Args:
        error: The exception to handle
        context: Context about where the error occurred
        log_level: Logging level (error, warning, info)

    Returns:
        JSON-serializable error dict
    """
    log_func = getattr(logger, log_level.lower(), logger.error)

    if isinstance(error, MenuPlannerError):
        log_func(f"{context}: {error.code} - {error.message}")
        return {
            "status": "error",
            "code": error.code,
            "message": error.message,
            "details": error.details,
            "timestamp": error.timestamp,
        }
    else:
        error_msg = str(error)
        log_func(f"{context}: {error.__class__.__name__} - {error_msg}")
        return {
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"error_type": error.__class__.__name__},
            "timestamp": datetime.now().isoformat(),
        }


def validate_recipe(recipe: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate recipe structure.

    Returns:
        (is_valid, error_message)
    """
    required_fields = ["id", "title_no", "title_en", "category"]
    for field in required_fields:
        if field not in recipe or not recipe[field]:
            return False, f"Missing required field: {field}"

    if not isinstance(recipe.get("ingredients_included", []), list):
        return False, "ingredients_included must be a list"

    return True, None


def validate_category(category: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate category structure.

    Returns:
        (is_valid, error_message)
    """
    required_fields = ["code", "name_no", "name_en"]
    for field in required_fields:
        if field not in category or not category[field]:
            return False, f"Missing required field: {field}"

    return True, None


def safe_load_json(file_path: Path, default: Any = None) -> Any:
    """
    Safely load JSON file with error handling.

    Returns:
        Parsed JSON or default value if error
    """
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return default

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default


def safe_save_json(file_path: Path, data: Any) -> bool:
    """
    Safely save JSON file with error handling.

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False
