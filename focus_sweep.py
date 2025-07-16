import os
import psutil
import time
import threading
import customtkinter as ctk
import ctypes
import json
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")


ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x500")
app.title("Focus Sweep")
app.iconbitmap("logo.ico")  # ← your logo here!
 

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
    "python.exe", "cmd.exe", "powershell.exe", "py.exe","Focus Sweep",

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
def focus_sweep_loop():
    try:
        while not stop_requested:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    if proc.pid == current_pid:
                        continue
                    name = proc.info['name']
                    if name is None:
                        continue
                    if name.lower() in safe_apps_lower:
                        continue
                    ram_mb = proc.info['memory_info'].rss / (1024 * 1024)
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    if (ram_mb > MIN_RAM_MB or cpu_percent > MIN_CPU_PERCENT) and not stop_requested:
                        try:
                            proc.terminate()
                            textbox.insert("end", f"❌ Closed: {name} | RAM: {ram_mb:.1f} MB | CPU: {cpu_percent:.1f}%\n")
                            textbox.see("end")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Focus mode stopped by user. Exiting...")




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
    
    with open("decks.json", "r") as f:
        data = json.load(f)
    deck_names = list(data.keys())

    if i >= len(deck_names):
        # No deck saved for this button index
        textbox.insert("end", f"⚠️ No deck found for deck {i+1}.\n")
        textbox.see("end")
        return
    
    try:
        apps = data[deck_names[i]]
    except IndexError:
        apps = []

    

    if active_deck_index == i:
        # Stop current active deck
        stop_requested = True
        active_deck_index = None
        button.configure(
            text="Start",
            text_color="black",
            hover_color="green"
        )
        textbox.insert("end", "🛑 Focus Sweep stopped.\n")
        textbox.see("end")
        return

    # If another deck was active, you might want to reset its button here

    # Start new deck
    stop_requested = False
    apps = data[deck_names[i]]
    allowed_apps = [app.strip().lower() + ".exe" for app in apps]
    safe_apps = set(allowed_apps + system_whitelist)
    safe_apps_lower = set(app.lower() for app in safe_apps)

    active_deck_index = i  # Set active deck to current

    threading.Thread(target=focus_sweep_loop, daemon=True).start()

    textbox.insert("end", "🧹 Focus Sweep started!\n")
    for app_name in safe_apps:
        textbox.insert("end", f" • {app_name}\n")
    textbox.see("end")
    print(data)

    button.configure(
        text="Stop ?",
        text_color="black",
        hover_color="red"
    )



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




save_button = ctk.CTkButton(app, text="Save Deck", command=save_deck)
save_button.pack(pady=10)

button_row = ctk.CTkFrame(app, fg_color="gray20")
button_row.pack(pady=20)


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


save_button = ctk.CTkButton(app, text="clear_all_decks", command=clear_all_decks)
save_button.pack(pady=10)

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