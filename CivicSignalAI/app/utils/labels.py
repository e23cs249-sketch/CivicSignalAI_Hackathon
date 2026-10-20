from enum import Enum


class Category(str, Enum):
    OVERFLOWING_GARBAGE = "overflowing_garbage"
    BROKEN_STREETLIGHT = "broken_streetlight"
    DAMAGED_ROAD = "damaged_road"
    WATER_LEAK = "water_leak"
    UNSAFE_SIDEWALK = "unsafe_sidewalk"
    POTHOLES = "potholes"
    DRAINAGE_WATERLOGGING = "drainage_waterlogging"
    DAMAGED_PUBLIC_PROPERTY = "damaged_public_property"
    OTHER = "other"


CATEGORY_LABELS = {
    Category.OVERFLOWING_GARBAGE: "Overflowing garbage",
    Category.BROKEN_STREETLIGHT: "Broken streetlight",
    Category.DAMAGED_ROAD: "Damaged road",
    Category.WATER_LEAK: "Water leak",
    Category.UNSAFE_SIDEWALK: "Unsafe sidewalk",
    Category.POTHOLES: "Potholes",
    Category.DRAINAGE_WATERLOGGING: "Drainage and waterlogging",
    Category.DAMAGED_PUBLIC_PROPERTY: "Damaged public property",
    Category.OTHER: "Other civic issue",
}

CATEGORY_ALIASES = {
    Category.OVERFLOWING_GARBAGE: (
        "overflowing garbage",
        "garbage",
        "trash",
        "waste",
    ),
    Category.BROKEN_STREETLIGHT: (
        "streetlight",
        "street light",
        "street lamp",
    ),
    Category.DAMAGED_ROAD: (
        "damaged road",
        "road damage",
        "pothole",
    ),
    Category.WATER_LEAK: (
        "water leak",
        "leaking pipe",
        "pipe leak",
        "leak",
    ),
    Category.UNSAFE_SIDEWALK: (
        "unsafe sidewalk",
        "sidewalk",
        "walkway",
    ),
    Category.POTHOLES: ("potholes", "pothole"),
    Category.DRAINAGE_WATERLOGGING: ("drainage", "waterlogging", "water logging", "blocked drain"),
    Category.DAMAGED_PUBLIC_PROPERTY: ("public property", "damaged bench", "damaged sign"),
    Category.OTHER: (),
}

HIGH_PRIORITY_TERMS = (
    "dangerous",
    "unsafe",
    "sparking",
    "exposed wire",
    "live wire",
    "flooding",
)
MEDIUM_PRIORITY_TERMS = (
    "leak",
    "leaking",
    "pothole",
    "overflowing",
    "broken",
    "damaged",
    "outage",
)
LOW_PRIORITY_TERMS = ("minor", "small", "intermittent", "cosmetic")
