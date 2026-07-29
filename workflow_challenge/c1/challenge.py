"""
Workflow Engine challenge -- YOUR implementation goes here.

Read README.md one stage at a time, implement, then run:

    python tests.py 1        # runs stages 1..N against this file
    python tests.py 2
    ...
    python tests.py 6

Keep earlier stages green as you extend -- refactoring without breaking
existing behavior is exactly what the interview probes.
"""


class WorkflowError(Exception):
    """Raise this for any invalid workflow definition or execution failure."""


# The operation registry is provided -- your engine looks ops up here.
# Each op receives the (already-resolved) inputs dict and returns the output.
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


def _is_ref(value):
    """A reference is a dict with exactly one key, "$ref"."""
    return isinstance(value, dict) and len(value) == 1 and "$ref" in value


def resolve(value, results):
    """Recursively replace any {"$ref": id} with results[id].

    Walks lists and literal dicts so refs nested at any depth are resolved.
    """
    if _is_ref(value):
        ref_id = value["$ref"]
        if ref_id not in results:
            raise WorkflowError(f"unknown or not-yet-run ref: {ref_id!r}")
        return results[ref_id]
    if isinstance(value, dict):
        resolved_dict = {}
        for key, inner_value in value.items():
            resolved_dict[key] = resolve(inner_value, results)
        return resolved_dict
    if isinstance(value, list):
        resolved_list = []
        for item in value:
            resolved_list.append(resolve(item, results))
        return resolved_list
    return value


def collect_refs(value):
    """Recursively gather every "$ref" target id inside a value.

    The "gather" cousin of resolve: same recursive walk, but instead of
    replacing refs it returns the set of ids the value depends on.
    """
    refs = set()
    if _is_ref(value):
        refs.add(value["$ref"])
    elif isinstance(value, dict):
        for inner_value in value.values():
            refs |= collect_refs(inner_value)
    elif isinstance(value, list):
        for item in value:
            refs |= collect_refs(item)
    return refs


def run_workflow(workflow):
    """Execute `workflow` and return {node_id: output} for every top-level
    node that ran.

    Stage 1: workflow == {"steps": [{"id", "op", "inputs"}, ...]} -- run the
    steps in listed order and collect their outputs.

    Stage 3: steps may be listed in any order. Derive execution order from
    the $refs via lazy, memoized evaluation; detect cycles and missing refs.

    Later stages layer on: groups & scope, conditional execution, and map.
    See README.md -- one stage at a time.
    """
    # Index steps by id, validating duplicate ids and unknown ops up front.
    steps_by_id = {}
    for step in workflow["steps"]:
        node_id = step["id"]
        if node_id in steps_by_id:
            raise WorkflowError(f"duplicate id: {node_id!r}")
        if step["op"] not in OPS:
            raise WorkflowError(f"unknown op: {step['op']!r}")
        steps_by_id[node_id] = step

    results = {}
    visiting = set()  # ids on the current recursion stack -> cycle detection

    def evaluate(node_id):
        if node_id in results:          # already computed -> memoized
            return qq qq
        if node_id in visiting:         # back-edge -> cycle (incl. self-ref)
            raise WorkflowError(f"cycle detected at: {node_id!r}")
        if node_id not in steps_by_id:  # ref to an id that exists nowhere
            raise WorkflowError(f"unknown ref: {node_id!r}")

        step = steps_by_id[node_id]
        visiting.add(node_id)
        for dep_id in collect_refs(step["inputs"]):
            evaluate(dep_id)            # ensure dependencies run first
        visiting.remove(node_id)

        inputs = resolve(step["inputs"], results)
        results[node_id] = OPS[step["op"]](inputs)

    for node_id in steps_by_id:
        evaluate(node_id)

    return results
