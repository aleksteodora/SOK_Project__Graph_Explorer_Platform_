"""
Flask app for the Graph Explorer Platform.

Mirrors the Django implementation:
- Main page view (composes platform UI fragments)
- Workspace REST API (list / create / select)
- CLI REST API (message history / execute command)
- Graph data API (current graph JSON)
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, redirect, render_template, request, session


# ── Make api package importable ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_api_src = str(PROJECT_ROOT / "api" / "src")
if _api_src not in sys.path:
    sys.path.insert(0, _api_src)


# ── Jinja2 for rendering platform template variables ──────────────────
try:
    from jinja2 import Template as JinjaTemplate

    def _render_jinja(template_str: str, **kwargs) -> str:
        return JinjaTemplate(template_str).render(**kwargs)
except ImportError:
    def _render_jinja(template_str: str, **kwargs) -> str:
        result = template_str
        for key, value in kwargs.items():
            result = result.replace("{{ " + key + " }}", value)
        return result


# ── Platform / API imports ────────────────────────────────────────────
from api import (
    Graph, Node, Edge,
    DataSourcePlugin, VisualizerPlugin, PluginParameter,
)

# The graph-platform package is named 'platform' which clashes with the
# Python stdlib module of the same name. We load it explicitly via
# importlib from known file paths.
import importlib.util as _ilu

_PLATFORM_SRC = PROJECT_ROOT / "platform" / "src" / "platform"


def _load_platform_module(name: str, py_file: str | Path):
    """Import a single module from the graph-platform source tree."""
    target = _PLATFORM_SRC / py_file
    spec = _ilu.spec_from_file_location(name, str(target))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create module spec for {name} from {target}")
    mod = _ilu.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_graph_service_mod = _load_platform_module("platform.graph_service", "graph_service.py")
_plugin_registry_mod = _load_platform_module("platform.plugin_registry", "plugin_registry.py")
_cli_mod = _load_platform_module("platform.cli", "cli.py")
_workspace_mod = _load_platform_module("platform.workspace", "workspace.py")

_load_platform_module("platform.dtos", Path("dtos") / "__init__.py")
_msg_dto_mod = _load_platform_module("platform.dtos.MessageDTO", Path("dtos") / "MessageDTO.py")
_msg_resp_dto_mod = _load_platform_module("platform.dtos.MessageResponseDTO", Path("dtos") / "MessageResponseDTO.py")

PluginRegistry = _plugin_registry_mod.PluginRegistry
Workspace = _workspace_mod.Workspace
WorkspaceError = _workspace_mod.WorkspaceError
CLI = _cli_mod.CLI
InvalidCommandError = _cli_mod.InvalidCommandError
GraphService = _graph_service_mod.GraphService
FilterParseError = _graph_service_mod.FilterParseError
FilterTypeError = _graph_service_mod.FilterTypeError
MessageDTO = _msg_dto_mod.MessageDTO
MessageResponseDTO = _msg_resp_dto_mod.MessageResponseDTO


# ── Flask app ─────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = "graph-explorer-flask-dev-key"
app.config["JSON_SORT_KEYS"] = False


# ══════════════════════════════════════════════════════════════════════
# Template helpers
# ══════════════════════════════════════════════════════════════════════

TEMPLATES_DIR = PROJECT_ROOT / "platform" / "templates"


def _read_platform_template(filename: str) -> str:
    """Read an HTML fragment from the platform templates directory."""
    filepath = TEMPLATES_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")

    alt = Path(sys.prefix) / "templates" / filename
    if alt.exists():
        return alt.read_text(encoding="utf-8")

    return ""


# ══════════════════════════════════════════════════════════════════════
# Singletons & in-memory session storage
# ══════════════════════════════════════════════════════════════════════

_registry: Optional[PluginRegistry] = None

# session_key  →  { workspace_id: Workspace }
_workspaces: dict[str, dict[str, Workspace]] = {}
# session_key  →  workspace_id
_active_ws: dict[str, str] = {}
# session_key  →  [ {text, type} ]
_cli_messages: dict[str, list[dict]] = {}


def _get_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _registry.load()
    return _registry


def _ensure_session() -> str:
    sk = session.get("session_key")
    if not sk:
        sk = str(uuid.uuid4())
        session["session_key"] = sk
    return sk


def _ws_dict(sk: str) -> dict[str, Workspace]:
    return _workspaces.setdefault(sk, {})


def _messages(sk: str) -> list[dict]:
    return _cli_messages.setdefault(sk, [])


def _active_workspace(sk: str) -> Optional[Workspace]:
    ws_id = _active_ws.get(sk)
    if ws_id:
        return _ws_dict(sk).get(ws_id)
    return None


# ══════════════════════════════════════════════════════════════════════
# Main page
# ══════════════════════════════════════════════════════════════════════

@app.get("/")
def root_redirect():
    return redirect("/graph_visualizer/", code=302)


@app.get("/graph_visualizer/")
def index():
    """Render the main Graph Explorer page with all platform UI fragments."""
    sk = _ensure_session()

    main_style = _read_platform_template("graph-visualizer-mainview-style.html")
    main_body = _read_platform_template("graph-visualizer-mainview-body.html")
    main_script = _read_platform_template("graph-visualizer-mainview-script.html")

    fv_style = _read_platform_template("graph-visualizer-filterview-style.html")
    fv_body = _read_platform_template("graph-visualizer-filterview-body.html")
    fv_script = _read_platform_template("graph-visualizer-filterview-script.html")

    ws_style = _read_platform_template("graph-visualizer-workspace-style.html")
    ws_body = _read_platform_template("graph-visualizer-workspace-body.html")
    ws_script_raw = _read_platform_template("graph-visualizer-workspace-script.html")

    cli_style = _read_platform_template("graph-visualizer-cli-style.html")
    cli_body = _read_platform_template("graph-visualizer-cli-body.html")
    cli_script_raw = _read_platform_template("graph-visualizer-cli-script.html")

    bv_style = _read_platform_template("graph-visualizer-birdview-style.html")
    bv_body = _read_platform_template("graph-visualizer-birdview-body.html")
    bv_script = _read_platform_template("graph-visualizer-birdview-script.html")

    tv_style = _read_platform_template("graph-visualizer-treeview-style.html")
    tv_body = _read_platform_template("graph-visualizer-treeview-body.html")
    tv_script = _read_platform_template("graph-visualizer-treeview-script.html")

    vp_style = _read_platform_template("graph-visualizer-vispicker-style.html")
    vp_body = _read_platform_template("graph-visualizer-vispicker-body.html")
    vp_script_raw = _read_platform_template("graph-visualizer-vispicker-script.html")

    base_url = "/graph_visualizer"

    ws_script = _render_jinja(
        ws_script_raw,
        workspaces_fetch_api=f"{base_url}/api/workspaces/",
        plugins_fetch_api=f"{base_url}/api/plugins/",
        workspace_select_api=f"{base_url}/api/workspace/select/",
        workspace_create_api=f"{base_url}/api/workspace/create/",
    )

    cli_script = _render_jinja(
        cli_script_raw,
        messages_fetch_url=f"{base_url}/api/messages/",
        message_post_url=f"{base_url}/api/message/",
    )

    vp_script = _render_jinja(
        vp_script_raw,
        visualizers_fetch_api=f"{base_url}/api/visualizers/",
        visualizer_select_api=f"{base_url}/api/visualizer/select/",
    )

    graph_html = ""
    ws = _active_workspace(sk)
    if ws and ws.is_loaded():
        try:
            graph_html = ws.render()
        except Exception:
            graph_html = ""

    active_name = ws.name if ws else ""

    context = {
        "main_style": main_style,
        "main_body": main_body,
        "main_script": main_script,
        "fv_style": fv_style,
        "fv_body": fv_body,
        "fv_script": fv_script,
        "ws_style": ws_style,
        "ws_body": ws_body,
        "ws_script": ws_script,
        "cli_style": cli_style,
        "cli_body": cli_body,
        "cli_script": cli_script,
        "bv_style": bv_style,
        "bv_body": bv_body,
        "bv_script": bv_script,
        "tv_style": tv_style,
        "tv_body": tv_body,
        "tv_script": tv_script,
        "vp_style": vp_style,
        "vp_body": vp_body,
        "vp_script": vp_script,
        "graph_html": graph_html,
        "active_workspace_name": active_name,
    }
    return render_template("index.html", **context)


# ══════════════════════════════════════════════════════════════════════
# Workspace REST API
# ══════════════════════════════════════════════════════════════════════

@app.get("/graph_visualizer/api/workspaces/")
def api_workspaces():
    sk = _ensure_session()
    data = [
        {"id": w.workspace_id, "name": w.name}
        for w in _ws_dict(sk).values()
    ]
    return jsonify(data)


@app.get("/graph_visualizer/api/plugins/")
def api_plugins():
    registry = _get_registry()
    names = registry.get_data_source_names()
    plugins = registry.get_data_sources()
    data = [
        {"id": name, "name": plugin.get_name()}
        for name, plugin in zip(names, plugins)
    ]
    return jsonify(data)


@app.get("/graph_visualizer/api/visualizers/")
def api_visualizers():
    sk = _ensure_session()
    registry = _get_registry()

    entries = []
    for name, vis in zip(registry.get_visualizer_names(), registry.get_visualizers()):
        entries.append({"id": name, "name": vis.get_name(), "obj": vis})

    ws = _active_workspace(sk)
    active_vis = ws.visualizer if ws else None

    data = []
    for e in entries:
        data.append({
            "id": e["id"],
            "name": e["name"],
            "active": (active_vis is e["obj"]) if active_vis else False,
        })
    return jsonify(data)


@app.post("/graph_visualizer/api/visualizer/select/")
def api_visualizer_select():
    sk = _ensure_session()
    body = request.get_json(silent=True) or {}
    vis_id = body.get("visualizer_id", "")

    ws = _active_workspace(sk)
    if ws is None:
        return jsonify({"error": "No active workspace."}), 400

    registry = _get_registry()

    try:
        visualizer = registry.get_visualizer(vis_id)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 400

    ws.set_visualizer(visualizer)
    return jsonify({"ok": True})


@app.post("/graph_visualizer/api/workspace/select/")
def api_workspace_select():
    sk = _ensure_session()
    body = request.get_json(silent=True) or {}
    workspace_id = body.get("workspace_id", "")

    ws = _ws_dict(sk).get(workspace_id)
    if ws is None:
        return jsonify({"error": "Workspace not found"}), 404

    _active_ws[sk] = workspace_id
    return jsonify({"ok": True})


@app.post("/graph_visualizer/api/workspace/create/")
def api_workspace_create():
    sk = _ensure_session()
    body = request.get_json(silent=True) or {}

    name = body.get("name", "").strip()
    plugin_id = body.get("plugin_id", "")
    filename = body.get("filename", "").strip()

    if not name or not plugin_id or not filename:
        return jsonify({"error": "All fields are required (name, plugin, filename)."}), 400

    registry = _get_registry()

    try:
        data_source = registry.get_data_source(plugin_id)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 400

    vis_names = registry.get_visualizer_names()
    if not vis_names:
        return jsonify({"error": "No visualizer plugin installed."}), 400
    visualizer = registry.get_visualizer(vis_names[0])

    ws_id = str(uuid.uuid4())[:8]
    ws = Workspace(workspace_id=ws_id, name=name)
    ws.set_data_source(data_source)
    ws.set_visualizer(visualizer)

    try:
        ws.load_and_render({"file_name": filename})
    except Exception as exc:
        return jsonify({"error": f"Failed to load graph: {exc}"}), 500

    _ws_dict(sk)[ws_id] = ws
    _active_ws[sk] = ws_id

    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# CLI REST API
# ══════════════════════════════════════════════════════════════════════

@app.get("/graph_visualizer/api/messages/")
def api_messages():
    sk = _ensure_session()
    return jsonify(_messages(sk))


@app.post("/graph_visualizer/api/message/")
def api_message():
    sk = _ensure_session()
    body = request.get_json(silent=True) or {}
    command = body.get("message", "").strip()

    if not command:
        return jsonify({"response": None, "error": "Empty command"})

    msgs = _messages(sk)
    msgs.append({"text": command, "type": "cli-cmd"})

    ws = _active_workspace(sk)
    if ws is None:
        err = "No active workspace. Create or select one first."
        msgs.append({"text": err, "type": "cli-err"})
        return jsonify({"response": None, "error": err})

    if not ws.is_loaded():
        err = "Workspace has no loaded graph."
        msgs.append({"text": err, "type": "cli-err"})
        return jsonify({"response": None, "error": err})

    try:
        result = ws.execute_cli(command)

        if result.strip().startswith("<script>") or result.strip().startswith("<svg"):
            friendly = "Query applied."
            msgs.append({"text": friendly, "type": "cli-out"})
            return jsonify({
                "response": friendly,
                "error": None,
                "graph_html": result,
            })

        msgs.append({"text": result, "type": "cli-out"})

        graph_html = None
        cmd_word = command.strip().split()[0] if command.strip() else ""
        if cmd_word in (
            "create-node", "create-edge", "edit-node", "edit-edge",
            "delete-node", "delete-edge", "clear",
        ):
            try:
                graph_html = ws.render()
            except Exception:
                pass

        resp = {"response": result, "error": None}
        if graph_html:
            resp["graph_html"] = graph_html
        return jsonify(resp)

    except (InvalidCommandError, WorkspaceError, ValueError,
            FilterParseError, FilterTypeError) as exc:
        err = str(exc)
        msgs.append({"text": err, "type": "cli-err"})
        return jsonify({"response": None, "error": err})
    except Exception as exc:
        err = f"Unexpected error: {exc}"
        msgs.append({"text": err, "type": "cli-err"})
        return jsonify({"response": None, "error": err})


# ══════════════════════════════════════════════════════════════════════
# Graph data API
# ══════════════════════════════════════════════════════════════════════

@app.get("/graph_visualizer/api/graph/")
def api_graph():
    sk = _ensure_session()
    ws = _active_workspace(sk)
    if ws is None or not ws.is_loaded():
        return jsonify({"nodes": [], "edges": []})
    return jsonify(ws.graph.to_dict())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
