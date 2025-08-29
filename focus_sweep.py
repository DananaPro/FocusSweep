import os
import psutil
import time
import threading
import customtkinter as ctk
import ctypes
import json
import sys
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")


ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x500")
app.title("Focus Sweep")



def resource_path(relative_path):
    """Get absolute path to resource (works for dev and PyInstaller exe)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app.iconbitmap(resource_path("icon.ico"))

 

# ------------------------------
# 1. Customize thresholds
# ------------------------------
MIN_RAM_MB = 80         # RAM threshold
MIN_CPU_PERCENT = 3.0   # CPU usage threshold
CHECK_INTERVAL = 5      # seconds between scans


# ------------------------------
# 3. System/process whitelist
# ------------------------------
system_whitelist = [
    # Core Windows
    "System", "System Idle Process", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "csrss.exe", "smss.exe","SystemSettings",

    # Shell & UI
    "explorer.exe", "svchost.exe", "sihost.exe", "StartMenuExperienceHost.exe",
    "ShellExperienceHost.exe", "SearchHost.exe", "TextInputHost.exe",
    "fontdrvhost.exe", "RuntimeBroker.exe", "dwm.exe", "conhost.exe",
    "taskhostw.exe",

    # Security
    "SecurityHealthService.exe", "SecurityHealthSystray.exe", "MsMpEng.exe",
    "wmiPrvSE.exe", "WerFault.exe",

    # Audio & Background
    "audiodg.exe",

    # Script tools
    "python.exe", "cmd.exe", "powershell.exe", "py.exe","Focus Sweep","GitExtensions","Git Extensions",

     # Extras
     "SignalRPG.exe", "WallpaperAlive.exe", "SignalRgb.exe",

    # # Cloud tools
    # "OneDrive.exe", "steam.exe", "steamwebhelper.exe",

    # # Development tools
     "Code.exe"
]


# Get current script's process ID to avoid closing itself
current_pid = os.getpid()
stop_requested = False

safe_apps_lower = set()
def normalize(name):
    if not name:
        return ""
    name = name.lower().replace(" ", "")
    if not name.endswith(".exe"):
        name += ".exe"
    return name

def focus_sweep_loop():
    global stop_requested
    while not stop_requested:
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                if proc.pid == current_pid:
                    continue  # never kill self
                proc_name = normalize(proc.info['name'])
                if proc_name in safe_apps_lower:
                    continue

                ram_mb = proc.info['memory_info'].rss / (1024*1024)
                cpu_percent = proc.cpu_percent(interval=0.1)

                if ram_mb > MIN_RAM_MB or cpu_percent > MIN_CPU_PERCENT:
                    try:
                        proc.terminate()
                        textbox.insert("end", f"❌ Closed: {proc.info['name']} | RAM: {ram_mb:.1f} MB | CPU: {cpu_percent:.1f}%\n")
                        textbox.see("end")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(CHECK_INTERVAL)


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

active_deck_index  = None  # Flag to track state    


def use_deck(i, button):
    global active_deck_index, safe_apps_lower, stop_requested

    try:
        with open("decks.json", "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    deck_names = list(data.keys())
    if i >= len(deck_names):
        textbox.insert("end", f"⚠️ No deck found for deck {i+1}.\n")
        textbox.see("end")
        return

    # Stop if already active
    if active_deck_index == i:
        stop_requested = True
        active_deck_index = None
        button.configure(text="Start", text_color="black", hover_color="green")
        textbox.insert("end", "🛑 Focus Sweep stopped.\n")
        textbox.see("end")
        return

    # Start new deck
    stop_requested = False
    active_deck_index = i

    # Normalize apps in the deck
    allowed_apps = [normalize(app) for app in data[deck_names[i]] if app.strip()]
    # Merge with system whitelist
    safe_apps_lower = set(normalize(app) for app in allowed_apps + system_whitelist)

    threading.Thread(target=focus_sweep_loop, daemon=True).start()

    textbox.insert("end", "🧹 Focus Sweep started!\n")
    for app_name in sorted(safe_apps_lower):
        textbox.insert("end", f" • {app_name}\n")
    textbox.see("end")

    button.configure(text="Stop ?", text_color="black", hover_color="red")



global buttons

def save_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()
    if not deck_name or not apps_raw:
        textbox.insert("end", "⚠️ Please enter deck name and at least one app.\n")
        textbox.see("end")
        return

    apps_list = [app.strip() for app in apps_raw.split(',')]

    # Load existing decks or start fresh
    try:
        with open("decks.json", "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

        # Load existing decks or start fresh
    try:
        with open("decks.json", "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    # Update deck data (add or replace)
    if deck_name in data:
        data[deck_name].extend(apps_list)
        data[deck_name] = list(set(data[deck_name]))  # Optional: remove duplicates
    else:
        data[deck_name] = apps_list

    with open("decks.json", "w") as f:
        json.dump(data, f, indent=2)

    textbox.insert("end", f"✅ Deck '{deck_name}' saved.\n")
    textbox.see("end")

    # Update button texts to match deck names
    buttons = [deck_one, deck_two, deck_three]
    deck_names = list(data.keys())

    for i, button in enumerate(buttons):
        if i < len(deck_names):
            button.configure(text=deck_names[i])
        else:
            button.configure(text="")  # clear extra buttons if fewer decks

    # Clear inputs if you want
    deck_entry.delete(0, "end")
    apps_entry.delete(0, "end")
    print(data)
    
def clear_all_decks():
    with open("decks.json", "w") as f:
        json.dump({}, f, indent=2)

    with open("decks.json", "r") as f:
        data = json.load(f)

    textbox.insert("end", "🗑️ All decks deleted.\n")
    textbox.see("end")

    for button in [deck_one, deck_two, deck_three]:
        button.configure(text="")

    print(data)

def remove_from_deck():
    deck_name = deck_entry.get().strip()  # deck to modify
    apps_raw = apps_entry.get().strip()   # reuse the same entry for removal

    if not deck_name or not apps_raw:
        textbox.insert("end", "⚠️ Enter deck name and apps to remove.\n")
        textbox.see("end")
        return

    apps_to_remove = [app.strip() for app in apps_raw.split(',')]

    # Load current decks
    try:
        with open("decks.json", "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        textbox.insert("end", "⚠️ No decks found.\n")
        textbox.see("end")
        return

    if deck_name not in data:
        textbox.insert("end", f"⚠️ Deck '{deck_name}' does not exist.\n")
        textbox.see("end")
        return

    # Remove apps
    data[deck_name] = [app for app in data[deck_name] if app not in apps_to_remove]

    with open("decks.json", "w") as f:
        json.dump(data, f, indent=2)

    textbox.insert("end", f"🗑️ Removed {apps_to_remove} from '{deck_name}'.\n")
    textbox.insert("end", f"Current apps: {data[deck_name]}\n")
    textbox.see("end")

    # Optionally clear the input after removal
    apps_entry.delete(0, "end")





action_row = ctk.CTkFrame(app, fg_color="gray25")
action_row.pack(pady=10)

save_button = ctk.CTkButton(action_row, text="Save Deck", command=save_deck)
save_button.pack(side="left", padx=5)

remove_button = ctk.CTkButton(action_row, text="Remove Apps", command=remove_from_deck)
remove_button.pack(side="left", padx=5)

clear_button = ctk.CTkButton(action_row, text="Clear All Decks", command=clear_all_decks)
clear_button.pack(side="left", padx=5)



deck_label = ctk.CTkLabel(app, text="Decks:", font=("Arial", 16))
deck_label.pack(pady=(10, 0))  # small padding above and no extra below


button_row = ctk.CTkFrame(app, fg_color="gray20")
button_row.pack(pady=5)  # slightly smaller padding since label above


deck_one = ctk.CTkButton(button_row, text="Deck 1", command=lambda: use_deck(0,deck_one))
deck_one.pack(side="left", padx=10)

deck_two = ctk.CTkButton(button_row, text="Deck 2", command=lambda: use_deck(1,deck_two))
deck_two.pack(side="left", padx=10)

deck_three = ctk.CTkButton(button_row, text="Deck 3", command=lambda: use_deck(2,deck_three))
deck_three.pack(side="left", padx=10)


try:
    with open("decks.json", "r") as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    data = {}

buttons = [deck_one, deck_two, deck_three]
deck_names = list(data.keys())

for i, button in enumerate(buttons):
    if i < len(deck_names):
        button.configure(text=deck_names[i])
    else:
        button.configure(text="")



# Create the Start button
# button = ctk.CTkButton(
#     app,
#     text="Start",
#     command=start_button,
#     text_color="black",    # Default text black
#     hover_color="green"      # Hover green for "Start" state
# )
# button.pack(pady=10)



app.mainloop()