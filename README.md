# Big Pig Farm

A terminal-based idle simulation game where you manage a guinea pig farm. Watch your guinea pigs roam freely with ASCII art representation, exhibiting natural behaviors like eating, sleeping, playing, and reproducing. Expand your farm, breed rare color patterns, and build the ultimate guinea pig paradise.

## Features

- **ASCII Art Guinea Pigs** - Cute animated guinea pigs that move around your farm
- **Autonomous Behaviors** - Pigs eat, drink, sleep, play, and socialize on their own
- **Genetics System** - Mendelian inheritance with multiple gene loci for color and pattern
- **Breeding** - Breed guinea pigs to discover rare color combinations
- **Farm Management** - Place, move, and remove facilities visually
- **Farm Expansion** - Upgrade your farm through 6 tiers from Starter Hutch to Ultimate Farm
- **Economy** - Buy facilities, sell pigs, manage your money
- **Save System** - Auto-saves every 30 seconds and on exit

## Installation

### Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd big-pig-farm

# Install dependencies
poetry install

# Run the game
poetry run big-pig-farm
```

## How to Play

### Main Controls

| Key | Action |
|-----|--------|
| `F` | Feed all food bowls and water bottles |
| `S` | Open Shop |
| `P` | View Pigs list |
| `B` | Open Breeding planner |
| `E` | Toggle Edit mode (for facilities) |
| `N` | Start New Game |
| `Space` | Pause/Resume |
| `+`/`-` | Adjust game speed |
| `Tab` | Select next pig |
| `Arrow keys` | Scroll view (or move cursor in edit mode) |
| `Esc` | Deselect / Exit mode |
| `Q` | Quit game |

### Edit Mode (Press E)

In edit mode, you can manage facilities visually:

| Key | Action |
|-----|--------|
| `Arrow keys` | Move cursor |
| `Enter` | Select facility under cursor |
| `M` | Start moving selected facility |
| `R` / `Delete` | Remove facility (get full refund) |
| `Esc` | Exit edit mode |

### Shop (Press S)

| Key | Action |
|-----|--------|
| `F` | Facilities category |
| `D` | Food category |
| `U` | Upgrades category (farm expansion) |
| `Tab` | Cycle categories |
| `Arrow keys` | Navigate items |
| `Enter` | Purchase |

## Game Mechanics

### Guinea Pig Needs

Guinea pigs have several needs that decay over time:

- **Hunger** - Reduced by eating at food bowls
- **Thirst** - Reduced by drinking from water bottles
- **Energy** - Restored by sleeping in hideouts
- **Happiness** - Increased by playing, socializing, and meeting other needs
- **Social** - Increased by interacting with other pigs

Pigs will automatically seek out facilities to meet their needs. They continue eating/drinking until 90% satisfied.

### Facilities

| Facility | Purpose | Tier Required |
|----------|---------|---------------|
| Food Bowl | Reduces hunger | 1 |
| Water Bottle | Provides hydration | 1 |
| Hideout | Sleep and shelter | 1 |
| Hay Rack | Fiber + health bonus | 2 |
| Exercise Wheel | Entertainment + health | 2 |
| Tunnel System | Play + happiness | 2 |
| Play Area | Social activities | 3 |
| Grooming Station | Health + sale value | 3 |
| Breeding Den | Improved breeding | 4 |
| Nursery | Faster baby growth | 4 |
| Veggie Garden | Auto food production | 4 |

Removing facilities refunds the full purchase price.

### Genetics

Guinea pigs inherit traits through a realistic genetics system:

- **Base Color** (E and B loci): Black, Chocolate, Golden
- **Pattern** (S locus): Solid, Dutch, Dalmatian
- **Color Intensity** (C locus): Full, Chinchilla, Himalayan
- **Roan** (R locus): Normal, Roan pattern

Rarity tiers affect sale value:
- Common (1x) - Solid black, brown, golden
- Uncommon (1.5x) - Dutch pattern, chocolate
- Rare (2.5x) - Dalmatian, Roan
- Very Rare (4x) - Himalayan, Chinchilla
- Legendary (10x) - Perfect Dalmatian, rare combinations

### Farm Tiers

| Tier | Name | Size | Capacity | Cost |
|------|------|------|----------|------|
| 1 | Starter Hutch | 20x10 | 4 pigs | Free |
| 2 | Cozy Enclosure | 30x15 | 8 pigs | $500 |
| 3 | Family Pen | 40x20 | 15 pigs | $2,000 |
| 4 | Guinea Grove | 50x25 | 25 pigs | $8,000 |
| 5 | Piggy Paradise | 60x30 | 40 pigs | $25,000 |
| 6 | Ultimate Farm | 80x40 | 60 pigs | $100,000 |

Higher tiers unlock additional facilities and increase pig capacity.

## Save Data

Game saves are stored at:
```
~/.big_pig_farm/savegame.db
```

The game auto-saves:
- Every 30 seconds during gameplay
- When you quit the game

To reset your game, either:
- Press `N` in-game and confirm
- Delete the save file manually: `rm ~/.big_pig_farm/savegame.db`

## Development

### Running Tests

```bash
poetry run pytest tests/ -v
```

### Project Structure

```
big_pig_farm/
├── app.py              # Main Textual application
├── main.py             # Entry point
├── data/               # Configuration, sprites, names
│   ├── config.py       # Game balance constants
│   ├── sprites.py      # ASCII art definitions
│   └── names.py        # Name generation
├── entities/           # Core game entities
│   ├── guinea_pig.py   # Guinea pig entity
│   ├── genetics.py     # Genetic system
│   └── facilities.py   # Facility definitions
├── game/               # Game systems
│   ├── engine.py       # Game loop and tick management
│   ├── state.py        # Game state container
│   ├── world.py        # Farm grid and pathfinding
│   └── save_manager.py # SQLite persistence
├── simulation/         # Simulation logic
│   ├── behavior.py     # AI state machine
│   ├── needs.py        # Needs decay and recovery
│   └── breeding.py     # Reproduction system
├── economy/            # Economy system
│   ├── currency.py     # Money management
│   ├── shop.py         # Shop items and purchases
│   └── market.py       # Pig valuation
└── ui/                 # User interface
    ├── screens/        # Full-screen views
    │   ├── main_game.py
    │   ├── shop.py
    │   ├── pig_list.py
    │   ├── breeding.py
    │   ├── facilities.py
    │   └── confirm.py
    └── widgets/        # Reusable components
        ├── farm_view.py
        ├── status_bar.py
        └── notification.py
```

### Tech Stack

- **Python 3.10+** - Modern Python with type hints
- **Textual** - Terminal UI framework
- **Rich** - Text styling (Textual dependency)
- **Pydantic** - Data validation and serialization
- **SQLite** - Save game persistence
- **Poetry** - Dependency management

## License

MIT License

## Credits

Created with love for guinea pigs everywhere.
