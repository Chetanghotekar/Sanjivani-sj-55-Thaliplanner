# ThaliPlanner: 10 Real User Questions

Data available: 20 recipes in `data/records.json` with these fields only: `dish_name`, `region_or_type`, `servings`, `ingredients`, `time_and_difficulty`, `source_url`.

| # | Question a user would ask | Can the data answer it? | Expected answer / why not |
|---|---|---|---|
| 1 | Which dishes can I make with moong dal? | Yes | Moong Dal, Khichdi (both list moong dal as an ingredient) |
| 2 | What South Indian dishes do you have? | Yes | Sambar I, Rasam, Idli, Dosa I, Masala Dosa, Medu Vada (`region_or_type` = South Indian) |
| 3 | How long does Dhokla take and how hard is it? | Yes | 35 minutes, medium |
| 4 | What ingredients do I need for Paneer Butter Masala? | Yes | paneer, tomato, butter, cream, spices |
| 5 | Which recipes are easy and take 20 minutes or less? | Yes | Rasam (25 min) does not qualify; Onion Chutney (20), Coconut Chutney (15), Masala Chai I (10) do |
| 6 | **How many calories are in a Masala Dosa?** | **No** | The data has no calorie or nutrition field. The correct response is "I don't have that information", not a guess. |
| 7 | I have potatoes and onions, what can I cook? | Yes | Potato Curry (Aloo Masala), Masala Dosa (both list potatoes and onion) |
| 8 | Can you suggest a simple thali using your recipes? | Partly | Combine a dal, a vegetable curry, a rice, and a chutney, e.g. Moong Dal + Potato Curry + Indian Rice + Coconut Chutney. The data has no "thali" or meal-planning field, so this needs reasoning over several records. |
| 9 | Which Gujarati dish can I make for a snack? | Yes | Dhokla (the only Gujarati recipe). The data does not say it is a snack, so the answer should be careful. |
| 10 | Where can I find the source for the Idli recipe? | Yes | The `source_url` field of the Idli record |

## Notes

- Questions 1-6 are the questions from my project card. **Replace rows 1-5 with the exact wording from the card if it differs; keep Q6 as the one the data cannot answer.**
- Q6 is the "out-of-data" test: a good system says it does not know. A bad system invents a number.
- Q8 and Q9 are partly answerable and are included to test how the system handles gaps.
