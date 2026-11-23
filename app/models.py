"""Recipe record schema for ThaliPlanner with complete timings, ingredients, and method steps."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional


@dataclass
class Record:
    id: int
    dish_name: str
    region_or_type: str = "Unknown"
    servings: Optional[Any] = None
    preparation_time: Optional[str] = None
    cooking_time: Optional[str] = None
    soaking_time: Optional[str] = None
    fermentation_time: Optional[str] = None
    difficulty: Optional[str] = None
    ingredients: List[str] = field(default_factory=list)
    preparation_steps: List[str] = field(default_factory=list)
    time_and_difficulty: str = ""
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
