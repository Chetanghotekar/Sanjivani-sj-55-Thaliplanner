"""build_grocery_list: scaling, unit conversion and merging. Pure Python, no LLM."""
import pytest

from app.tools import build_grocery_list, convert_to_base, normalize_item, load_quantities

RECORDS = [
    {"id": 1, "dish_name": "Dal A", "servings": 4, "ingredients": ["moong dal", "salt", "mystery spice"]},
    {"id": 2, "dish_name": "Rice B", "servings": 2, "ingredients": ["rice", "moong dal", "potatoes"]},
    {"id": 3, "dish_name": "No Servings", "servings": None, "ingredients": ["rice"]},
]
QTY = {
    "1": [["moong dal", 1, "cup"], ["salt", 1, "tsp"]],
    "2": [["rice", 1, "cup"], ["moong dal", 0.5, "cup"], ["potatoes", 2, "piece"]],
    "3": [["rice", 1, "cup"]],
}


def item(result, name, unit=None):
    return next(i for i in result["items"] if i["item"] == name and (unit is None or i["unit"] == unit))


def test_scaling_and_cup_to_grams():
    out = build_grocery_list([{"recipe_id": 1, "servings": 8}], RECORDS, QTY)
    assert item(out, "moong dal")["quantity"] == 400      # 1 cup x2 = 2 cups x 200 g
    assert out["recipes"][0]["scale"] == 2.0


def test_same_ingredient_is_summed_across_recipes():
    out = build_grocery_list([{"recipe_id": 1, "servings": 4}, {"recipe_id": 2, "servings": 4}], RECORDS, QTY)
    moong = item(out, "moong dal")
    assert moong["quantity"] == 400                        # 200 g + (0.5 cup x2 = 200 g)
    assert moong["from"] == ["Dal A", "Rice B"]


def test_tbsp_tsp_and_liquids():
    assert convert_to_base("salt", 1, "tsp")[:2] == pytest.approx((6.04, "g"), abs=0.01)
    assert convert_to_base("rice", 2, "tbsp")[:2] == pytest.approx((23.125, "g"), abs=0.01)
    assert convert_to_base("milk", 1, "cup")[:2] == (240.0, "ml")
    assert convert_to_base("oil", 2, "tbsp")[:2] == (30.0, "ml")
    assert convert_to_base("ginger", 2, "kg")[:2] == (2000.0, "g")
    assert convert_to_base("water", 1.5, "l")[:2] == (1500.0, "ml")


def test_pieces_become_grams_when_known_and_unknown_conversion_is_flagged():
    assert convert_to_base("potato", 2, "piece")[:2] == (300.0, "g")
    assert convert_to_base("cardamom", 2, "piece")[:2] == (2, "piece")
    qty, unit, warning = convert_to_base("unobtainium", 1, "cup")
    assert (qty, unit) == (1, "cup") and "no gram/ml conversion" in warning


def test_aliases_merge_potatoes_and_potato():
    assert normalize_item("Potatoes ") == "potato"
    out = build_grocery_list([{"recipe_id": 2}], RECORDS, QTY)
    assert item(out, "potato")["quantity"] == 300


def test_servings_default_to_recipe_servings():
    out = build_grocery_list([{"recipe_id": 1}], RECORDS, QTY)
    assert out["recipes"][0]["scale"] == 1.0 and item(out, "moong dal")["quantity"] == 200


def test_unquantified_ingredients_are_listed_not_guessed():
    out = build_grocery_list([{"recipe_id": 1}], RECORDS, QTY)
    assert out["unquantified"] == [{"item": "mystery spice", "from": ["Dal A"]}]
    assert all(i["item"] != "mystery spice" for i in out["items"])


def test_missing_recipe_and_recipe_without_servings():
    out = build_grocery_list([{"recipe_id": 999}, {"recipe_id": 3, "servings": 2}, {"recipe_id": 1}], RECORDS, QTY)
    assert out["missing_recipes"] == [999]
    assert any("No Servings" in w for w in out["warnings"])
    assert len(out["recipes"]) == 1


@pytest.mark.parametrize("bad", [[], None, "x", [{"servings": 2}], [{"recipe_id": 1, "servings": 0}],
                                 [{"recipe_id": 1, "servings": -3}], [{"recipe_id": 1, "servings": "4"}],
                                 [{"recipe_id": 1, "servings": True}]])
def test_bad_input_raises(bad):
    with pytest.raises(ValueError):
        build_grocery_list(bad, RECORDS, QTY)


def test_display_switches_to_kg_and_litres():
    out = build_grocery_list([{"recipe_id": 1, "servings": 40}], RECORDS, QTY)
    assert item(out, "moong dal")["display"] == "2 kg"


# ---- the real data file ----
def test_every_real_recipe_has_quantities_and_converts_cleanly():
    quantities = load_quantities()
    from app.records import load_records
    records = load_records()
    assert len(quantities) >= 20
    out = build_grocery_list([{"recipe_id": r["id"], "servings": 4} for r in records[:20]], records, quantities)
    assert out["warnings"] == [] and out["unquantified"] == [] and out["missing_recipes"] == []
    assert item(out, "moong dal")["unit"] == "g"
