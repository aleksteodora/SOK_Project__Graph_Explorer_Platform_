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
├── graph_explorer/       # Django web application
└── graph_explorer_flask/ # Flask web application
```

---

## Prerequisites

- Python 3.11+
- pip

---

## Installation

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
pip install -e ./graph_explorer

# 3. Install test dependencies
pip install pytest
```

---

## Running the Application

**Django**
```bash
cd graph_explorer
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000

**Flask**
```bash
cd graph_explorer_flask
python app.py
```
Open http://127.0.0.1:5000

---

## Running Tests

```bash
pytest
```

Run tests for a specific component:
```bash
pytest api/tests/
pytest platform/tests/
```
