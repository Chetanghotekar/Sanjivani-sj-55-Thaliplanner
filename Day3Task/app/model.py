from dataclasses import dataclass
from typing import List

@dataclass
class Record:
    dish_name: str
    region_or_type: str
    servings: str
    ingredients: List[str]
    time_and_difficulty: str
    source_url: str