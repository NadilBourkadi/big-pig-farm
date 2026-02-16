"""Farm area and tunnel connection models."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from big_pig_farm.entities.biomes import BiomeType


class FarmArea(BaseModel):
    """A rectangular room within the farm grid."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    biome: BiomeType
    x1: int  # Top-left corner (inclusive, wall)
    y1: int  # Top-left corner (inclusive, wall)
    x2: int  # Bottom-right corner (inclusive, wall)
    y2: int  # Bottom-right corner (inclusive, wall)
    is_starter: bool = False
    grid_col: int = 0  # Column in the 2-column grid layout
    grid_row: int = 0  # Row in the 2-column grid layout

    @property
    def interior_x1(self) -> int:
        """Left boundary of walkable interior (inside wall)."""
        return self.x1 + 1

    @property
    def interior_y1(self) -> int:
        """Top boundary of walkable interior (inside wall)."""
        return self.y1 + 1

    @property
    def interior_x2(self) -> int:
        """Right boundary of walkable interior (inside wall)."""
        return self.x2 - 1

    @property
    def interior_y2(self) -> int:
        """Bottom boundary of walkable interior (inside wall)."""
        return self.y2 - 1

    @property
    def interior_width(self) -> int:
        """Width of walkable interior."""
        return self.interior_x2 - self.interior_x1 + 1

    @property
    def interior_height(self) -> int:
        """Height of walkable interior."""
        return self.interior_y2 - self.interior_y1 + 1

    @property
    def center_x(self) -> int:
        """Center x coordinate."""
        return (self.x1 + self.x2) // 2

    @property
    def center_y(self) -> int:
        """Center y coordinate."""
        return (self.y1 + self.y2) // 2

    def contains(self, x: int, y: int) -> bool:
        """Check if a point is inside the area (including walls)."""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def contains_interior(self, x: int, y: int) -> bool:
        """Check if a point is inside the walkable interior."""
        return self.interior_x1 <= x <= self.interior_x2 and self.interior_y1 <= y <= self.interior_y2


class TunnelConnection(BaseModel):
    """A corridor connecting two farm areas."""
    id: UUID = Field(default_factory=uuid4)
    area_a_id: UUID
    area_b_id: UUID
    cells: list[tuple[int, int]] = Field(default_factory=list)
    orientation: str = "horizontal"  # "horizontal" or "vertical"
