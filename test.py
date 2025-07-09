import json
import os

# Try to load the decks file
try:
    with open("decks.json", "r") as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    data = {}  # Start fresh if file is empty or missing

# Get user input
add_deck = input("To create a deck, choose a name:\n")
app_deck = input("What apps would you like to add? (Separate with commas)\n")
app_list = [app.strip() for app in app_deck.split(',')]

# Add deck
data[add_deck] = app_list

# Save it
with open("decks.json", "w") as f:
    json.dump(data, f, indent=2)

print("LET ME COOK FRFR💀 EMOJI")
print("your data is:")
print(json.dumps(data, indent=2))
