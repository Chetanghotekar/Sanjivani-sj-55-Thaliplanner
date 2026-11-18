"""Day 3: Recipe record model."""
from dataclasses import asdict, dataclass, field
from typing import List, Optional

@dataclass
class Record:
    id: int
    dish_name: str
    region_or_type: str = "Unknown"
    servings: Optional[int] = None
    ingredients: List[str] = field(default_factory=list)
    time_and_difficulty: str = ""
    source_url: str = ""

    def to_dict(self):
        return asdict(self)
