from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from tools.doc_reader import read_doc_tool


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[[Dict[str, Any]], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list(self) -> List[Tool]:
        return list(self._tools.values())

    def names(self) -> List[str]:
        return sorted(self._tools.keys())


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    ):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
    raise ValueError("Unsupported expression")


def _calculator_tool(args: Dict[str, Any]) -> str:
    expr = args.get("expression") or args.get("input")
    if not expr:
        return "Error: missing expression"
    try:
        tree = ast.parse(str(expr), mode="eval")
        result = _safe_eval(tree)
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


def _pip_install_tool(args: Dict[str, Any]) -> str:
    package = args.get("package") or args.get("name") or args.get("input")
    if not package:
        return "Error: missing 'package'"
    try:
        proc = subprocess.run(
            ["pip", "install", str(package)],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return f"Error: failed to run pip: {exc}"

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"pip install failed (code={proc.returncode})\nstdout:\n{stdout}\nstderr:\n{stderr}"
    if stderr:
        return f"pip install succeeded with warnings:\n{stdout}\n{stderr}"
    return stdout or "pip install succeeded"


def build_default_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="calculator",
            description="Evaluate a basic math expression.",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            func=_calculator_tool,
        )
    )
    registry.register(
        Tool(
            name="read_doc",
            description="Read a .doc or .docx file and return extracted plain text.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the .doc/.docx file"},
                    "max_chars": {
                        "type": "integer",
                        "description": "Optional max chars to return (truncates output).",
                    },
                },
                "required": ["path"],
            },
            func=read_doc_tool,
        )
    )
    registry.register(
        Tool(
            name="pip_install",
            description="Install a Python package using pip.",
            parameters={
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "Package spec, e.g., 'requests' or 'requests==2.32.3'",
                    }
                },
                "required": ["package"],
            },
            func=_pip_install_tool,
        )
    )
    return registry
