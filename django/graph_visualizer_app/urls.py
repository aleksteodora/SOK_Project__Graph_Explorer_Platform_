from django.urls import path
from . import views

urlpatterns = [
    # ── Main page ─────────────────────────────────────────────────────
    path("", views.index, name="index"),

    # ── Workspace API ─────────────────────────────────────────────────
    path("api/workspaces/",        views.api_workspaces,       name="api_workspaces"),
    path("api/plugins/",           views.api_plugins,          name="api_plugins"),
    path("api/visualizers/",       views.api_visualizers,      name="api_visualizers"),
    path("api/workspace/select/",  views.api_workspace_select, name="api_workspace_select"),
    path("api/workspace/create/",  views.api_workspace_create, name="api_workspace_create"),
    path("api/visualizer/select/", views.api_visualizer_select, name="api_visualizer_select"),

    # ── CLI API ───────────────────────────────────────────────────────
    path("api/messages/",          views.api_messages,         name="api_messages"),
    path("api/message/",           views.api_message,          name="api_message"),

    # ── Graph data API ────────────────────────────────────────────────
    path("api/graph/",             views.api_graph,            name="api_graph"),
]

