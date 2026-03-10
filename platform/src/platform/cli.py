from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Tuple

from api import Graph, Node, Edge
from .graph_service import GraphService, FilterParseError, FilterTypeError


class CLI:
    """
    Command Line Interface for graph manipulation.

    Parses text commands entered by the user in the terminal UI
    and delegates to GraphService for execution.
    All commands operate on the base graph in the workspace.
    """

    HELP_TEXT = """Available commands:
  create-node --<type> name=value ...
  create-edge <source_id> <target_id> [--directed] [--<type> name=value ...]
  edit-node <node_id> --<type> name=value ...
  edit-edge <edge_id> --<type> name=value ...
  delete-node <node_id>
  delete-edge <edge_id>
  search <query>
  filter <attribute> <comparator> <value>
  clear
  help

Attribute types: --int  --float  --string  --date (DD.MM.YYYY)
"""

    @staticmethod
    def parse_command(graph: Graph, command: str) -> str:
        """Parses and executes a command string on the given graph."""
        command = command.strip()
        if not command:
            return ""

        tokens = CLI._tokenize(command)
        if not tokens:
            return ""

        cmd = tokens[0]
        args = tokens[1:]

        match cmd:
            case "create-node":
                return CLI._create_node(graph, args)
            case "create-edge":
                return CLI._create_edge(graph, args)
            case "edit-node":
                return CLI._edit_node(graph, args)
            case "edit-edge":
                return CLI._edit_edge(graph, args)
            case "delete-node":
                return CLI._delete_node(graph, args)
            case "delete-edge":
                return CLI._delete_edge(graph, args)
            case "search":
                return CLI._search(args)
            case "filter":
                return CLI._filter(args)
            case "clear":
                GraphService.clear_graph(graph)
                return "Graph cleared."
            case "help":
                return CLI.HELP_TEXT
            case _:
                raise InvalidCommandError(
                    f"Unknown command: '{cmd}'. Type 'help' for available commands."
                )

    @staticmethod
    def _create_node(graph: Graph, args: List[str]) -> str:
        attributes = CLI._parse_attributes(args)
        node_id = CLI._generate_node_id(graph)
        node = GraphService.create_node(graph, node_id, attributes)
        return f"Created node '{node.node_id}' with attributes: {node.attributes}"

    @staticmethod
    def _create_edge(graph: Graph, args: List[str]) -> str:
        if len(args) < 2:
            raise InvalidCommandError(
                "create-edge requires source and target node IDs.\n"
                "Usage: create-edge <source_id> <target_id> [--directed] [--<type> name=value ...]"
            )

        source_id = args[0]
        target_id = args[1]
        rest = args[2:]

        directed = False
        if "--directed" in rest:
            directed = True
            rest = [a for a in rest if a != "--directed"]

        attributes = CLI._parse_attributes(rest)
        edge_id = CLI._generate_edge_id(graph)
        edge = GraphService.create_edge(
            graph, edge_id, source_id, target_id,
            directed=directed, attributes=attributes
        )
        arrow = "→" if edge.directed else "—"
        return (
            f"Created edge '{edge.edge_id}': "
            f"{edge.source.node_id} {arrow} {edge.target.node_id}"
        )

    @staticmethod
    def _edit_node(graph: Graph, args: List[str]) -> str:
        if not args:
            raise InvalidCommandError(
                "edit-node requires a node ID.\n"
                "Usage: edit-node <node_id> --<type> name=value ..."
            )
        node_id = args[0]
        attributes = CLI._parse_attributes(args[1:])
        if not attributes:
            raise InvalidCommandError(
                "edit-node requires at least one attribute to update."
            )
        node = GraphService.edit_node(graph, node_id, attributes)
        return f"Updated node '{node.node_id}': {node.attributes}"

    @staticmethod
    def _edit_edge(graph: Graph, args: List[str]) -> str:
        if not args:
            raise InvalidCommandError(
                "edit-edge requires an edge ID.\n"
                "Usage: edit-edge <edge_id> --<type> name=value ..."
            )
        edge_id = args[0]
        attributes = CLI._parse_attributes(args[1:])
        if not attributes:
            raise InvalidCommandError(
                "edit-edge requires at least one attribute to update."
            )
        edge = GraphService.edit_edge(graph, edge_id, attributes)
        return f"Updated edge '{edge.edge_id}': {edge.attributes}"

    @staticmethod
    def _delete_node(graph: Graph, args: List[str]) -> str:
        if len(args) != 1:
            raise InvalidCommandError(
                "delete-node requires exactly one node ID.\n"
                "Usage: delete-node <node_id>"
            )
        GraphService.delete_node(graph, args[0])
        return f"Deleted node '{args[0]}'."

    @staticmethod
    def _delete_edge(graph: Graph, args: List[str]) -> str:
        if len(args) != 1:
            raise InvalidCommandError(
                "delete-edge requires exactly one edge ID.\n"
                "Usage: delete-edge <edge_id>"
            )
        GraphService.delete_edge(graph, args[0])
        return f"Deleted edge '{args[0]}'."

    @staticmethod
    def _search(args: List[str]) -> str:
        """Search is handled by Workspace.execute_cli() after this returns."""
        if not args:
            raise InvalidCommandError(
                "search requires a query.\n"
                "Usage: search <query>"
            )
        return f"__search__:{' '.join(args)}"

    @staticmethod
    def _filter(args: List[str]) -> str:
        """Filter is handled by Workspace.execute_cli() after this returns."""
        if len(args) < 3:
            raise InvalidCommandError(
                "filter requires an expression.\n"
                "Usage: filter <attribute> <comparator> <value>\n"
                "Example: filter age > 30"
            )
        return f"__filter__:{' '.join(args)}"

    @staticmethod
    def _parse_attributes(args: List[str]) -> Dict[str, Any]:
        """
        Parses attribute flags from argument list.

        Format: --<type> name=value
        Types:  int, float, string, date

        Dates must be in DD.MM.YYYY format.
        Strings with spaces must be wrapped in single quotes:
            --string name='Alice Smith'
        """
        attributes: Dict[str, Any] = {}
        current_type = None
        i = 0

        while i < len(args):
            token = args[i]

            if token.startswith("--"):
                current_type = token[2:]
                i += 1
                continue

            if "=" not in token:
                i += 1
                continue

            if current_type is None:
                raise InvalidCommandError(
                    f"Attribute '{token}' has no type flag before it. "
                    f"Use --int, --float, --string, or --date."
                )

            name, raw_value = token.split("=", 1)

            if current_type == "string" and raw_value.startswith("'"):
                while not raw_value.endswith("'") or len(raw_value) == 1:
                    i += 1
                    if i >= len(args):
                        raise InvalidCommandError(
                            "Unclosed single quote in string value."
                        )
                    raw_value += " " + args[i]
                raw_value = raw_value[1:-1]

            attributes[name] = CLI._cast_value(name, current_type, raw_value)
            i += 1

        return attributes

    @staticmethod
    def _cast_value(name: str, type_flag: str, raw: str) -> Any:
        try:
            match type_flag:
                case "int":
                    return int(raw)
                case "float":
                    return float(raw)
                case "string":
                    return raw
                case "date":
                    return datetime.strptime(raw, "%d.%m.%Y").date()
                case _:
                    raise InvalidCommandError(
                        f"Unknown type flag '--{type_flag}'. "
                        f"Use --int, --float, --string, or --date."
                    )
        except ValueError:
            raise InvalidCommandError(
                f"Cannot parse '{raw}' as --{type_flag} for attribute '{name}'."
            )

    @staticmethod
    def _tokenize(command: str) -> List[str]:
        """Splits command into tokens respecting single-quoted strings."""
        tokens = []
        current = ""
        in_quotes = False

        for char in command:
            if char == "'" :
                in_quotes = not in_quotes
                current += char
            elif char == " " and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return tokens

    @staticmethod
    def _generate_node_id(graph: Graph) -> str:
        """Generates a unique node ID by finding the next available integer."""
        i = 1
        while graph.has_node(str(i)):
            i += 1
        return str(i)

    @staticmethod
    def _generate_edge_id(graph: Graph) -> str:
        """Generates a unique edge ID."""
        i = 1
        while graph.has_edge(f"e{i}"):
            i += 1
        return f"e{i}"


class InvalidCommandError(Exception):
    """Raised when a CLI command is unknown or has invalid arguments."""
    pass