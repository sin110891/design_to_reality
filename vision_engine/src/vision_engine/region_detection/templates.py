from __future__ import annotations

ROOM_TYPE_ALIASES: dict[str, str] = {
    "living": "living_room",
    "living room": "living_room",
    "bed": "bedroom",
    "master_bedroom": "bedroom",
    "dining": "dining_room",
    "kitchen_diner": "kitchen",
    "home_office": "office",
    "study": "office",
}

ROOM_REGION_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "bedroom": [
        {"region_type": "bed", "region_code": "bed_01", "display_name": "Bed"},
        {"region_type": "fitted_wardrobe", "region_code": "wardrobe_01", "display_name": "Wardrobe"},
        {"region_type": "ceiling_pendant_light", "region_code": "light_01", "display_name": "Ceiling light"},
        {"region_type": "floor_finish", "region_code": "floor_01", "display_name": "Floor finish"},
        {"region_type": "wall_finish", "region_code": "wall_01", "display_name": "Wall finish"},
        {"region_type": "rug", "region_code": "rug_01", "display_name": "Rug"},
    ],
    "living_room": [
        {"region_type": "sofa", "region_code": "sofa_01", "display_name": "Main sofa"},
        {"region_type": "coffee_table", "region_code": "coffee_table_01", "display_name": "Coffee table"},
        {"region_type": "floor_lamp", "region_code": "floor_lamp_01", "display_name": "Floor lamp"},
        {"region_type": "pendant_light", "region_code": "light_01", "display_name": "Pendant light"},
        {"region_type": "rug", "region_code": "rug_01", "display_name": "Rug"},
        {"region_type": "floor_finish", "region_code": "floor_01", "display_name": "Floor finish"},
    ],
    "dining_room": [
        {"region_type": "dining_table", "region_code": "dining_table_01", "display_name": "Dining table"},
        {"region_type": "chair", "region_code": "chair_01", "display_name": "Dining chairs"},
        {"region_type": "pendant_light", "region_code": "light_01", "display_name": "Pendant light"},
        {"region_type": "floor_finish", "region_code": "floor_01", "display_name": "Floor finish"},
    ],
    "kitchen": [
        {"region_type": "joinery", "region_code": "joinery_01", "display_name": "Kitchen joinery"},
        {"region_type": "pendant_light", "region_code": "light_01", "display_name": "Pendant light"},
        {"region_type": "floor_finish", "region_code": "floor_01", "display_name": "Floor finish"},
    ],
    "office": [
        {"region_type": "joinery", "region_code": "desk_01", "display_name": "Desk / storage"},
        {"region_type": "chair", "region_code": "chair_01", "display_name": "Desk chair"},
        {"region_type": "floor_lamp", "region_code": "floor_lamp_01", "display_name": "Task lighting"},
        {"region_type": "floor_finish", "region_code": "floor_01", "display_name": "Floor finish"},
    ],
}

DEFAULT_TEMPLATE_KEY = "living_room"


def normalise_room_type(room_type: str | None) -> str:
    if not room_type:
        return DEFAULT_TEMPLATE_KEY
    key = room_type.strip().lower().replace("-", "_").replace(" ", "_")
    if key in ROOM_REGION_TEMPLATES:
        return key
    alias = ROOM_TYPE_ALIASES.get(room_type.strip().lower()) or ROOM_TYPE_ALIASES.get(key)
    if alias:
        return alias
    return DEFAULT_TEMPLATE_KEY


def template_regions(room_type: str | None) -> list[dict[str, str]]:
    return list(ROOM_REGION_TEMPLATES.get(normalise_room_type(room_type), ROOM_REGION_TEMPLATES[DEFAULT_TEMPLATE_KEY]))


def allowed_region_types(room_type: str | None) -> list[str]:
    types = {item["region_type"] for item in template_regions(room_type)}
    types.update(
        {
            "sofa",
            "armchair",
            "coffee_table",
            "side_table",
            "bed",
            "fitted_wardrobe",
            "freestanding_wardrobe",
            "pendant_light",
            "ceiling_pendant_light",
            "floor_lamp",
            "table_lamp",
            "floor_finish",
            "wall_finish",
            "ceiling_finish",
            "rug",
            "curtains",
            "joinery",
            "mirror",
            "artwork",
        }
    )
    return sorted(types)
