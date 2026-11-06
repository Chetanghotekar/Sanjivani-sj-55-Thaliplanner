
from data.sample_records import sample_records


# 1. Load all recipes
def load_records():
    return sample_records


# 2. Search recipes by keyword
def search(keyword):
    results = []

    keyword = keyword.lower()

    for recipe in load_records():

        # Search in dish name
        if keyword in recipe["dish_name"].lower():
            results.append(recipe)

        # Search in category
        elif keyword in recipe["region_or_type"].lower():
            results.append(recipe)

        # Search in ingredients
        elif any(keyword in item.lower()
                 for item in recipe["ingredients"]):
            results.append(recipe)

    return results


# 3. Count recipes by category
def count_by(field="region_or_type"):
    counts = {}

    for recipe in load_records():

        category = recipe[field]

        if category in counts:
            counts[category] += 1
        else:
            counts[category] = 1

    return counts


# 4. Get recipe using ID
def get_by_id(recipe_id):

    for recipe in load_records():

        if recipe["id"] == recipe_id:
            return recipe

    return None
