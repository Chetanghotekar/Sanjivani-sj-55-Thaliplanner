"""Day 2: Command-line interface for recipe records."""
from app.records import load_records, search, count_by, get_by_id

def main():
    while True:
        print("\n--- ThaliPlanner Records ---")
        print("1. Show all recipes")
        print("2. Search recipes")
        print("3. Count by category")
        print("4. Find recipe by ID")
        print("0. Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            for item in load_records():
                print(f'{item.get("id")}. {item.get("dish_name")} | Servings: {item.get("servings")}')
        elif choice == "2":
            term = input("Search word: ")
            for item in search(term):
                print(item["id"], item["dish_name"], "|", ", ".join(item.get("ingredients", [])))
        elif choice == "3":
            for category, total in count_by().items():
                print(f"{category}: {total}")
        elif choice == "4":
            item = get_by_id(input("Recipe ID: "))
            print(item if item else "Recipe not found.")
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
