"""Day 01: Introduce the ThaliPlanner project."""

product = "ThaliPlanner"
user = "Travellers and people interested in Indian food and culture"
problem = (
    "Travellers often search different places to discover regional thalis, "
    "destinations, festivals, and local traditions."
)
data_source = (
    "Public tourism websites, regional food information, festival information, "
    "and sample project data"
)

print("=" * 55)
print("             THALIPLANNER - PROJECT CARD")
print("=" * 55)
print(f"Product     : {product}")
print(f"User        : {user}")
print(f"Problem     : {problem}")
print(f"Data source : {data_source}")
print("=" * 55)

name = input("What is your name? ").strip()
question = input("What would you like to know about ThaliPlanner? ").strip()

if name:
    print(f"\nHello, {name}! Welcome to {product}.")
else:
    print(f"\nWelcome to {product}!")

if question:
    print(f"Your question: {question}")
else:
    print("You did not enter a question.")
