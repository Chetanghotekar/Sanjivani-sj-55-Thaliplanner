
from app.records import load_records, search, count_by, get_by_id


def main():

    while True:

        print("\n===== THALI PLANNER =====")
        print("1. Show all recipes")
        print("2. Search recipe")
        print("3. Count recipes by category")
        print("4. Find recipe by ID")
        print("5. Exit")

        choice = input("\nEnter your choice: ")

        # Option 1: Show all recipes
        if choice == "1":

            recipes = load_records()

            for recipe in recipes:
                print("\nID:", recipe["id"])
                print("Dish:", recipe["dish_name"])
                print("Category:", recipe["region_or_type"])
                print("Servings:", recipe["servings"])
                print("Ingredients:", recipe["ingredients"])
                print("Time:", recipe["time_and_difficulty"])
                print("Source:", recipe["source_url"])

        # Option 2: Search recipe
        elif choice == "2":

            keyword = input("Enter keyword: ")

            results = search(keyword)

            if results:
                for recipe in results:
                    print(recipe["dish_name"])
            else:
                print("No recipe found.")

        # Option 3: Count recipes
        elif choice == "3":

            counts = count_by()

            for category, total in counts.items():
                print(category, ":", total)

        # Option 4: Find recipe by ID
        elif choice == "4":

            try:
                recipe_id = int(input("Enter recipe ID: "))

                recipe = get_by_id(recipe_id)

                if recipe:
                    print(recipe)
                else:
                    print("Recipe not found.")

            except ValueError:
                print("Please enter a valid number.")

        # Option 5: Exit
        elif choice == "5":

            print("Thank you for using Thali Planner!")
            break

        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
