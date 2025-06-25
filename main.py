import os
import psutil
import time

# ------------------------------
# 1. Customize thresholds
# ------------------------------
MIN_RAM_MB = 80         # RAM threshold
MIN_CPU_PERCENT = 3.0   # CPU usage threshold
CHECK_INTERVAL = 5      # seconds between scans

# ------------------------------
# 2. User-defined whitelist
# ------------------------------
user_input = input("🟢 Which apps do you want to keep open? (name without .exe, comma-separated): ").lower().split(',')
allowed_apps = [app.strip() + ".exe" for app in user_input]

# ------------------------------
# 3. System/process whitelist
# ------------------------------
system_whitelist = [
    # Core Windows
    "System", "System Idle Process", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "csrss.exe", "smss.exe",

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
    "python.exe", "cmd.exe", "powershell.exe", "py.exe",

    # Extras
    "Spotify.exe", "SignalRPG.exe", "WallpaperAlive.exe", "SignalRgb.exe","Acrobat.exe",

    # Cloud tools
    "OneDrive.exe", "steam.exe", "steamwebhelper.exe",

    # Development tools
    "Code.exe"
]


# Combine whitelists
safe_apps = set(allowed_apps + system_whitelist)

# Create lowercase safe app names for case-insensitive matching
safe_apps_lower = set(app.lower() for app in safe_apps)

# ------------------------------
# 4. Confirm final safe list
# ------------------------------
print("\n✅ Allowed apps (these will stay open):")
for app in safe_apps:
    print("   •", app)

confirm = input("\n⚠️  Are you SURE you want to close everything else and keep checking constantly? (yes/no): ").strip().lower()
if confirm != "yes":
    print("❌ Action canceled. No apps were closed.")
    exit()

# Get current script's process ID to avoid closing itself
current_pid = os.getpid()

print("\n🧹 Focus mode activated. Press Ctrl+C to stop.\n")

# ------------------------------
# 5. Continuous close distractions
# ------------------------------
try:
    while True:
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                # Skip this script's own process
                if proc.pid == current_pid:
                    continue

                name = proc.info['name']
                if name is None:
                    continue

                # Case-insensitive check
                if name.lower() in safe_apps_lower:
                    continue

                ram_mb = proc.info['memory_info'].rss / (1024 * 1024)
                cpu_percent = proc.cpu_percent(interval=0.1)

                if ram_mb > MIN_RAM_MB or cpu_percent > MIN_CPU_PERCENT:
                    proc.terminate()
                    print(f"❌ Closed: {name} | RAM: {ram_mb:.1f} MB | CPU: {cpu_percent:.1f}%")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 Focus mode stopped by user. Exiting...")
