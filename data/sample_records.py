"""Day 2/3/13: Complete curated recipe records from Wikibooks with timings, ingredients, and method."""
from __future__ import annotations

SAMPLE_RECORDS = [
    {
        "id": 1,
        "dish_name": "Moong Dal",
        "region_or_type": "Dal",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "15 minutes",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "1 cup yellow moong dal",
            "1/2 tsp turmeric powder",
            "1 tsp cumin seeds",
            "1 tbsp ghee or oil",
            "1 tsp salt",
            "3 cups water"
        ],
        "preparation_steps": [
            "Wash moong dal thoroughly and drain the water.",
            "Add dal, water, turmeric, and salt to a pot or pressure cooker.",
            "Cook until the dal is soft and tender.",
            "In a small pan, heat ghee or oil and add cumin seeds until they splutter.",
            "Pour the tempering (tadka) over the cooked dal.",
            "Garnish with chopped coriander and serve hot with steamed rice or roti."
        ],
        "time_and_difficulty": "30 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Moong_Dal"
    },
    {
        "id": 2,
        "dish_name": "Langar Dal",
        "region_or_type": "Dal",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "75 minutes",
        "soaking_time": "2 hours",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "1/2 cup whole urad dal",
            "1/2 cup chana dal",
            "1 tbsp ginger, minced",
            "1 tbsp garlic, minced",
            "2 tomatoes, chopped",
            "1 tsp garam masala",
            "2 tbsp ghee",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Wash and soak whole urad dal and chana dal for at least 2 hours.",
            "Pressure cook with water, salt, and turmeric until creamy and soft.",
            "In a pan, heat ghee and saute ginger, garlic, and chopped tomatoes.",
            "Add the spices and simmer until ghee separates from masala.",
            "Pour the masala into the cooked dal and simmer on low flame.",
            "Finish with fresh coriander and serve hot with roti."
        ],
        "time_and_difficulty": "90 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Langar_Dal"
    },
    {
        "id": 3,
        "dish_name": "Khichdi",
        "region_or_type": "Rice",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "20 minutes",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "1/2 cup rice",
            "1/2 cup yellow moong dal",
            "1/2 tsp turmeric powder",
            "1 tsp salt",
            "2 tbsp ghee",
            "1 tsp cumin seeds"
        ],
        "preparation_steps": [
            "Wash rice and moong dal together until water runs clear.",
            "Soak in water for 20 minutes and drain.",
            "Heat ghee in a pressure cooker and add cumin seeds.",
            "Add rice, dal, turmeric, salt, and 4 cups of water.",
            "Pressure cook for 3-4 whistles until soft and porridge-like.",
            "Serve warm with papad, yogurt, and pickle."
        ],
        "time_and_difficulty": "35 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Khichdi"
    },
    {
        "id": 4,
        "dish_name": "Sambar I",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "30 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "1/2 cup toor dal",
            "1 lemon-sized ball tamarind",
            "1 cup mixed vegetables (drumstick, carrot, shallots)",
            "2 tbsp sambar powder",
            "1/2 tsp turmeric powder",
            "1 tsp mustard seeds",
            "1 sprig curry leaves"
        ],
        "preparation_steps": [
            "Cook toor dal with turmeric and water until mushy; mash well.",
            "Extract tamarind juice with 1 cup warm water.",
            "Boil chopped vegetables in tamarind water with sambar powder and salt.",
            "Add mashed dal and simmer for 5-7 minutes.",
            "Temper mustard seeds and curry leaves in hot oil and pour into sambar.",
            "Serve hot with idli, dosa, or steamed rice."
        ],
        "time_and_difficulty": "45 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Sambar"
    },
    {
        "id": 5,
        "dish_name": "Rasam",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "5 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "2 ripe tomatoes, chopped",
            "1 small ball tamarind",
            "1 tsp black pepper, crushed",
            "1 tsp cumin seeds",
            "1 sprig curry leaves",
            "1/4 tsp asafoetida (hing)",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Extract tamarind juice and boil with chopped tomatoes, turmeric, and salt.",
            "Crush black pepper and cumin coarsely in a mortar.",
            "Add crushed spices and curry leaves to the simmering tomato broth.",
            "Simmer until froth rises to the surface; do not boil vigorously.",
            "Temper mustard seeds and hing in ghee and add to rasam.",
            "Garnish with coriander leaves and serve as soup or with rice."
        ],
        "time_and_difficulty": "25 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Rasam"
    },
    {
        "id": 6,
        "dish_name": "Idli",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "12 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "8 hours",
        "difficulty": "Medium",
        "ingredients": [
            "2 cups idli rice",
            "1 cup urad dal",
            "1/2 tsp fenugreek seeds",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Wash and soak rice and urad dal separately.",
            "Grind them into a smooth batter.",
            "Mix the batter and add salt.",
            "Allow the batter to ferment.",
            "Pour the batter into greased idli moulds.",
            "Steam until the idlis are cooked.",
            "Serve hot with sambar and coconut chutney."
        ],
        "time_and_difficulty": "30 minutes plus fermentation, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Idli"
    },
    {
        "id": 7,
        "dish_name": "Dosa I",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "4 hours",
        "fermentation_time": "8 hours",
        "difficulty": "Medium",
        "ingredients": [
            "3 cups parboiled rice",
            "1 cup whole white urad dal",
            "1/2 tsp fenugreek seeds",
            "1 tsp salt",
            "Oil for cooking"
        ],
        "preparation_steps": [
            "Soak rice and urad dal with fenugreek seeds in water for 4 hours.",
            "Grind to a smooth pouring consistency and ferment overnight.",
            "Heat a flat griddle (tawa) and ladle batter in a spiral outwards.",
            "Drizzle oil along the edges until golden and crisp.",
            "Fold and serve warm with coconut chutney and sambar."
        ],
        "time_and_difficulty": "30 minutes plus fermentation, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Dosa"
    },
    {
        "id": 8,
        "dish_name": "Masala Dosa",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "8 hours",
        "difficulty": "Medium",
        "ingredients": [
            "2 cups prepared dosa batter",
            "3 large potatoes, boiled and mashed",
            "1 onion, thinly sliced",
            "1 tsp mustard seeds",
            "1 sprig curry leaves",
            "1/2 tsp turmeric powder",
            "2 green chillies, chopped"
        ],
        "preparation_steps": [
            "Heat oil in a pan, add mustard seeds, curry leaves, and green chillies.",
            "Add sliced onions and saute until translucent.",
            "Add turmeric, mashed potatoes, salt, and 2 tbsp water; mix into potato masala.",
            "Spread dosa batter thinly onto a hot greased griddle.",
            "Place a spoonful of potato masala in the centre.",
            "Roll the crisp dosa and serve hot with chutney."
        ],
        "time_and_difficulty": "40 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Masala_Dosa"
    },
    {
        "id": 9,
        "dish_name": "Medu Vada",
        "region_or_type": "South Indian",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "3 hours",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "1 cup whole urad dal",
            "1 tsp black pepper, crushed",
            "1 tsp cumin seeds",
            "1 sprig curry leaves, chopped",
            "1 inch ginger, minced",
            "Oil for deep frying",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Soak urad dal in water for 3 hours and drain completely.",
            "Grind with minimal water to a fluffy, thick batter.",
            "Fold in crushed pepper, cumin, curry leaves, ginger, and salt.",
            "Shape portions into doughnuts with a hole in the center.",
            "Deep fry in medium hot oil until crisp and golden brown.",
            "Drain excess oil and serve hot with sambar and chutney."
        ],
        "time_and_difficulty": "40 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Medu_Vada"
    },
    {
        "id": 10,
        "dish_name": "Potato Curry (Aloo Masala)",
        "region_or_type": "Curry",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "4 boiled potatoes, diced",
            "1 large onion, chopped",
            "1 tsp mustard seeds",
            "1/2 tsp turmeric powder",
            "1 sprig curry leaves",
            "1 tbsp oil",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Heat oil in a pan and splutter mustard seeds and curry leaves.",
            "Saute sliced onions and green chillies until softened.",
            "Add turmeric and salt, then stir in boiled diced potatoes.",
            "Cook on low heat for 5-7 minutes so spices coat potatoes.",
            "Garnish with fresh cilantro and serve with puri or dosa."
        ],
        "time_and_difficulty": "30 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Potato_Curry"
    },
    {
        "id": 11,
        "dish_name": "Cholley",
        "region_or_type": "North Indian",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "45 minutes",
        "soaking_time": "8 hours",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "1 cup dried white chickpeas (kabuli chana)",
            "2 onions, finely chopped",
            "2 tomatoes, pureed",
            "1 tbsp ginger-garlic paste",
            "2 tbsp chole masala",
            "2 tbsp oil",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Soak chickpeas overnight and pressure cook until tender.",
            "Heat oil in a pan, add ginger-garlic paste and chopped onions until browned.",
            "Add tomato puree, chole masala, and salt; cook until oil releases.",
            "Add cooked chickpeas along with their stock and simmer for 15 minutes.",
            "Lightly mash some chickpeas to thicken gravy.",
            "Serve hot with bhature or steamed basmati rice."
        ],
        "time_and_difficulty": "60 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Chole"
    },
    {
        "id": 12,
        "dish_name": "Matar Paneer",
        "region_or_type": "North Indian",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "200g paneer cubes",
            "1 cup green peas (matar)",
            "1 onion, pureed",
            "2 tomatoes, pureed",
            "1 tsp garam masala",
            "1 tsp coriander powder",
            "2 tbsp oil"
        ],
        "preparation_steps": [
            "Shallow fry paneer cubes in oil until light golden and set aside in warm water.",
            "In the same pan, saute pureed onion and ginger-garlic paste until brown.",
            "Add tomato puree, turmeric, coriander powder, and salt; cook until thick.",
            "Add green peas and 1 cup water; simmer until peas are tender.",
            "Add paneer cubes and garam masala, simmer for 5 minutes.",
            "Garnish with coriander and serve with roti or naan."
        ],
        "time_and_difficulty": "35 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Matar_Paneer"
    },
    {
        "id": 13,
        "dish_name": "Paneer Butter Masala",
        "region_or_type": "North Indian",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "200g paneer, cubed",
            "4 tomatoes, pureed",
            "2 tbsp butter",
            "2 tbsp fresh cream",
            "1 tsp ginger-garlic paste",
            "1 tsp garam masala",
            "1 tsp kasuri methi"
        ],
        "preparation_steps": [
            "Saute onions, ginger, and garlic in a pan with butter until golden.",
            "Add tomato puree, turmeric, red chilli powder, and salt; cook until oil separates.",
            "Blend the mixture into a silky smooth gravy if desired, then return to pan.",
            "Add paneer cubes and simmer gently for 5 minutes.",
            "Stir in fresh cream, garam masala, and crushed kasuri methi.",
            "Serve warm with naan, paratha, or jeera rice."
        ],
        "time_and_difficulty": "40 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Paneer_Butter_Masala"
    },
    {
        "id": 14,
        "dish_name": "Indian Rice",
        "region_or_type": "Rice",
        "servings": 4,
        "preparation_time": "5 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "15 minutes",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "1 cup basmati rice",
            "2 cups water",
            "1 tsp salt",
            "1 tsp ghee or butter"
        ],
        "preparation_steps": [
            "Rinse basmati rice thoroughly until water is clear, then soak for 15 minutes.",
            "Bring 2 cups of water to a boil in a heavy-bottomed pot.",
            "Add drained rice, salt, and ghee to the boiling water.",
            "Reduce heat to low, cover with tight lid, and simmer for 15 minutes.",
            "Turn off heat and let sit covered for 5 minutes, then fluff with fork."
        ],
        "time_and_difficulty": "25 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Indian_Rice"
    },
    {
        "id": 15,
        "dish_name": "Coconut Rice",
        "region_or_type": "Rice",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "2 cups cooked cooled rice",
            "1/2 cup freshly grated coconut",
            "1 tsp mustard seeds",
            "1 tsp urad dal",
            "1 sprig curry leaves",
            "1 tbsp coconut oil",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Cook rice and spread on a plate to cool completely.",
            "Heat coconut oil in a pan, add mustard seeds, urad dal, and curry leaves.",
            "Add green chillies and grated coconut; saute on low heat for 2 minutes.",
            "Gently fold in the cooked rice and salt until evenly combined.",
            "Serve warm with papad, pickle, or potato curry."
        ],
        "time_and_difficulty": "30 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Coconut_Rice"
    },
    {
        "id": 16,
        "dish_name": "Onion Chutney",
        "region_or_type": "Chutney",
        "servings": 4,
        "preparation_time": "5 minutes",
        "cooking_time": "15 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "2 medium onions, sliced",
            "3 dried red chillies",
            "1 small piece tamarind",
            "1 tbsp sesame or vegetable oil",
            "1 tsp salt"
        ],
        "preparation_steps": [
            "Heat oil in a skillet and roast red chillies until fragrant.",
            "Add sliced onions and saute until softened and lightly browned.",
            "Allow the sauteed onion mixture to cool completely.",
            "Grind with tamarind, salt, and very little water to a smooth paste.",
            "Temper with mustard seeds and curry leaves in hot oil before serving."
        ],
        "time_and_difficulty": "20 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Onion_Chutney"
    },
    {
        "id": 17,
        "dish_name": "Coconut Chutney",
        "region_or_type": "Chutney",
        "servings": 4,
        "preparation_time": "5 minutes",
        "cooking_time": "10 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "1 cup fresh grated coconut",
            "2 green chillies",
            "1/2 inch ginger piece",
            "2 tbsp roasted chana dal",
            "1 tsp salt",
            "1/2 cup water"
        ],
        "preparation_steps": [
            "Place grated coconut, green chillies, ginger, roasted dal, and salt in blender.",
            "Add water gradually and grind into a slightly coarse or smooth paste.",
            "Transfer chutney to a serving bowl.",
            "Heat oil in a small ladle, crackle mustard seeds, red chilli, and curry leaves.",
            "Pour the tempering over the chutney and mix well."
        ],
        "time_and_difficulty": "15 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Coconut_Chutney"
    },
    {
        "id": 18,
        "dish_name": "Mango Chutney",
        "region_or_type": "Chutney",
        "servings": 4,
        "preparation_time": "10 minutes",
        "cooking_time": "25 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "2 semi-ripe mangoes, peeled and diced",
            "1/2 cup sugar or jaggery",
            "2 tbsp vinegar",
            "1/2 tsp red chilli powder",
            "1/2 tsp cumin powder",
            "1/2 tsp salt"
        ],
        "preparation_steps": [
            "In a saucepan, combine diced mangoes, sugar, and vinegar.",
            "Cook over medium heat until sugar dissolves and mangoes soften.",
            "Add chilli powder, cumin powder, and salt.",
            "Simmer for 15-20 minutes, stirring occasionally, until thick and jam-like.",
            "Cool completely and store in an airtight glass jar."
        ],
        "time_and_difficulty": "35 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Mango_Chutney"
    },
    {
        "id": 19,
        "dish_name": "Masala Chai I",
        "region_or_type": "Beverage",
        "servings": 2,
        "preparation_time": "3 minutes",
        "cooking_time": "7 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Easy",
        "ingredients": [
            "2 tsp black tea leaves",
            "1 cup whole milk",
            "1 cup water",
            "1 inch crushed fresh ginger",
            "2 green cardamom pods, crushed",
            "2 tsp sugar"
        ],
        "preparation_steps": [
            "In a saucepan, bring 1 cup of water to a boil with crushed ginger and cardamom.",
            "Add black tea leaves and simmer for 2 minutes to extract flavors.",
            "Pour in milk and add sugar to taste.",
            "Bring the chai to a rolling boil, reduce heat, and let it rise again.",
            "Strain through a fine mesh sieve into tea glasses and serve hot."
        ],
        "time_and_difficulty": "10 minutes, easy",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Masala_Chai"
    },
    {
        "id": 20,
        "dish_name": "Dhokla",
        "region_or_type": "Gujarati",
        "servings": 4,
        "preparation_time": "15 minutes",
        "cooking_time": "20 minutes",
        "soaking_time": "Not specified in the recipe source.",
        "fermentation_time": "Not specified in the recipe source.",
        "difficulty": "Medium",
        "ingredients": [
            "1 cup gram flour (besan)",
            "1/2 cup yogurt (curd)",
            "1 tbsp lemon juice",
            "1 tsp eno fruit salt",
            "1 tsp mustard seeds",
            "1 tbsp oil",
            "2 green chillies, slit"
        ],
        "preparation_steps": [
            "Whisk gram flour, yogurt, water, and salt into a smooth lump-free batter.",
            "Add lemon juice and Eno fruit salt right before steaming and mix gently.",
            "Pour the batter into a greased steaming pan.",
            "Steam for 15-20 minutes until a toothpick inserted comes out clean.",
            "Heat oil in a small pan, crackle mustard seeds, curry leaves, and green chillies.",
            "Pour the tempering over the steamed dhokla and cut into square pieces.",
            "Garnish with fresh coriander and serve with green chutney."
        ],
        "time_and_difficulty": "35 minutes, medium",
        "source_url": "https://en.wikibooks.org/wiki/Cookbook:Dhokla"
    }
]
