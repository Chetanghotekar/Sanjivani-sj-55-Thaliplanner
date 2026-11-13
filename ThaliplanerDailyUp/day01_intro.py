"""Day 1: Introduce the ThaliPlanner product."""
product = "ThaliPlanner"
user = "Students and families"
problem = "People need help deciding what Indian dish to cook."
data_source = "Wikibooks Indian recipes and curated recipe records"

print("=" * 40)
print(f"Product: {product}")
print(f"User: {user}")
print(f"Problem: {problem}")
print(f"Data source: {data_source}")
print("=" * 40)

name = input("Enter your name: ")
question = input("What recipe would you like to find? ")
print(f"Hello {name}! ThaliPlanner will help you explore recipes for: {question}")
