from __future__ import annotations

import ast
import json
import logging
import operator
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.services import llm_service

logger = logging.getLogger(__name__)

# ───────────────────────── tools ─────────────────────────

_OPS: dict[type, Callable] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    """Walk the AST by hand. NEVER eval() a string an LLM produced."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 10**6):
            raise ValueError("exponent too large")   # 2**10**9 freezes the process
        return _OPS[type(node.op)](left, right)
    raise ValueError("unsupported expression")


def calculate(expression: str) -> str:
    return str(_eval_node(ast.parse(expression, mode="eval").body))


def get_current_time(timezone: str = "UTC") -> str:
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"unknown timezone: {timezone}")
    return datetime.now(tz).isoformat(timespec="seconds")


# ───────────────────────── registry ─────────────────────────

REGISTRY: dict[str, Callable[..., str]] = {
    "calculate": calculate,
    "get_current_time": get_current_time,
}

# The `description` fields ARE the prompt. The model picks tools from these words.
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate an arithmetic expression. Use for any math the user asks for.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "e.g. '(2 + 3) * 4 / 7'"}
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Current date and time in an IANA timezone. The model has no clock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA name, e.g. 'Asia/Kolkata'."}
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def execute(name: str, raw_arguments: str) -> str:
    """NEVER raises. A tool error is DATA the model reads and recovers from."""
    fn = REGISTRY.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'."          # models hallucinate tool names
    try:
        kwargs = json.loads(raw_arguments or "{}")       # arguments arrive as a JSON *string*
    except json.JSONDecodeError:
        return "Error: arguments were not valid JSON."   # generated token-by-token, so it can be malformed
    if not isinstance(kwargs, dict):
        return "Error: arguments must be a JSON object."
    try:
        return str(fn(**kwargs))
    except TypeError as exc:
        return f"Error: bad arguments — {exc}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("tool_failed", extra={"tool": name, "err": str(exc)})
        return f"Error: {exc}"


# ───────────────────────── the loop ─────────────────────────


async def run_tool_loop(messages: list[dict[str, Any]], *, model: str | None = None) -> str:
    """model → tool_calls → execute → model → ... → final text."""
    messages = list(messages)   # don't mutate the caller's list

    for step in range(settings.MAX_TOOL_ITERATIONS):
        msg = await llm_service.complete_raw(messages, model=model, tools=TOOLS)

        if not msg.tool_calls:                       # answered in words. done.
            return msg.content or ""

        messages.append({                            # replay the assistant's request verbatim
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:                    # EVERY call needs a reply, or the next request 400s
            result = execute(tc.function.name, tc.function.arguments)
            logger.info("tool_call", extra={"tool": tc.function.name, "step": step})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    raise llm_service.LLMError("Tool loop did not converge.", 500)   # unbounded bill guard