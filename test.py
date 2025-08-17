import json
import os

# # Try to load the decks file
# try:
#     with open("test.json", "r") as f:
#         data = json.load(f)
# except (json.JSONDecodeError, FileNotFoundError):
#     data = {}  # Start fresh if file is empty or missing

# # Get user input
# add_deck = input("To create a deck, choose a name:\n")
# app_deck = input("What apps would you like to add? (Separate with commas)\n")
# app_list = [app.strip() for app in app_deck.split(',')]

# # Add deck
# data[add_deck] = app_list

# # Save it
# with open("test.json", "w") as f:
#     json.dump(data, f, indent=2)

# print("LET ME COOK FRFR💀 EMOJI")
# print("your data is:")
# print(json.dumps(data, indent=2))


foods = []

give_food = input("give food (Separate with commas): \n")
foods = [app.strip() for app in give_food.split(',')]

removed_food = input("what food to remove (Separate with commas): \n")
L_foods = [app.strip() for app in removed_food.split(',')]

for x in L_foods:
    while x in foods:
        foods.remove(x)

print("Updated foods:", foods)
