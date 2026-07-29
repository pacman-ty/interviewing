"""
Reference solution for the Workflow Engine challenge -- Stages 1 through 6.

SPOILERS: attempt each stage in challenge.py before reading this.

Verify with:  python tests.py 6 solution

(Test this file with stage >= 3. Stage 3 deliberately supersedes Stage 2's
"a ref must point to an earlier step" rule, and this file implements the
final spec, so the superseded Stage 2 test would fail against it.)
"""


class WorkflowError(Exception):
    """Any invalid workflow definition or execution failure."""


OPS = {
    "const": lambda inputs: inputs["value"],
    "add": lambda inputs: sum(inputs["values"]),
    "concat": lambda inputs: str(inputs.get("sep", "")).join(
        str(v) for v in inputs["values"]
    ),
    "upper": lambda inputs: inputs["value"].upper(),
    "length": lambda inputs: len(inputs["value"]),
    "get": lambda inputs: inputs["obj"][inputs["key"]],
    "gt": lambda inputs: inputs["left"] > inputs["right"],
    "eq": lambda inputs: inputs["left"] == inputs["right"],
}

# Sentinel returned by lookups when a reference points at a node that was
# skipped (Stage 5). Distinct from None, which is a legitimate output value.
_SKIPPED = object()


def is_ref(value):
    """A reference is a dict with exactly one key: "$ref"."""
    return isinstance(value, dict) and set(value.keys()) == {"$ref"}


class Scope:
    """One lexical scope (Stage 4): the outputs and skipped ids for a set of
    sibling nodes, chained to the enclosing scope."""

    def __init__(self, parent=None):
        self.parent = parent
        self.values = {}      # node id -> output
        self.skipped = set()  # node ids that were skipped (Stage 5)

    def lookup(self, name):
        scope = self
        while scope is not None:
            if name in scope.values:
                return scope.values[name]
            if name in scope.skipped:
                return _SKIPPED
            scope = scope.parent
        raise WorkflowError(f"Reference to unknown id '{name}'")


def resolve(value, scope, skipped_as_none=False):
    """Recursively replace references with their values (Stage 2).

    Returns _SKIPPED if any reference targets a skipped node, so callers can
    cascade the skip (Stage 5). With skipped_as_none=True (used for group/map
    exports), such references resolve to None instead -- a documented design
    choice; erroring or dropping keys would also be defensible.
    """
    if is_ref(value):
        found = scope.lookup(value["$ref"])
        if found is _SKIPPED and skipped_as_none:
            return None
        return found
    if isinstance(value, list):
        out = []
        for item in value:
            item = resolve(item, scope, skipped_as_none)
            if item is _SKIPPED:
                return _SKIPPED
            out.append(item)
        return out
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            item = resolve(item, scope, skipped_as_none)
            if item is _SKIPPED:
                return _SKIPPED
            out[key] = item
        return out
    return value


# ---------------------------- ordering (Stage 3/4) ----------------------------

def _collect_refs(value, acc):
    if is_ref(value):
        acc.add(value["$ref"])
    elif isinstance(value, list):
        for item in value:
            _collect_refs(item, acc)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_refs(item, acc)


def free_refs(node):
    """Reference names inside `node` that must resolve in the scope where the
    node lives -- i.e. refs NOT satisfied by the node's own children. Used to
    build dependency edges between siblings (Stage 3), and it is what makes
    ordering work across group boundaries (Stage 4)."""
    acc = set()
    _collect_refs(node.get("when"), acc)  # `when` resolves in the enclosing scope
    kind = node.get("type", "step")

    if kind == "step":
        _collect_refs(node.get("inputs", {}), acc)

    elif kind in ("group", "map"):
        if kind == "map":
            _collect_refs(node.get("items"), acc)  # items resolve outside too
        inner = set()
        child_ids = set()
        for child in node.get("steps", []):
            child_ids.add(child.get("id"))
            inner |= free_refs(child)
        _collect_refs(node.get("exports"), inner)  # exports resolve in child scope
        bound = child_ids | ({"item"} if kind == "map" else set())
        acc |= inner - bound

    else:
        raise WorkflowError(f"Unknown node type '{kind}'")

    return acc


def order_nodes(nodes):
    """Return nodes in a valid execution order (Stage 3).

    A node depends on any sibling whose id appears among its free refs.
    Raises on duplicate ids and on cycles (a self-reference is a cycle).
    Stable: preserves listed order among nodes that are ready together.
    """
    by_id = {}
    for node in nodes:
        nid = node.get("id")
        if not nid:
            raise WorkflowError("Every node needs an 'id'")
        if nid in by_id:
            raise WorkflowError(f"Duplicate id '{nid}'")
        by_id[nid] = node

    deps = {
        nid: {r for r in free_refs(node) if r in by_id}
        for nid, node in by_id.items()
    }

    ordered, done = [], set()
    pending = list(by_id)
    while pending:
        ready = [nid for nid in pending if deps[nid] <= done]
        if not ready:
            raise WorkflowError(f"Cycle detected among: {sorted(pending)}")
        for nid in ready:
            ordered.append(by_id[nid])
            done.add(nid)
        pending = [nid for nid in pending if nid not in done]
    return ordered


# -------------------------------- execution ----------------------------------

def run_nodes(nodes, scope):
    for node in order_nodes(nodes):
        run_node(node, scope)


def run_node(node, scope):
    nid = node["id"]

    if "when" in node:  # Stage 5
        cond = resolve(node["when"], scope)
        if cond is _SKIPPED or not cond:
            scope.skipped.add(nid)
            return

    kind = node.get("type", "step")

    if kind == "step":
        inputs = resolve(node.get("inputs", {}), scope)
        if inputs is _SKIPPED:  # an input referenced a skipped node -> cascade
            scope.skipped.add(nid)
            return
        op_name = node.get("op")
        if op_name not in OPS:
            raise WorkflowError(f"Unknown op '{op_name}' in step '{nid}'")
        try:
            scope.values[nid] = OPS[op_name](inputs)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(f"Step '{nid}' failed: {exc}") from exc

    elif kind == "group":  # Stage 4
        child_scope = Scope(parent=scope)
        run_nodes(node.get("steps", []), child_scope)
        scope.values[nid] = resolve(
            node.get("exports"), child_scope, skipped_as_none=True
        )

    elif kind == "map":  # Stage 6
        items = resolve(node.get("items"), scope)
        if items is _SKIPPED:
            scope.skipped.add(nid)
            return
        if not isinstance(items, list):
            raise WorkflowError(
                f"Map '{nid}' items must be a list, got {type(items).__name__}"
            )
        results = []
        for item in items:
            child_scope = Scope(parent=scope)
            child_scope.values["item"] = item
            run_nodes(node.get("steps", []), child_scope)
            results.append(
                resolve(node.get("exports"), child_scope, skipped_as_none=True)
            )
        scope.values[nid] = results

    else:
        raise WorkflowError(f"Unknown node type '{kind}'")


def run_workflow(workflow):
    """Execute a workflow, returning {id: output} for every top-level node
    that ran. Skipped nodes are absent; groups appear as their exports; inner
    ids never leak out."""
    scope = Scope()
    run_nodes(workflow.get("steps", []), scope)
    return dict(scope.values)
