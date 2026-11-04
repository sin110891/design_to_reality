from __future__ import annotations

REGION_TYPE_SEARCH_TERMS: dict[str, str] = {
    "bed": "double bed",
    "nightstand": "bedside table",
    "dresser": "chest of drawers",
    "sofa": "sofa",
    "armchair": "armchair",
    "coffee_table": "coffee table",
    "side_table": "side table",
    "dining_table": "dining table",
    "chair": "dining chair",
    "floor_finish": "engineered wood flooring",
    "wall_finish": "interior wall paint",
    "ceiling_finish": "ceiling paint",
    "pendant_light": "pendant light",
    "ceiling_pendant_light": "ceiling pendant light",
    "ceiling_flush_mount_light": "flush mount ceiling light",
    "ceiling_chandelier": "chandelier",
    "ceiling_spotlight": "ceiling spotlight",
    "ceiling_track_light": "track lighting",
    "wall_sconce": "wall sconce",
    "wall_picture_light": "picture light",
    "wall_washer": "wall washer light",
    "cabinet_light": "cabinet light",
    "floor_lamp": "floor lamp",
    "table_lamp": "table lamp",
    "curtains": "curtains",
    "blinds": "window blinds",
    "rug": "area rug",
    "joinery": "built in wardrobe cabinet",
    "freestanding_wardrobe": "freestanding wardrobe",
    "fitted_wardrobe": "fitted wardrobe",
    "wardrobe_system": "wardrobe system",
    "artwork": "wall art",
    "mirror": "mirror",
}


def build_search_query(*, region_type: str, display_name: str | None = None) -> str:
    base = REGION_TYPE_SEARCH_TERMS.get(region_type.lower().strip(), region_type.replace("_", " "))
    if display_name and display_name.strip().lower() not in base.lower():
        return f"{base} {display_name.strip()}"
    return base
