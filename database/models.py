from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text, Boolean, Date, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from database.database import Base

# Use String for SQLite compatibility, UUID for PostgreSQL
def create_id_column():
    """Create ID column compatible with both SQLite and PostgreSQL."""
    return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

# Association table for many-to-many relationship between WeeklyMenu and Recipe
menu_recipes = Table(
    'menu_recipes',
    Base.metadata,
    Column('menu_id', String(36), ForeignKey('weekly_menus.id'), primary_key=True),
    Column('recipe_id', String(36), ForeignKey('recipes.id'), primary_key=True),
    Column('day', String(20), primary_key=True)  # Monday, Tuesday, etc.
)

class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Referral tracking (attribution only - no reward logic yet)
    referral_code = Column(String(12), unique=True, nullable=False, index=True)
    referred_by_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    referred_by_code = Column(String(12), nullable=True)  # raw code, survives referrer deletion

    # Optional shared-device PIN: lets the account holder re-select "Owner" from
    # the profile picker with a short PIN instead of the full account password.
    # NULL means no PIN set yet - falls back to requiring the full password.
    pin_hash = Column(String(255), nullable=True)

    # Email confirmation: login is blocked until this is set (see
    # core/auth_helpers.py create_user/confirm_email). NULL = not yet
    # confirmed. email_confirmation_token is cleared once used, so a stale
    # token can't be replayed after confirmation already happened.
    email_confirmed_at = Column(DateTime, nullable=True)
    email_confirmation_token = Column(String(64), nullable=True, index=True)

    # Password reset: token is set when user requests a reset, cleared once used.
    password_reset_token = Column(String(64), nullable=True, index=True)
    password_reset_requested_at = Column(DateTime, nullable=True)

    # Relationships
    households = relationship('Household', back_populates='owner')
    household_members = relationship('HouseholdMember', back_populates='user')

    def __repr__(self):
        return f'<User {self.email}>'


class Household(Base):
    __tablename__ = 'households'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    owner_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unused (servings-based shopping list scaling was removed 2026-06-30 -
    # households just edit a recipe's own ingredient list if they need to
    # adjust quantities). Column kept rather than dropped to avoid an extra
    # migration; safe to ignore.
    default_servings = Column(Integer, default=4, nullable=False)

    # JSONB columns for household data storage (replaces file-based storage)
    recipes_db = Column(JSON, nullable=True)
    pantry = Column(JSON, nullable=True)
    weekly_menu = Column(JSON, nullable=True)
    categories = Column(JSON, nullable=True)
    activity_log = Column(JSON, nullable=True)
    removed_categories = Column(JSON, nullable=True)
    imported_packs = Column(JSON, nullable=True)

    # Relationships
    owner = relationship('User', back_populates='households')
    members = relationship('HouseholdMember', back_populates='household', cascade='all, delete-orphan')
    recipes = relationship('Recipe', back_populates='household', cascade='all, delete-orphan')
    menus = relationship('WeeklyMenu', back_populates='household', cascade='all, delete-orphan')
    shopping_lists = relationship('ShoppingList', back_populates='household', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Household {self.name}>'


class HouseholdMember(Base):
    __tablename__ = 'household_members'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id = Column(String(36), ForeignKey('households.id'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)  # NULL for profiles (no own login)
    role = Column(String(50), default='viewer', nullable=False)  # owner, editor, viewer
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Profile fields (used when user_id is NULL - a "Netflix-style" profile under an account holder)
    is_profile = Column(Boolean, default=False, nullable=False)
    display_name = Column(String(100), nullable=True)  # shown for profiles instead of User.email
    avatar_type = Column(String(20), nullable=True)  # 'preset', 'upload', or NULL
    avatar_value = Column(String(500), nullable=True)  # preset filename or uploaded image path/URL

    # Relationships
    household = relationship('Household', back_populates='members')
    user = relationship('User', back_populates='household_members')

    def __repr__(self):
        label = self.display_name if self.is_profile else self.user_id
        return f'<HouseholdMember {label} in {self.household_id}>'


class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id = Column(String(36), ForeignKey('households.id'), nullable=True)  # NULL = public recipes
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), default='Easy', nullable=False)
    time_minutes = Column(Integer, default=30, nullable=False)
    category = Column(String(100), nullable=True)
    instructions = Column(JSON, nullable=True)  # Array of instruction strings
    comment = Column(Text, nullable=True)
    allergens = Column(JSON, nullable=True)  # Array of allergen strings
    created_by = Column(String(36), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    household = relationship('Household', back_populates='recipes')
    ingredients = relationship('RecipeIngredient', back_populates='recipe', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Recipe {self.title}>'

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            'id': str(self.id),
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'difficulty': self.difficulty,
            'time_minutes': self.time_minutes,
            'category': self.category,
            'instructions': self.instructions or [],
            'comment': self.comment or '',
            'allergens': self.allergens or [],
            'ingredients': [ing.to_dict() for ing in self.ingredients]
        }


class RecipeIngredient(Base):
    __tablename__ = 'recipe_ingredients'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipe_id = Column(String(36), ForeignKey('recipes.id'), nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Float, default=0, nullable=False)
    unit = Column(String(50), nullable=True)
    allergens = Column(JSON, nullable=True)  # Array of allergen strings

    # Relationships
    recipe = relationship('Recipe', back_populates='ingredients')

    def __repr__(self):
        return f'<RecipeIngredient {self.name}>'

    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'unit': self.unit,
            'allergens': self.allergens or []
        }


class WeeklyMenu(Base):
    __tablename__ = 'weekly_menus'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id = Column(String(36), ForeignKey('households.id'), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    dinners = Column(JSON, nullable=True)  # Array of {day, recipe_id}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    household = relationship('Household', back_populates='menus')

    def __repr__(self):
        return f'<WeeklyMenu {self.week_start}>'

    def to_dict(self):
        return {
            'id': str(self.id),
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'dinners': self.dinners or []
        }


class ShoppingList(Base):
    __tablename__ = 'shopping_lists'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id = Column(String(36), ForeignKey('households.id'), nullable=False)
    menu_id = Column(String(36), ForeignKey('weekly_menus.id'), nullable=True)
    data = Column(JSON, nullable=True)  # Full shopping list structure
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    household = relationship('Household', back_populates='shopping_lists')

    def __repr__(self):
        return f'<ShoppingList {self.household_id}>'
