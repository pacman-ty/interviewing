"""Reference solution for the mock workflow-engine interview.

Built up stage by stage, but this file contains the FINAL combined engine
plus a validation pass. Run `python3 reference_solution.py` to see all
stages execute against the sample workflows.
"""

from __future__ import annotations
from typing import Any


# ---------------------------------------------------------------------------
# Scope: lexical variable resolution with parent chaining.
# ---------------------------------------------------------------------------
class Scope:
    def __init__(self, parent: "Scope | None" = None) -> None:
        self.parent = parent
        self.vars: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.vars[name] = value

    def resolve(self, name: str) -> Any:
        scope: "Scope | None" = self
        while scope is not None:
            if name in scope.vars:
                return scope.vars[name]
            scope = scope.parent
        raise KeyError(f"Unresolved reference: {name!r}")

    def has(self, name: str) -> bool:
        scope: "Scope | None" = self
        while scope is not None:
            if name in scope.vars:
                return True
            scope = scope.parent
        return False


# ---------------------------------------------------------------------------
# Operators. Kept in a table so adding a new op never touches the executor.
# ---------------------------------------------------------------------------
def _op_add(args): return sum(args)
def _op_sub(args): return args[0] - args[1]
def _op_mul(args):
    out = 1
    for a in args:
        out *= a
    return out
def _op_gt(args): return args[0] > args[1]
def _op_eq(args): return args[0] == args[1]

BINARY_OPS = {
    "add": _op_add,
    "sub": _op_sub,
    "mul": _op_mul,
    "gt": _op_gt,
    "eq": _op_eq,
}


# ---------------------------------------------------------------------------
# Executor.
# ---------------------------------------------------------------------------
class WorkflowEngine:
    def __init__(self) -> None:
        # Flat trace of every value produced, in execution order.
        self.trace: list[tuple[str, Any]] = []

    def run(self, steps: list[dict]) -> dict[str, Any]:
        root = Scope()
        self._exec_block(steps, root)
        return dict(root.vars)

    def _exec_block(self, steps: list[dict], scope: Scope) -> None:
        for step in steps:
            self._exec_step(step, scope)

    def _exec_step(self, step: dict, scope: Scope) -> None:
        op = step["op"]
        step_id = step["id"]

        if op == "const":
            value = step["value"]

        elif op == "ref":
            value = scope.resolve(step["arg"])

        elif op in BINARY_OPS:
            resolved = [scope.resolve(a) for a in step["args"]]
            value = BINARY_OPS[op](resolved)

        elif op == "if":
            cond = scope.resolve(step["cond"])
            branch = step["then"] if cond else step.get("else", [])
            # Child scope: branch steps can read parent vars but not leak out.
            child = Scope(parent=scope)
            self._exec_block(branch, child)
            # The `if` step's value is the last value produced in the taken
            # branch (or the condition itself if the branch is empty).
            value = self.trace[-1][1] if branch else cond

        else:
            raise ValueError(f"Unknown op: {op!r}")

        scope.define(step_id, value)
        self.trace.append((step_id, value))


# ---------------------------------------------------------------------------
# Stage 5: static validation BEFORE running anything.
# Walks the tree, tracking which names are defined in each scope, and reports
# every problem instead of crashing on the first one.
# ---------------------------------------------------------------------------
def validate(steps: list[dict]) -> list[str]:
    errors: list[str] = []

    def walk(block: list[dict], defined_outer: set[str]) -> set[str]:
        defined = set(defined_outer)
        for step in block:
            sid = step["id"]
            op = step["op"]

            refs: list[str] = []
            if op == "ref":
                refs = [step["arg"]]
            elif op in BINARY_OPS:
                refs = list(step["args"])
            elif op == "if":
                refs = [step["cond"]]

            for r in refs:
                if r not in defined:
                    errors.append(f"step {sid!r}: reference {r!r} is not in scope")

            if op == "if":
                # Each branch gets its own child scope; names it defines do NOT
                # escape back to the parent.
                walk(step.get("then", []), defined)
                walk(step.get("else", []), defined)

            if sid in defined:
                errors.append(f"duplicate step id {sid!r}")
            defined.add(sid)
        return defined

    walk(steps, set())
    return errors


# ---------------------------------------------------------------------------
# Sample workflows / demo.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    stage1 = [
        {"id": "a", "op": "const", "value": 5},
        {"id": "b", "op": "const", "value": 3},
    ]
    print("Stage 1:", WorkflowEngine().run(stage1))

    stage2 = stage1 + [
        {"id": "sum", "op": "add", "args": ["a", "b"]},
        {"id": "prod", "op": "mul", "args": ["a", "b", "sum"]},
    ]
    print("Stage 2:", WorkflowEngine().run(stage2))

    stage3 = stage2 + [
        {"id": "big", "op": "gt", "args": ["prod", "sum"]},
        {
            "id": "branch",
            "op": "if",
            "cond": "big",
            "then": [{"id": "t", "op": "add", "args": ["prod", "sum"]}],
            "else": [{"id": "f", "op": "sub", "args": ["sum", "prod"]}],
        },
    ]
    print("Stage 3/4:", WorkflowEngine().run(stage3))

    bad = [
        {"id": "x", "op": "add", "args": ["missing", "x"]},
        {"id": "x", "op": "const", "value": 1},
        {
            "id": "c",
            "op": "if",
            "cond": "x",
            "then": [{"id": "inner", "op": "const", "value": 9}],
            "else": [],
        },
        {"id": "leak", "op": "ref", "arg": "inner"},  # inner is out of scope here
    ]
    print("Stage 5 errors:")
    for e in validate(bad):
        print("  -", e)
