"""Schema mapping: source columns and rules to event type (CDC/Kafka → EventCreate)."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ColumnMapping:
    """Maps a source column to a target field on the event.

    target_field values:
        "subject_id"       — maps to subject_id
        "event_time"      — maps to event_time
        "payload.STATUS"  — maps to payload["STATUS"]
        "correlation_id"   — maps to correlation_id
    """

    source_column: str
    target_field: str


@dataclass
class EventTypeRule:
    """Rule to resolve event_type from a source row and operation."""

    event_type: str
    condition: str | None = None
    priority: int = 0

    # condition is a Python expression evaluated with row data in scope.
    # None means "default" — matches if no prior rule matched.


@dataclass
class TableMapping:
    """Mapping from a source table to subject_type, columns, and event_type rules."""

    source_table: str
    subject_type: str
    column_mappings: list[ColumnMapping]
    event_type_rules: list[EventTypeRule]
    default_schema_version: int = 1

    def resolve_event_type(
        self, row: dict[str, Any], operation: str
    ) -> str | None:
        """Evaluate rules in priority order; return first match."""
        context = {**row, "row": row, "operation": operation}
        for rule in sorted(self.event_type_rules, key=lambda r: -r.priority):
            if rule.condition is None:
                return rule.event_type
            try:
                if _safe_eval_condition(rule.condition, context):
                    return rule.event_type
            except (SyntaxError, NameError, TypeError, ValueError) as exc:
                logger.warning(
                    "Rejected EventTypeRule condition for table %s "
                    "(event_type=%s, condition=%r): %s",
                    self.source_table,
                    rule.event_type,
                    rule.condition,
                    exc,
                )
                continue
        return None


def _safe_eval_condition(condition: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a boolean condition expression against row/operation context.

    Only a restricted subset of Python is allowed:
    - boolean operations (and/or/not)
    - comparisons (==, !=, <, <=, >, >=, in, not in, is, is not)
    - names (no dunder names)
    - constants
    - subscripts (e.g. row[\"STATUS\"] or payload[\"STATUS\"])
    """

    expr = ast.parse(condition, mode="eval")

    allowed_nodes = (
        ast.Expression,
        ast.BoolOp,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Subscript,
        ast.Slice,
        ast.List,
        ast.Tuple,
    )

    allowed_ops = (
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.In,
        ast.NotIn,
        ast.Is,
        ast.IsNot,
    )

    class _Validator(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if node.id.startswith("__"):
                raise ValueError("Access to dunder names is not allowed")
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:  # type: ignore[override]
            raise ValueError("Attribute access is not allowed")

        def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
            raise ValueError("Function calls are not allowed")

        def generic_visit(self, node: ast.AST) -> None:
            if not isinstance(node, allowed_nodes) and not isinstance(
                node, allowed_ops
            ):
                raise ValueError(f"Disallowed expression node: {type(node).__name__}")
            super().generic_visit(node)

    _Validator().visit(expr)

    compiled = compile(expr, "<event_type_rule>", "eval")
    result = eval(compiled, {}, context)
    return bool(result)
