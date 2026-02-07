"""Name generation data for guinea pigs."""

import random
from typing import Optional

# First name components (gender-specific)
MALE_PREFIXES = [
    "Sir", "Mr.", "Duke", "Lord", "Baron", "Count", "King", "Prince",
]
FEMALE_PREFIXES = [
    "Lady", "Ms.", "Princess", "Queen", "Duchess", "Baroness", "Countess",
]
NEUTRAL_PREFIXES = [
    "Professor", "Captain", "Dr.", "Chief",
]

# Cute guinea pig names
CUTE_NAMES = [
    "Squeaky", "Patches", "Peanut", "Cinnamon", "Nutmeg", "Cookie", "Biscuit",
    "Caramel", "Mocha", "Cocoa", "Oreo", "Brownie", "Muffin", "Cupcake",
    "Butterscotch", "Toffee", "Marshmallow", "Ginger", "Pepper", "Clover",
    "Daisy", "Poppy", "Rosie", "Willow", "Maple", "Hazel", "Olive", "Basil",
    "Sage", "Thyme", "Parsley", "Mint", "Peaches", "Apricot", "Plum", "Cherry",
    "Mango", "Kiwi", "Coconut", "Almond", "Walnut", "Cashew", "Pistachio",
    "Pretzel", "Crumble", "Fudge", "Truffle", "Pudding", "Custard", "Waffle",
    "Pancake", "Noodle", "Dumpling", "Tofu", "Mochi", "Boba", "Sushi",
]

# Food-based names
FOOD_NAMES = [
    "Carrot", "Lettuce", "Celery", "Cucumber", "Tomato", "Spinach", "Kale",
    "Broccoli", "Cabbage", "Radish", "Turnip", "Beet", "Pumpkin", "Squash",
    "Zucchini", "Eggplant", "Potato", "Bean", "Pea", "Corn",
]

# Color-based names
COLOR_NAMES = [
    "Ginger", "Rusty", "Sandy", "Sunny", "Goldie", "Copper", "Bronze",
    "Ebony", "Onyx", "Shadow", "Midnight", "Coal", "Smoky", "Dusty",
    "Snowy", "Ivory", "Pearl", "Cotton", "Cloud", "Frost", "Cream",
    "Cocoa", "Chocolate", "Mocha", "Espresso", "Coffee", "Brownie",
    "Caramel", "Honey", "Amber", "Tawny", "Fawn",
]

# Personality-based names
PERSONALITY_NAMES = [
    "Whiskers", "Nibbles", "Squeaks", "Wiggles", "Tumbles", "Scamper",
    "Zippy", "Bouncy", "Fluffy", "Fuzzy", "Snuggles", "Cuddles", "Bubbles",
    "Giggles", "Twinkle", "Sparkle", "Pebbles", "Buttons", "Pickles",
    "Sprout", "Nugget", "Pip", "Dot", "Speck", "Freckles", "Speckles",
]

# Famous pig/rodent names
FAMOUS_NAMES = [
    "Hamtaro", "Pikachu", "Remy", "Stuart", "Gus", "Jerry", "Mickey",
    "Minnie", "Chip", "Dale", "Gadget", "Fievel", "Bernard", "Bianca",
    "Templeton", "Rizzo", "Splinter", "Ratigan",
]

# Suffixes for unique combinations
SUFFIXES = [
    "Jr.", "III", "the Great", "the Fluffy", "the Brave", "the Wise",
    "the Mighty", "the Gentle", "the Swift", "the Noble",
]

ALL_NAMES = CUTE_NAMES + FOOD_NAMES + COLOR_NAMES + PERSONALITY_NAMES + FAMOUS_NAMES


def generate_name(include_title: bool = False, include_suffix: bool = False, gender: Optional[str] = None) -> str:
    """Generate a random guinea pig name.

    Args:
        include_title: Whether to potentially include a title prefix
        include_suffix: Whether to potentially include a suffix
        gender: "male", "female", or None for gender-appropriate prefixes

    Returns:
        A randomly generated name
    """
    name = random.choice(ALL_NAMES)

    if include_title and random.random() < 0.15:
        if gender == "male":
            prefixes = MALE_PREFIXES + NEUTRAL_PREFIXES
        elif gender == "female":
            prefixes = FEMALE_PREFIXES + NEUTRAL_PREFIXES
        else:
            prefixes = MALE_PREFIXES + FEMALE_PREFIXES + NEUTRAL_PREFIXES
        prefix = random.choice(prefixes)
        name = f"{prefix} {name}"

    if include_suffix and random.random() < 0.1:
        suffix = random.choice(SUFFIXES)
        name = f"{name} {suffix}"

    return name


def generate_unique_name(existing_names: set[str], gender: Optional[str] = None, max_attempts: int = 100) -> str:
    """Generate a unique name not in the existing set.

    Args:
        existing_names: Set of names already in use
        gender: "male", "female", or None for gender-appropriate prefixes
        max_attempts: Maximum attempts before adding a number suffix

    Returns:
        A unique name
    """
    for _ in range(max_attempts):
        name = generate_name(include_title=True, include_suffix=True, gender=gender)
        if name not in existing_names:
            return name

    # Fallback: add a number
    base_name = random.choice(ALL_NAMES)
    counter = 1
    while f"{base_name} {counter}" in existing_names:
        counter += 1
    return f"{base_name} {counter}"
