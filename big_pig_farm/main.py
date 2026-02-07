"""Entry point for Big Pig Farm."""

import sys

from big_pig_farm.app import BigPigFarmApp


def main() -> None:
    """Run the Big Pig Farm game."""
    debug = "--debug" in sys.argv
    app = BigPigFarmApp(debug=debug)
    app.run()


if __name__ == "__main__":
    main()
