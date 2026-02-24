"""Movement, wandering, dodging, and rescue logic for guinea pig AI."""

import random
from typing import TYPE_CHECKING

from big_pig_farm.data.config import BEHAVIOR, NEEDS, SIMULATION
from big_pig_farm.entities.areas import FarmArea
from big_pig_farm.entities.biomes import COLOR_TO_BIOME
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig, Position

if TYPE_CHECKING:
    from big_pig_farm.simulation.behavior_controller import BehaviorController


def get_biome_wander_target(
    controller: "BehaviorController", pig: GuineaPig,
) -> tuple[FarmArea | None, bool]:
    """Find the target area for biome-biased wandering.

    Color is the primary driver: a pig whose base color matches a biome's
    signature color will target that biome's area.  Falls back to
    preferred_biome for pigs whose color has no matching biome on the farm.

    Returns (target_area, is_color_match).  A* homing only fires for
    color matches; preferred_biome fallback only gets the soft direction
    bias, so rooms stay populated even when their signature color is rare.
    """
    farm = controller.game_state.farm
    pig_x, pig_y = pig.position.x, pig.position.y

    def _closest(areas: list[FarmArea]) -> FarmArea:
        return min(areas, key=lambda a: abs(a.center_x - pig_x) + abs(a.center_y - pig_y))

    # Primary: match pig's base color to a biome's signature color
    color_biome = COLOR_TO_BIOME.get(pig.phenotype.base_color)
    if color_biome:
        areas = farm.find_areas_by_biome(color_biome)
        if areas:
            return _closest(areas), True

    # Fallback: use preferred_biome (inherited from birth area)
    if pig.preferred_biome:
        areas = farm.find_areas_by_biome(pig.preferred_biome)
        if areas:
            return _closest(areas), False

    return None, False


def bias_wander_directions(
    controller: "BehaviorController",
    pig: GuineaPig,
    target_area: FarmArea,
) -> list[tuple[int, int]]:
    """Return cardinal directions weighted toward the target area.

    If the pig is outside the target area, directions aligned with the
    vector toward the area center get a higher weight.  If inside,
    directions pointing away from the nearest edge get a higher weight
    to reduce tunnel drift-out.
    """
    pig_gx, pig_gy = pig.position.grid_pos()
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    inside = target_area.contains_interior(pig_gx, pig_gy)

    if inside:
        # Boost directions that point away from the nearest edge (inward),
        # so pigs near a tunnel opening are less likely to drift out.
        edge_dists = {
            (1, 0): target_area.interior_x2 - pig_gx,
            (-1, 0): pig_gx - target_area.interior_x1,
            (0, 1): target_area.interior_y2 - pig_gy,
            (0, -1): pig_gy - target_area.interior_y1,
        }
        weights: list[float] = [
            BEHAVIOR.BIOME_WANDER_BIAS_INSIDE if edge_dists[d] > 3 else 1.0
            for d in directions
        ]
    else:
        # Outside: weight toward the area center
        vec_x = target_area.center_x - pig_gx
        vec_y = target_area.center_y - pig_gy
        weights = []
        for dx, dy in directions:
            # Dot product with normalized direction gives alignment
            alignment = dx * vec_x + dy * vec_y
            if alignment > 0:
                weights.append(BEHAVIOR.BIOME_WANDER_BIAS_OUTSIDE)
            else:
                weights.append(1.0)

    return random.choices(directions, weights=weights, k=len(directions))


