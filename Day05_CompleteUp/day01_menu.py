"""Day 1: Simple interactive menu."""
while True:
    print("\n--- ThaliPlanner Menu ---")
    print("1. About ThaliPlanner")
    print("2. Sample questions")
    print("3. Check serving size")
    print("0. Exit")
    choice = input("Choose an option: ").strip()

    if choice == "1":
        print("ThaliPlanner helps users explore Indian recipes.")
    elif choice == "2":
        print("Examples: Find dal recipes | Show rice dishes | Search paneer")
    elif choice == "3":
        try:
            servings = int(input("Enter number of servings: "))
            if servings <= 0:
                print("Invalid serving count.")
            elif servings <= 4:
                print("Suitable for a small family.")
            else:
                print("Suitable for a larger group.")
        except ValueError:
            print("Please enter a whole number.")
    elif choice == "0":
        print("Thank you for using ThaliPlanner!")
        break
    else:
        print("Invalid option. Try again.")
