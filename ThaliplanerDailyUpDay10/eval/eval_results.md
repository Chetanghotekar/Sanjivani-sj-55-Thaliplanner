# ThaliPlanner Retrieval Evaluation

- Dataset: `eval/eval_set.json` (15 rows)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Metric: question-level accuracy; every expected term must occur in retrieved top-k evidence. Q6 is correct only when it abstains.

| Configuration | Chunk size | Overlap | Top-k | Chunks | Passed | Accuracy | Evidence / abstention recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Config A | 700 | 100 | 3 | 57 | 10/15 | 66.7% | 76.2% |
| Config B | 900 | 120 | 5 | 49 | 11/15 | 73.3% | 78.6% |

**Winner: Config B**

## Config A details

- **Q1 [FAIL]:** Which dishes can I make with moong dal?
  - Missing evidence terms: Khichdi
- **Q2 [PASS]:** What South Indian dishes do you have?
- **Q3 [PASS]:** How long does Dhokla take and how hard is it?
- **Q4 [PASS]:** What ingredients do I need for Paneer Butter Masala?
- **Q5 [FAIL]:** Which recipes are easy and take 20 minutes or less?
  - Missing evidence terms: Onion Chutney, Coconut Chutney, Masala Chai I
- **Q6 [PASS]:** How many calories are in a Masala Dosa?
- **Q7 [FAIL]:** I have potatoes and onions, what can I cook?
  - Missing evidence terms: Masala Dosa
- **Q8 [FAIL]:** Can you suggest a simple thali using your recipes?
  - Missing evidence terms: Potato Curry, Indian Rice, Coconut Chutney
- **Q9 [PASS]:** Which Gujarati dish can I make for a snack?
- **Q10 [PASS]:** Where can I find the source for the Idli recipe?
- **Q11 [PASS]:** Which recipes use coconut?
- **Q12 [FAIL]:** Suggest a quick drink from the recipe collection.
  - Missing evidence terms: Masala Chai I, 10 minutes
- **Q13 [PASS]:** Which recipes contain paneer?
- **Q14 [PASS]:** What is the serving count for Moong Dal?
- **Q15 [PASS]:** Which chutneys are available?

## Config B details

- **Q1 [PASS]:** Which dishes can I make with moong dal?
- **Q2 [PASS]:** What South Indian dishes do you have?
- **Q3 [PASS]:** How long does Dhokla take and how hard is it?
- **Q4 [PASS]:** What ingredients do I need for Paneer Butter Masala?
- **Q5 [FAIL]:** Which recipes are easy and take 20 minutes or less?
  - Missing evidence terms: Onion Chutney, Coconut Chutney, Masala Chai I
- **Q6 [PASS]:** How many calories are in a Masala Dosa?
- **Q7 [FAIL]:** I have potatoes and onions, what can I cook?
  - Missing evidence terms: Masala Dosa
- **Q8 [FAIL]:** Can you suggest a simple thali using your recipes?
  - Missing evidence terms: Potato Curry, Indian Rice, Coconut Chutney
- **Q9 [PASS]:** Which Gujarati dish can I make for a snack?
- **Q10 [PASS]:** Where can I find the source for the Idli recipe?
- **Q11 [PASS]:** Which recipes use coconut?
- **Q12 [FAIL]:** Suggest a quick drink from the recipe collection.
  - Missing evidence terms: Masala Chai I, 10 minutes
- **Q13 [PASS]:** Which recipes contain paneer?
- **Q14 [PASS]:** What is the serving count for Moong Dal?
- **Q15 [PASS]:** Which chutneys are available?
