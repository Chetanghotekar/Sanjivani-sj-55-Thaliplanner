"""Day 01: A simple while-loop menu for ThaliPlanner."""

while True:
    print("\n========== THALIPLANNER MENU ==========")
    print("1. About ThaliPlanner")
    print("2. Sample questions")
    print("3. Check a regional thali rule")
    print("0. Exit")

    choice = input("Enter your choice: ").strip()

    if choice == "1":
        print("\nThaliPlanner helps travellers discover Indian destinations,")
        print("regional thalis, festivals, traditions, and cultural experiences.")

    elif choice == "2":
        print("\nSample questions:")
        print("- Which traditional thali can I try in Maharashtra?")
        print("- What food is popular in Rajasthan?")
        print("- Which festivals are celebrated in Gujarat?")

    elif choice == "3":
        state = input("Enter an Indian state: ").strip().lower()

        if state == "maharashtra":
            print("Rule result: Explore a Maharashtrian thali, such as a meal with bhakri, pithla, and thecha.")
        elif state == "rajasthan":
            print("Rule result: Explore a Rajasthani thali with dishes such as dal baati churma.")
        else:
            print("Rule result: We do not have a sample thali rule for that state yet.")

    elif choice == "0":
        print("Thank you for exploring ThaliPlanner. Goodbye!")
        break

    else:
        print("Invalid choice. Please enter 1, 2, 3, or 0.")