def start_wandering(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Start random wandering using simple straight-line movement.

    Instead of running A* to a random distant cell, pick a random
    walkable direction and build a short straight-line path.  This
    eliminates A* for the ~60% of pigs that are wandering at any
    given time — the single biggest source of unnecessary pathfinding.
    """
    farm = controller.game_state.farm
    pig_gx, pig_gy = pig.position.grid_pos()

    # Cardinal directions — biased toward preferred biome if applicable
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    target_area, is_color_match = get_biome_wander_target(controller, pig)
    if target_area:
        inside = target_area.contains_interior(pig_gx, pig_gy)

        # A* homing only fires for color-matched biomes — it's the only
        # way to cross rooms (tunnels block straight-line wander).  Pigs
        # whose color biome isn't on the farm get only the soft direction
        # bias toward their preferred_biome, keeping non-matching rooms
        # populated while directional mutations build up matching colors.
        if is_color_match and not inside and random.random() < BEHAVIOR.BIOME_HOMING_CHANCE:
            home_target = farm.find_random_walkable_in_area(target_area.id)
            if home_target:
                set_path_to(controller, pig, home_target)
                if pig.path:
                    pig.log_behavior(f"Heading home to {target_area.name}")
                    pig.target_description = f"heading to {target_area.name}"
                    pig.behavior_state = BehaviorState.WANDERING
                    return
                else:
                    pig.log_behavior(f"Homing path failed to {target_area.name}")
            else:
                pig.log_behavior(f"No walkable tile in {target_area.name}")

        # Inside or homing skipped: biased straight-line wander.
        # Pick one direction from the weighted distribution and commit
        # to it — trying all four and keeping the longest lets tunnel
        # directions win over homeward ones near room edges.
        biased = bias_wander_directions(controller, pig, target_area)
        chosen_dx, chosen_dy = biased[0]
        steps = random.randint(
            BEHAVIOR.SIMPLE_WANDER_MIN_STEPS,
            BEHAVIOR.SIMPLE_WANDER_MAX_STEPS,
        )
        best_path: list[tuple[int, int]] = []
        cx, cy = pig_gx, pig_gy
        for _ in range(steps):
            nx, ny = cx + chosen_dx, cy + chosen_dy
            if farm.is_walkable(nx, ny):
                best_path.append((nx, ny))
                cx, cy = nx, ny
            else:
                break
        # If biased direction is blocked, fall back to longest of all 4
        if not best_path:
            random.shuffle(directions)
            for dx, dy in directions:
                steps = random.randint(
                    BEHAVIOR.SIMPLE_WANDER_MIN_STEPS,
                    BEHAVIOR.SIMPLE_WANDER_MAX_STEPS,
                )
                path: list[tuple[int, int]] = []
                cx, cy = pig_gx, pig_gy
                for _ in range(steps):
                    nx, ny = cx + dx, cy + dy
                    if farm.is_walkable(nx, ny):
                        path.append((nx, ny))
                        cx, cy = nx, ny
                    else:
                        break
                if len(path) > len(best_path):
                    best_path = path
    else:
        random.shuffle(directions)
        best_path = []
        for dx, dy in directions:
            steps = random.randint(
                BEHAVIOR.SIMPLE_WANDER_MIN_STEPS,
                BEHAVIOR.SIMPLE_WANDER_MAX_STEPS,
            )
            path = []
            cx, cy = pig_gx, pig_gy
            for _ in range(steps):
                nx, ny = cx + dx, cy + dy
                if farm.is_walkable(nx, ny):
                    path.append((nx, ny))
                    cx, cy = nx, ny
                else:
                    break
            if len(path) > len(best_path):
                best_path = path

    if best_path:
        pig.path = best_path
        end = best_path[-1]
        pig.target_position = Position(x=float(end[0]), y=float(end[1]))
    else:
        # All directions blocked — jump to a random open cell in the area
        target = None
        if pig.current_area_id:
            target = farm.find_random_walkable_in_area(pig.current_area_id)
        if not target:
            target = farm.find_nearest_walkable((pig_gx, pig_gy), max_distance=10)
        if target and target != (pig_gx, pig_gy):
            pig.position.x = float(target[0])
            pig.position.y = float(target[1])
            pig.log_behavior("Teleported out of blocked position")
        else:
            pig.log_behavior("Stuck: no walkable target for wandering teleport")
    pig.behavior_state = BehaviorState.WANDERING


def set_path_to(
    controller: "BehaviorController", pig: GuineaPig, target: tuple[int, int],
) -> None:
    """Calculate and set path to target.

    Uses the persistent LRU path cache (cross-pig / cross-tick).
    Falls back to A* and stores the result for future reuse.
    """
    start = pig.position.grid_pos()
    path = controller.facility_manager._cached_find_path(start, target)

    if path:
        pig.path = path[1:]  # Skip current position
        if pig.path:
            pig.target_position = Position(x=float(target[0]), y=float(target[1]))


def clamp_to_bounds(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Clamp pig position to stay within the walkable area of the farm.

    Walls occupy the outermost ring (row/col 0 and height-1/width-1).
    The first walkable cells are at (1, 1), so we clamp to [1.0, w-2]
    and [1.0, h-2] — just enough to keep pigs off wall cells without
    blocking valid pathfinding waypoints along the border.
    """
    farm = controller.game_state.farm
    pig.position.x = max(1.0, min(pig.position.x, float(farm.width - 2)))
    pig.position.y = max(1.0, min(pig.position.y, float(farm.height - 2)))


def rescue_to_walkable(controller: "BehaviorController", pig: GuineaPig, farm) -> None:
    """Teleport a pig on a non-walkable cell to a safe position.

    Prefers a random walkable cell in the pig's current area (spreads
    pigs out instead of clustering them at the nearest walkable cell).
    Falls back to the nearest walkable cell if area lookup fails.
    """
    target = None
    if pig.current_area_id:
        target = farm.find_random_walkable_in_area(pig.current_area_id)
    if not target:
        gx, gy = int(pig.position.x), int(pig.position.y)
        target = farm.find_nearest_walkable((gx, gy), max_distance=20)
    if target:
        pig.position.x = float(target[0])
        pig.position.y = float(target[1])
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None
        pig.behavior_state = BehaviorState.IDLE
        pig.log_behavior("Rescued from non-walkable cell")
    else:
        pig.log_behavior("Stuck on non-walkable cell; no rescue target found")


def rescue_non_walkable_pigs(
    controller: "BehaviorController", pigs: list[GuineaPig],
) -> None:
    """Post-collision sweep: rescue any pigs that ended up on non-walkable cells."""
    farm = controller.game_state.farm
    for pig in pigs:
        gx, gy = int(pig.position.x), int(pig.position.y)
        if not farm.is_walkable(gx, gy):
            rescue_to_walkable(controller, pig, farm)


def try_dodge(
    controller: "BehaviorController",
    pig: GuineaPig,
    path_dx: float,
    path_dy: float,
    delta_seconds: float,
    speed: float,
) -> bool:
    """Try to sidestep perpendicular to the path direction to get around a blocking pig.

    Returns True if the pig successfully dodged.
    """
    farm = controller.game_state.farm
    move_dist = min(speed * delta_seconds, BEHAVIOR.DODGE_MAX_STEP)  # Cap dodge step

    # Calculate perpendicular directions (rotate 90 degrees both ways)
    perp_dirs = [(-path_dy, path_dx), (path_dy, -path_dx)]
    length = (path_dx * path_dx + path_dy * path_dy) ** 0.5
    if length < BEHAVIOR.PATH_VECTOR_EPSILON:
        return False

    for pdx, pdy in perp_dirs:
        pdx /= length
        pdy /= length
        new_x = pig.position.x + pdx * move_dist
        new_y = pig.position.y + pdy * move_dist
        if (farm.is_valid_position(int(new_x), int(new_y))
                and farm.is_walkable(int(new_x), int(new_y))
                and not controller.collision.is_position_blocked(new_x, new_y, pig)):
            pig.position.x = new_x
            pig.position.y = new_y
            return True
    return False


def give_up_and_fallback(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Give up reaching a facility and apply a need-specific fallback behavior.

    Instead of going IDLE (which causes immediate re-decision to the same
    facility), apply a fallback: sleep where standing, wander away, etc.
    Failed facilities are preserved so the pig doesn't immediately retry.
    """
    desc = pig.target_description or ""
    pig.path = []
    pig.target_position = None
    pig.target_facility_id = None
    pig.target_description = None
    controller._blocked_timers[pig.id] = 0
    controller._stuck_positions.pop(pig.id, None)
    controller._stuck_timers.pop(pig.id, None)

    # If hunger or thirst is critical, use a shorter cooldown (1 cycle
    # instead of 3) so the pig retries faster but doesn't spam every
    # single decision tick with the same blocked facility
    has_critical_need = (
        pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
        or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD
    )
    if has_critical_need:
        controller.facility_manager.set_failed_cooldown(
            pig.id, BEHAVIOR.CRITICAL_FAILED_COOLDOWN_CYCLES,
        )
    else:
        # Keep failed facilities for 3 decision cycles (~6 seconds) before retrying
        controller.facility_manager.set_failed_cooldown(pig.id, BEHAVIOR.FAILED_COOLDOWN_CYCLES)

    if "Hideout" in desc or "sleep" in desc:
        # Sleep where standing — the hideouts are all occupied
        pig.behavior_state = BehaviorState.SLEEPING
        pig.target_description = "sleeping (no hideout available)"
        pig.log_behavior("All hideouts blocked, sleeping where standing")
    else:
        # Wander away and try again later
        pig.behavior_state = BehaviorState.IDLE
        pig.log_behavior("All facilities blocked, wandering away")
        start_wandering(controller, pig)
        # Set a longer cooldown before next decision to avoid retrying immediately
        controller._decision_timers[pig.id] = 0


def update_movement(
    controller: "BehaviorController", pig: GuineaPig, delta_seconds: float,
) -> None:
    """Update pig position along its path.

    At high game speeds delta_seconds can be very large, so we consume
    multiple waypoints per tick until the movement budget is spent.
    """
    if not pig.path:
        return

    # Don't move while sleeping
    if pig.behavior_state == BehaviorState.SLEEPING:
        return

    # Calculate movement speed
    speed = SIMULATION.BASE_MOVE_SPEED

    # Reduce speed if tired
    if pig.needs.energy < BEHAVIOR.ENERGY_SLEEP_THRESHOLD:
        speed *= BEHAVIOR.TIRED_SPEED_MULT

    # Babies are slower
    if pig.is_baby:
        speed *= BEHAVIOR.BABY_SPEED_MULT

    remaining = speed * delta_seconds
    moved = False
    farm = controller.game_state.farm

    while pig.path and remaining > 0:
        next_point = pig.path[0]
        target_x, target_y = float(next_point[0]), float(next_point[1])

        dx = target_x - pig.position.x
        dy = target_y - pig.position.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance < BEHAVIOR.WAYPOINT_REACHED:
            # Already at this waypoint — pop it and continue
            if not controller.collision.is_position_blocked(target_x, target_y, pig):
                pig.position.x = target_x
                pig.position.y = target_y
                pig.path.pop(0)
                moved = True
                continue
            else:
                handle_movement_blocked(controller, pig, dx, dy, delta_seconds, speed)
                return

        if remaining >= distance:
            # Can reach this waypoint in one step
            if not controller.collision.is_position_blocked(target_x, target_y, pig):
                pig.position.x = target_x
                pig.position.y = target_y
                pig.path.pop(0)
                remaining -= distance
                moved = True
                continue
            else:
                handle_movement_blocked(controller, pig, dx, dy, delta_seconds, speed)
                return

        # Partial movement toward next waypoint (remaining < distance)
        new_x = pig.position.x + (dx / distance) * remaining
        new_y = pig.position.y + (dy / distance) * remaining

        if (farm.is_walkable(int(new_x), int(new_y))
                and not controller.collision.is_position_blocked(new_x, new_y, pig, min_distance=BEHAVIOR.BLOCKING_DEFAULT)):
            pig.position.x = new_x
            pig.position.y = new_y
            moved = True
        elif try_dodge(controller, pig, dx, dy, delta_seconds, speed):
            moved = True
        else:
            handle_movement_blocked(controller, pig, dx, dy, delta_seconds, speed)
            return
        break

    if moved:
        if pig.target_description and "(blocked)" in pig.target_description:
            pig.target_description = pig.target_description.replace(" (blocked)", "")
        controller._blocked_timers[pig.id] = 0
        controller._stuck_positions.pop(pig.id, None)
        controller._stuck_timers.pop(pig.id, None)

    if not pig.path:
        pig.target_position = None


def handle_movement_blocked(
    controller: "BehaviorController",
    pig: GuineaPig,
    dx: float,
    dy: float,
    delta_seconds: float,
    speed: float,
) -> None:
    """Handle a pig that is blocked during movement."""
    # Try dodging sideways to get around the blocking pig
    if try_dodge(controller, pig, dx, dy, delta_seconds, speed):
        if pig.target_description and "(blocked)" in pig.target_description:
            pig.target_description = pig.target_description.replace(" (blocked)", "")
        controller._blocked_timers[pig.id] = 0
        controller._stuck_positions.pop(pig.id, None)
        controller._stuck_timers.pop(pig.id, None)
        return

    # Blocked and can't dodge — track how long
    blocked_time = controller._blocked_timers.get(pig.id, 0) + delta_seconds
    controller._blocked_timers[pig.id] = blocked_time

    # Track how long pig is stuck at the same grid cell.
    # Unlike _blocked_timers, this is NOT reset by facility
    # switches — only by actual physical movement.
    grid_pos = (int(pig.position.x), int(pig.position.y))
    if controller._stuck_positions.get(pig.id) != grid_pos:
        controller._stuck_positions[pig.id] = grid_pos
        controller._stuck_timers[pig.id] = 0.0
    controller._stuck_timers[pig.id] = controller._stuck_timers.get(pig.id, 0.0) + delta_seconds

    if pig.target_description and "(blocked)" not in pig.target_description:
        pig.target_description = f"{pig.target_description} (blocked)"

    # If stuck at the same cell too long, force give-up regardless
    # of whether alternative facilities exist (prevents corridor deadlock)
    if controller._stuck_timers.get(pig.id, 0) > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
        give_up_and_fallback(controller, pig)
        return

    # After some time blocked, try to find an alternative facility
    if blocked_time > BEHAVIOR.BLOCKED_TIME_ALTERNATIVE:
        current_target = pig.target_position
        if current_target:
            found = controller.facility_manager.try_alternative_facility(pig, current_target)
            if found:
                controller._blocked_timers[pig.id] = 0
            elif blocked_time > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                give_up_and_fallback(controller, pig)
        elif blocked_time > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
            give_up_and_fallback(controller, pig)
