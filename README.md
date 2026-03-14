# Graph Explorer Platform

A modular, plugin-based platform for parsing, modeling, visualizing, searching, and manipulating graph structures. Supports multiple data sources and visualization styles, with both Django and Flask web interfaces.

---

## Team

| Student | Index |
|---------|-------|
| Teodora Aleksic | SV7/2023  |
| Lenka Nikolic   | SV16/2023 |
| Igor Maljik     | SV37/2023 |
| Lazar Jovic     | SV43/2023 |
| Vukasin Vujovic | SV11/2023 |

---

## Project Structure

```
graph-explorer-platform/
├── api/                  # Graph model and plugin interfaces
├── platform/             # GraphService, Workspace, CLI, PluginRegistry
├── json_plugin/          # Data source plugin — JSON
├── xml_plugin/           # Data source plugin — XML
├── csv_plugin/           # Data source plugin — CSV
├── simple_visualizer/    # Visualizer plugin — Simple (force layout)
├── block_visualizer/     # Visualizer plugin — Block
├── django/               # Django web application
└── flask/                # Flask web application
```

---

## Prerequisites

- Python 3.11+
- pip

---

## Running the Application

### Django

**Linux / macOS**
```bash
chmod +x run_django.sh
./run_django.sh
```

**Windows (PowerShell)**
```powershell
.\run_django.ps1
```

Open http://127.0.0.1:8000

---

### Flask

**Linux / macOS**
```bash
chmod +x run_flask.sh
./run_flask.sh
```

**Windows (PowerShell)**
```powershell
.\run_flask.ps1
```

Open http://127.0.0.1:5000

---

### Manual Setup (alternative)

If you prefer to set up manually:
```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 2. Install components (order matters — dependencies first)
pip install -e ./api
pip install -e ./platform
pip install -e ./json_plugin
pip install -e ./xml_plugin
pip install -e ./csv_plugin
pip install -e ./simple_visualizer
pip install -e ./block_visualizer

# 3. Run Django
cd django
python manage.py migrate
python manage.py runserver

# or Run Flask
cd flask
python app.py
```

---

## Running Tests

**Linux / macOS**
```bash
chmod +x test.sh
./test.sh
```

**Windows (PowerShell)**
```powershell
.\test.ps1
```

The test scripts will automatically set up the virtual environment, install all dependencies, and run the full test suite.

---
