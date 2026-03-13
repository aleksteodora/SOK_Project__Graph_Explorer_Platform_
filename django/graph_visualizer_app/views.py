"""
Django views for the Graph Explorer Platform.

Provides:
- Main page view (composes all platform UI fragments)
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

from django.http import JsonResponse
from django.shortcuts import render

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Jinja2 for rendering platform template variables ──────────────────
try:
    from jinja2 import Template as JinjaTemplate

    def _render_jinja(template_str: str, **kwargs) -> str:
        return JinjaTemplate(template_str).render(**kwargs)
except ImportError:
    # Fallback: simple string replacement
    def _render_jinja(template_str: str, **kwargs) -> str:
        result = template_str
        for key, value in kwargs.items():
            result = result.replace("{{ " + key + " }}", value)
        return result

# ── Platform / API imports ────────────────────────────────────────────

# Use normal imports from local project sources even when not installed in venv.
# Importing through `src.platform` avoids the stdlib `platform` name clash.
_platform_project_dir = PROJECT_ROOT / "platform"
if _platform_project_dir.exists():
    sys.path.insert(0, str(_platform_project_dir))

from src.platform import GraphService, FilterParseError, FilterTypeError
from src.platform.plugin_registry import PluginRegistry
from src.platform.workspace import Workspace, WorkspaceError
from src.platform.cli import CLI, InvalidCommandError
from src.platform.dtos.MessageDTO import MessageDTO
from src.platform.dtos.MessageResponseDTO import MessageResponseDTO

# ══════════════════════════════════════════════════════════════════════
# Template helpers
# ══════════════════════════════════════════════════════════════════════

TEMPLATES_DIR = PROJECT_ROOT / "platform" / "templates"


def _read_platform_template(filename: str) -> str:
    """Read an HTML fragment from the platform templates directory."""
    filepath = TEMPLATES_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    # Fallback: check sys.prefix (installed location)
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


def _ensure_session(request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


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
# Main page view
# ══════════════════════════════════════════════════════════════════════

def index(request):
    """Render the main Graph Explorer page with all platform UI fragments."""
    sk = _ensure_session(request)

    # ── Read platform template fragments ──────────────────────────────
    main_style  = _read_platform_template("graph-visualizer-mainview-style.html")
    main_body   = _read_platform_template("graph-visualizer-mainview-body.html")
    main_script = _read_platform_template("graph-visualizer-mainview-script.html")

    fv_style      = _read_platform_template("graph-visualizer-filterview-style.html")
    fv_body       = _read_platform_template("graph-visualizer-filterview-body.html")
    fv_script_raw = _read_platform_template("graph-visualizer-filterview-script.html")

    ws_style      = _read_platform_template("graph-visualizer-workspace-style.html")
    ws_body       = _read_platform_template("graph-visualizer-workspace-body.html")
    ws_script_raw = _read_platform_template("graph-visualizer-workspace-script.html")

    cli_style      = _read_platform_template("graph-visualizer-cli-style.html")
    cli_body       = _read_platform_template("graph-visualizer-cli-body.html")
    cli_script_raw = _read_platform_template("graph-visualizer-cli-script.html")

    bv_style  = _read_platform_template("graph-visualizer-birdview-style.html")
    bv_body   = _read_platform_template("graph-visualizer-birdview-body.html")
    bv_script = _read_platform_template("graph-visualizer-birdview-script.html")

    tv_style  = _read_platform_template("graph-visualizer-treeview-style.html")
    tv_body   = _read_platform_template("graph-visualizer-treeview-body.html")
    tv_script = _read_platform_template("graph-visualizer-treeview-script.html")

    vp_style      = _read_platform_template("graph-visualizer-vispicker-style.html")
    vp_body       = _read_platform_template("graph-visualizer-vispicker-body.html")
    vp_script_raw = _read_platform_template("graph-visualizer-vispicker-script.html")

    # ── Render Jinja2 variables in workspace & CLI & vispicker scripts
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

    fv_script = _render_jinja(
        fv_script_raw,
        message_post_url=f"{base_url}/api/message/",
        queries_reset_url=f"{base_url}/api/queries/reset/",
    )

    # ── Render graph visualization (if workspace is active) ───────────
    graph_html = ""
    ws = _active_workspace(sk)
    if ws and ws.is_loaded():
        try:
            graph_html = ws.render()
        except Exception:
            graph_html = ""

    # ── Active workspace info ─────────────────────────────────────────
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
    return render(request, "graph_visualizer_app/index.html", context)


# ══════════════════════════════════════════════════════════════════════
# Workspace REST API
# ══════════════════════════════════════════════════════════════════════

def api_workspaces(request):
    """GET → list of workspaces [{id, name}, …]"""
    sk = _ensure_session(request)
    data = [
        {"id": w.workspace_id, "name": w.name}
        for w in _ws_dict(sk).values()
    ]
    return JsonResponse(data, safe=False)


def api_plugins(request):
    """GET → list of data-source plugins [{id, name}, …]"""
    registry = _get_registry()
    names = registry.get_data_source_names()
    plugins = registry.get_data_sources()
    data = [
        {"id": name, "name": plugin.get_name()}
        for name, plugin in zip(names, plugins)
    ]
    return JsonResponse(data, safe=False)


def api_visualizers(request):
    """GET → list of visualizer plugins [{id, name, active}, …]"""
    sk = _ensure_session(request)
    registry = _get_registry()

    # Collect all available visualizers (registered plugins only)
    entries = []
    for name, vis in zip(registry.get_visualizer_names(),
                         registry.get_visualizers()):
        entries.append({"id": name, "name": vis.get_name(), "obj": vis})


    # Figure out which one is active on the current workspace
    ws = _active_workspace(sk)
    active_vis = ws.visualizer if ws else None

    data = []
    for e in entries:
        data.append({
            "id":     e["id"],
            "name":   e["name"],
            "active": (active_vis is e["obj"]) if active_vis else False,
        })
    return JsonResponse(data, safe=False)


def api_visualizer_select(request):
    """POST {visualizer_id} → change visualizer on the active workspace, re-render."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    sk = _ensure_session(request)
    body = json.loads(request.body)
    vis_id = body.get("visualizer_id", "")

    ws = _active_workspace(sk)
    if ws is None:
        return JsonResponse({"error": "No active workspace."}, status=400)

    registry = _get_registry()

    # Resolve the visualizer
    try:
        visualizer = registry.get_visualizer(vis_id)
    except KeyError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    ws.set_visualizer(visualizer)
    return JsonResponse({"ok": True})


