import threading
import json
import customtkinter as ctk

ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x450")
app.title("Deck Manager")

# UI Elements
label1 = ctk.CTkLabel(app, text="Enter deck name:", font=("Arial", 14))
label1.pack(pady=(10, 0))

deck_entry = ctk.CTkEntry(app, width=300)
deck_entry.pack(pady=5)

label2 = ctk.CTkLabel(app, text="Enter apps (comma separated):", font=("Arial", 14))
label2.pack(pady=(10, 0))

apps_entry = ctk.CTkEntry(app, width=300)
apps_entry.pack(pady=5)

textbox = ctk.CTkTextbox(app, width=350, height=150)
textbox.pack(pady=10)

def save_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()
    if not deck_name:
        textbox.insert("end", "⚠️ Please enter a deck name.\n")
        textbox.see("end")
        return
    if not apps_raw:
        textbox.insert("end", "⚠️ Please enter at least one app.\n")
        textbox.see("end")
        return

    apps_list = [app.strip() for app in apps_raw.split(',')]

    # Load existing data
    try:
        with open("decks.json", "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    # Update data
    data[deck_name] = apps_list

    # Save back
    with open("decks.json", "w") as f:
        json.dump(data, f, indent=2)

    textbox.insert("end", f"✅ Deck '{deck_name}' saved with apps: {apps_list}\n")
    textbox.see("end")

    buttons = [deck_one, deck_two, deck_three]  # Assuming these are your actual button variables

    deck_names = list(data.keys())

    for i, button in enumerate(buttons):
        if i < len(deck_names):
            button.configure(text=deck_names[i])
        else:
            continue  



    # Optional: clear entries
    deck_entry.delete(0, "end")
    apps_entry.delete(0, "end")

save_button = ctk.CTkButton(app, text="Save Deck", command=save_deck)
save_button.pack(pady=10)

button_row = ctk.CTkFrame(app, fg_color="gray20")  # or any hex code like "#222222"
button_row.pack(pady=20)


deck_one = ctk.CTkButton(button_row, text="Deck 1")
deck_one.pack(side="left", padx=10)

deck_two = ctk.CTkButton(button_row, text="Deck 2")
deck_two.pack(side="left", padx=10)

deck_three = ctk.CTkButton(button_row, text="Deck 3")
deck_three.pack(side="left", padx=10)



app.mainloop()
