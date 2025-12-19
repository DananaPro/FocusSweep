# 🧹 FocusSweep

**FocusSweep** is a Python script that helps you enter **focus mode** by automatically closing distracting apps that aren't on your safe list. Perfect for studying, deep work, or anytime you want to reduce digital distractions.

---

## 🚀 Features

- ✅ Whitelist only the apps you want open  
- 🚫 Auto-closes high-resource background distractions  
- 🔍 Uses RAM and CPU usage thresholds  
- 🛡️ Built-in protection so essential Windows processes **aren’t closed**  
- ⚙️ Easily customizable  
- 🎓 Premade deck **“Math”** included for focused study  

---

## 🛠️ How It Works

1. Enter the names of the apps you want to **keep open** (like `chrome`, `spotify`) — no quotes, no `.exe` needed.  
2. The script adds them to a **safe list** along with Windows system essentials.  
3. Every few seconds, it scans for open programs.  
4. Apps **not on your list** that use too much RAM or CPU get automatically closed.  
5. Use **decks** to save sets of apps for different focus sessions.  
6. Click a deck button to **start focus mode** or **stop** it.  
7. The premade deck **“Math”** is included for focused math study.  

---

## 📥 Installation

Make sure you have Python 3 installed.

Install the required dependencies:

```bash
pip install psutil customtkinter
