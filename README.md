
# 💻 SpecScoreX – The Smart System Rating Engine

SpecScoreX is a lightweight yet powerful web application that analyzes and rates the performance of your computer system based on its hardware specifications. It provides two modes:
- 🌐 **Quick Scan** – Runs directly in your browser without any downloads
- ⚙️ **Full Scan** – Uses a lightweight agent (Python or PowerShell) for deeper analysis

---

## 🔧 Features

- ✅ No login or signup required
- 🌐 Quick browser-based scan using JavaScript
- 🐍 Deep system scan using Python or PowerShell agent
- 📊 Clean hardware rating based on CPU, RAM, GPU, and Disk specs
- 📥 Open-source and platform-independent

---

## 📁 Project Structure

```
/SpecScoreX/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── quick-scan.js
├── backend/
│   ├── app.py
│   ├── rating_engine.py
│   └── requirements.txt
├── agents/
│   ├── spec_collector.py      # Python-based
│   └── spec_collector.ps1     # PowerShell-based (optional)
└── README.md
```

---

## 🚀 How It Works

### 🌐 Quick Scan
1. User visits the site
2. JavaScript collects basic device info (browser APIs)
3. Info is displayed instantly in the browser

### ⚙️ Full Scan
1. User downloads and runs an agent script (Python or PowerShell)
2. The script collects system specs using `psutil`, `platform`, etc.
3. The agent sends data to the backend API via HTTP POST
4. The backend analyzes and scores the specs
5. The result is returned and displayed on the UI

---

## 🛠️ Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla or TailwindCSS)
- **Backend**: Python, Flask
- **Agent**: Python (psutil, platform), optional PowerShell
- **Hosting**: GitHub Pages (frontend), Render or Fly.io (backend)

---

## ⚙️ Backend Setup (Flask API)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

> The API will start on `http://localhost:5000/submit`

---

## 🐍 Python Agent Usage

```bash
cd agents
python spec_collector.py
```

The agent will auto-detect system specs and POST to the Flask API.

---

## 📤 Sample API JSON Payload

```json
{
  "cpu": "Intel i5-11400H",
  "ram_gb": 16,
  "gpu": "NVIDIA GTX 1650",
  "storage_type": "SSD",
  "os": "Windows 11 Pro"
}
```

---

## 🏁 Output Format (From API)

```json
{
  "score": 8.3,
  "grade": "Good",
  "suggestions": ["Upgrade GPU for gaming", "More RAM for heavy multitasking"]
}
```

---

## 📄 License

MIT License – Open to use, customize and expand.

---

## 👥 Team Members

| Name   | Role                        |
|--------|-----------------------------|
| Akarsh | Team Lead & Full Stack Dev  |
| Ajeet  | Frontend Designer           |
| Ayush  | Full Stack Support Dev      |

---

## 📌 Roadmap

- [x] Quick Scan UI
- [x] System Agent (Python)
- [x] Backend Rating Engine
- [ ] PowerShell Agent (for Windows)
- [ ] Public API Documentation
- [ ] Mobile-Optimized UI
- [ ] Export Results as PDF

---

## 📬 Contact

For contributions or feedback, reach out at: **SpecScoreX@devmail.com**  
Or raise an issue/pull request on GitHub.

---