# 🧹 FocusSweep

**FocusSweep** is a Python script that helps you enter **focus mode** by automatically closing distracting apps that aren't on your safe list. Perfect for studying, deep work, or anytime you want to reduce digital distractions.

---

## 🚀 Features

- ✅ Whitelist only the apps you want open  
- 🚫 Auto-closes high-resource background distractions  
- 🔍 Uses RAM and CPU usage thresholds  
- 🛡️ Built-in protection so essential Windows processes **aren’t closed**  
- ⚙️ Easily customizable  

---

## 🛠️ How It Works

1. You enter the names of the apps you want to **keep open** (like `chrome`, `spotify`) — no quotes, no `.exe` needed.  
2. The script adds them to a list of essential apps.  
3. Every few seconds, it scans for open programs.  
4. If any app **not on your list** uses too much RAM or CPU, it gets closed.  

---

## 📥 Installation

Make sure you have Python 3 installed.

Install the required dependency:

```bash
pip install psutil
