# Project Delivery Accelerator Engine

An interactive project delivery dashboard that helps you track epics, stories, resources, NFR gates, and timelines — with an AI assistant that can answer questions about your project using your own uploaded documents.

Supports up to **5 projects**, runs entirely on your laptop (no internet required), and works with local AI via OLLAMA, AWS Bedrock, or your uploaded files alone.

---

## What You Can Do

- Track up to 5 projects, each with their own files and settings
- Upload your project artefacts (SOW, transcripts, CSVs, presentations, etc.)
- Choose which uploaded files feed into each dashboard tab
- Ask the AI assistant questions about your project
- Choose your AI mode: local OLLAMA model, AWS Bedrock, or files-only (no AI)
- View Gantt charts, NFR gates, dependency diagrams, resource plans, and more
- Everything persists on your machine until you delete it

---

## Installation (Step by Step)

### Step 1 — Install Python

1. Go to https://www.python.org/downloads/
2. Click **Download Python 3.11** (or newer)
3. Run the installer
   - ✅ On Windows: tick **"Add Python to PATH"** before clicking Install
4. Open a terminal (search "Terminal" on Mac, "Command Prompt" or "PowerShell" on Windows)
5. Verify it worked:
   ```
   python --version
   ```
   You should see something like `Python 3.11.x`

---

### Step 2 — Download This Project

**Option A — If you have Git installed:**
```
git clone https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine.git
cd Project_Delivery_Accelerator_Engine
```

**Option B — Download as ZIP:**
1. Go to https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine
2. Click the green **Code** button → **Download ZIP**
3. Unzip the file
4. Open a terminal and navigate into the folder:
   ```
   cd Project_Delivery_Accelerator_Engine
   ```

---

### Step 3 — Start the Dashboard

```
python server.py
```

Then open your browser and go to:
```
http://localhost:8888
```

That's it — the dashboard is running locally on your machine.

To stop it, press `Ctrl + C` in the terminal.

---

## Using OLLAMA (Local AI — No Internet Required)

OLLAMA lets you run AI models entirely on your own machine. No data leaves your computer.

### Install OLLAMA

1. Go to https://ollama.com/download
2. Download and install for your operating system (Mac, Windows, or Linux)
3. Once installed, open a terminal and download a model. We recommend starting with:
   ```
   ollama pull llama3
   ```
   This downloads the Llama 3 model (~4 GB). Other good options:
   - `ollama pull mistral` — fast and lightweight
   - `ollama pull phi3` — very small, good for low-spec machines
   - `ollama pull llama3:70b` — most capable, needs 32 GB+ RAM

4. OLLAMA runs automatically in the background after installation. You can verify it's running by visiting http://localhost:11434 in your browser — you should see `Ollama is running`.

### Connect OLLAMA to the Dashboard

1. Start the dashboard (`python server.py`)
2. Open http://localhost:8888
3. Create or select a project
4. In the top bar, change the **LLM** dropdown from `Bedrock` to **🦙 OLLAMA (local)**
5. A **Model** input box will appear — type the model name you downloaded (e.g. `llama3`)
6. The AI chat and content generation will now use your local model

> **Tip:** If OLLAMA is running on a different machine or port, set the environment variable before starting the server:
> ```
> OLLAMA_URL=http://192.168.1.10:11434 python server.py
> ```

---

## AI Modes Explained

| Mode | What it does | Needs internet? |
|------|-------------|-----------------|
| ☁️ **Bedrock (Nova Pro)** | Uses AWS Bedrock (Amazon Nova Pro model). Requires AWS credentials configured. | Yes |
| 🦙 **OLLAMA (local)** | Uses a model running on your machine via OLLAMA. | No |
| 📄 **Files Only** | No AI — shows the raw content of your enabled files. | No |
| 📄+🦙 **Files + OLLAMA** | Uses OLLAMA with your uploaded files as context. | No |

---

## Uploading Project Files

1. Select your project from the top bar
2. Click **📁 Files** in the top right
3. Click **Choose Files** and select your documents (SOW, transcripts, CSVs, etc.)
4. Click **Upload**
5. Once uploaded, tick the checkboxes next to each file to enable them for specific dashboard tabs (Gantt, Gates, Resources, etc.)

Supported file types: `.txt`, `.pdf`, `.csv`, `.docx`, `.pptx`, `.xlsx`, `.md`, `.json`, `.xml`, `.drawio`

---

## Managing Projects

- Click **+ New** in the top bar to create a project (max 5)
- Click a project name to switch to it
- Click the **✕** next to a project name to delete it and all its files
- Each project remembers its own LLM setting, uploaded files, and artifact toggles

---

## Diagram Viewer

The **Diagram Editor** tab shows your `.drawio` diagrams as XML. You can:
- **Copy XML** to clipboard and paste into [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) or https://app.diagrams.net
- **Download .drawio** to open directly in draw.io desktop

This works fully offline.

---

## Project Structure

```
Project_Delivery_Accelerator_Engine/
├── server.py                   # Main server — run this
├── project_manager.py          # Project persistence (5 projects, file uploads)
├── projects.json               # Your saved projects (auto-created)
├── uploads/                    # Your uploaded files (auto-created)
├── stories_data.py             # Story definitions
├── gates_data.py               # NFR gate matrix
├── migration_dashboard/        # Alternate entry point (same server)
├── tests/                      # Automated tests
└── sample_data/                # Example input files
```

---

## Troubleshooting

**"python: command not found"**
Try `python3 server.py` instead. On some systems Python 3 is called `python3`.

**Port 8888 already in use**
Change the port by editing `PORT = 8888` near the top of `server.py` to any free port (e.g. `8080`).

**OLLAMA not responding**
Make sure OLLAMA is running. Open a terminal and run `ollama serve` if it isn't started automatically.

**AWS Bedrock errors**
You need AWS credentials configured. Run `aws configure` and enter your Access Key, Secret Key, and region (`us-east-1`). Bedrock must be enabled in your AWS account.

**Dashboard shows old version after update**
Hard-refresh your browser: `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac).

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```
