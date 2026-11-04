from __future__ import annotations

from vision_engine.concept_board.domain.enums import CatalogueSnapshotStatus, DesignRegionLifecycle
from vision_engine.concept_board.domain.errors import InvariantError, RegionError


REGION_TYPE_TO_PRODUCT_TYPES: dict[str, set[str]] = {
    "bed": {"bed", "bed_frame", "furniture"},
    "nightstand": {"side_table", "bedside_table", "table"},
    "dresser": {"dresser", "cabinet", "joinery"},
    "sofa": {"sofa", "sectional"},
    "armchair": {"armchair", "chair"},
    "coffee_table": {"coffee_table", "table"},
    "side_table": {"side_table", "table"},
    "dining_table": {"dining_table", "table"},
    "chair": {"chair", "dining_chair"},
    "floor_finish": {"flooring", "floor_finish", "material"},
    "wall_finish": {"wall_finish", "paint", "material"},
    "ceiling_finish": {"ceiling_finish", "material"},
    "pendant_light": {"pendant_light", "lighting", "ceiling_light"},
    "ceiling_pendant_light": {"pendant_light", "lighting", "ceiling_light"},
    "ceiling_flush_mount_light": {"flush_mount_light", "lighting", "ceiling_light"},
    "ceiling_chandelier": {"chandelier", "lighting", "ceiling_light"},
    "ceiling_spotlight": {"spotlight", "lighting", "ceiling_light"},
    "ceiling_track_light": {"track_light", "lighting", "ceiling_light"},
    "wall_sconce": {"wall_sconce", "lighting", "wall_light"},
    "wall_picture_light": {"picture_light", "lighting", "wall_light"},
    "wall_washer": {"wall_washer", "lighting", "wall_light"},
    "cabinet_light": {"cabinet_light", "lighting"},
    "freestanding_wardrobe": {"wardrobe", "joinery", "cabinet"},
    "fitted_wardrobe": {"wardrobe", "joinery", "cabinet", "built_in"},
    "wardrobe_system": {"wardrobe", "joinery", "cabinet"},
    "floor_lamp": {"floor_lamp", "lighting"},
    "table_lamp": {"table_lamp", "lighting"},
    "curtains": {"curtains", "textile"},
    "blinds": {"blinds", "textile"},
    "rug": {"rug", "textile"},
    "joinery": {"joinery", "cabinet"},
    "built_in": {"joinery", "cabinet"},
    "artwork": {"artwork", "decor"},
    "mirror": {"mirror", "decor"},
    "plant": {"plant", "decor"},
    "decorative_object": {"decor"},
}


def assert_not_fixed_region(is_fixed: bool, action: str) -> None:
    if is_fixed:
        raise RegionError(f"Cannot {action} on fixed region without privileged override")


def assert_sealed_snapshot(status: CatalogueSnapshotStatus, action: str) -> None:
    if status != CatalogueSnapshotStatus.SEALED:
        raise InvariantError(f"{action} requires a sealed catalogue snapshot")


def assert_confirmed_region(status: DesignRegionLifecycle, action: str) -> None:
    if status != DesignRegionLifecycle.CONFIRMED:
        raise RegionError(f"{action} requires a confirmed design region")


def product_types_for_region(region_type: str) -> set[str]:
    key = region_type.lower().strip()
    return REGION_TYPE_TO_PRODUCT_TYPES.get(key, {key, "decor"})