def api_workspace_select(request):
    """POST {workspace_id} → activate an existing workspace."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    sk = _ensure_session(request)
    body = json.loads(request.body)
    workspace_id = body.get("workspace_id", "")

    ws = _ws_dict(sk).get(workspace_id)
    if ws is None:
        return JsonResponse({"error": "Workspace not found"}, status=404)

    _active_ws[sk] = workspace_id
    return JsonResponse({"ok": True})


def api_workspace_create(request):
    """POST {name, plugin_id, filename} → create workspace, load graph."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    sk = _ensure_session(request)
    body = json.loads(request.body)

    name      = body.get("name", "").strip()
    plugin_id = body.get("plugin_id", "")
    filename  = body.get("filename", "").strip()

    if not name or not plugin_id or not filename:
        return JsonResponse(
            {"error": "All fields are required (name, plugin, filename)."},
            status=400,
        )

    registry = _get_registry()

    # Resolve data-source plugin
    try:
        data_source = registry.get_data_source(plugin_id)
    except KeyError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    # Resolve visualizer (first available)
    vis_names = registry.get_visualizer_names()
    if not vis_names:
        return JsonResponse(
            {"error": "No visualizer plugin installed."},
            status=400,
        )
    visualizer = registry.get_visualizer(vis_names[0])

    # Create workspace
    ws_id = str(uuid.uuid4())[:8]
    ws = Workspace(workspace_id=ws_id, name=name)
    ws.set_data_source(data_source)
    ws.set_visualizer(visualizer)

    try:
        ws.load_and_render({"file_name": filename})
    except Exception as exc:
        return JsonResponse(
            {"error": f"Failed to load graph: {exc}"},
            status=500,
        )

    _ws_dict(sk)[ws_id] = ws
    _active_ws[sk] = ws_id

    return JsonResponse({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# CLI REST API
# ══════════════════════════════════════════════════════════════════════

def api_messages(request):
    """GET → list of past CLI messages [{text, type}, …]"""
    sk = _ensure_session(request)
    return JsonResponse(_messages(sk), safe=False)


def api_message(request):
    """POST {message} → execute CLI command, return {response, error}."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    sk = _ensure_session(request)
    body = json.loads(request.body)
    command = body.get("message", "").strip()
    silent = body.get("silent") is True

    if not command:
        return JsonResponse({"response": None, "error": "Empty command"})

    msgs = _messages(sk)
    if not silent:
        msgs.append({"text": command, "type": "cli-cmd"})

    # Need an active workspace
    ws = _active_workspace(sk)
    if ws is None:
        err = "No active workspace. Create or select one first."
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})

    if not ws.is_loaded():
        err = "Workspace has no loaded graph."
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})

    try:
        result = ws.execute_cli(command)

        # search / filter commands return rendered HTML directly
        if result.strip().startswith("<script>") or result.strip().startswith("<svg"):
            friendly = "Query applied."
            if not silent:
                msgs.append({"text": friendly, "type": "cli-out"})
            return JsonResponse({
                "response": friendly, "error": None,
                "graph_html": result,
            })

        # CRUD commands (create-node, delete-node, edit-node, …)
        # return text — but the graph was modified, so re-render it
        if not silent:
            msgs.append({"text": result, "type": "cli-out"})

        # Re-render for commands that modify the graph
        graph_html = None
        cmd_word = command.strip().split()[0] if command.strip() else ""
        if cmd_word in ("create-node", "create-edge", "edit-node",
                        "edit-edge", "delete-node", "delete-edge", "clear"):
            try:
                graph_html = ws.render()
            except Exception:
                pass

        resp = {"response": result, "error": None}
        if graph_html:
            resp["graph_html"] = graph_html
        return JsonResponse(resp)

    except (InvalidCommandError, WorkspaceError, ValueError,
            FilterParseError, FilterTypeError) as exc:
        err = str(exc)
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})
    except Exception as exc:
        err = f"Unexpected error: {exc}"
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})


def api_queries_reset(request):
    """POST → reset active query chain and return freshly rendered graph HTML."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    sk = _ensure_session(request)
    body = json.loads(request.body)
    silent = body.get("silent") is True

    msgs = _messages(sk)
    ws = _active_workspace(sk)
    if ws is None:
        err = "No active workspace. Create or select one first."
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})

    if not ws.is_loaded():
        err = "Workspace has no loaded graph."
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})

    try:
        graph_html = ws.reset()
        response = "Queries reset."
        if not silent:
            msgs.append({"text": response, "type": "cli-out"})
        return JsonResponse({
            "response": response,
            "error": None,
            "graph_html": graph_html,
        })
    except (WorkspaceError, ValueError,
            FilterParseError, FilterTypeError) as exc:
        err = str(exc)
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})
    except Exception as exc:
        err = f"Unexpected error: {exc}"
        if not silent:
            msgs.append({"text": err, "type": "cli-err"})
        return JsonResponse({"response": None, "error": err})


# ══════════════════════════════════════════════════════════════════════
# Graph data API
# ══════════════════════════════════════════════════════════════════════

def api_graph(request):
    """GET → current graph as JSON (nodes + edges)."""
    sk = _ensure_session(request)
    ws = _active_workspace(sk)
    if ws is None or not ws.is_loaded():
        return JsonResponse({"nodes": [], "edges": []})
    return JsonResponse(ws.graph.to_dict())
