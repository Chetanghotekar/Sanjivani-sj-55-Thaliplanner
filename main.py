
from data.sample_records import sample_records

# 1. Print all recipes
print("\n===== ALL RECIPES =====")

for recipe in sample_records:
    print(recipe["id"], recipe["dish_name"])


# 2. Search recipe by keyword
keyword = input("\nEnter recipe keyword: ").lower()

print("\n===== SEARCH RESULTS =====")

for recipe in sample_records:
    if keyword in recipe["dish_name"].lower():
        print(recipe["dish_name"])


# 3. Count recipes by category
print("\n===== CATEGORY COUNT =====")

category_count = {}

for recipe in sample_records:
    category = recipe["region_or_type"]

    if category in category_count:
        category_count[category] += 1
    else:
        category_count[category] = 1

for category, count in category_count.items():
    print(category, ":", count)
