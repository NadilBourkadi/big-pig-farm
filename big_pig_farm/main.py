"""Entry point for Big Pig Farm."""

from big_pig_farm.app import BigPigFarmApp


def main() -> None:
    """Run the Big Pig Farm game."""
    app = BigPigFarmApp()
    app.run()


if __name__ == "__main__":
    main()
