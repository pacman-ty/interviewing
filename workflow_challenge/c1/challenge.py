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


def run_workflow(workflow):
    """Execute `workflow` and return {node_id: output} for every top-level
    node that ran.

    Stage 1: workflow == {"steps": [{"id", "op", "inputs"}, ...]} -- run the
    steps in listed order and collect their outputs.

    Later stages layer on: references, dependency ordering, groups & scope,
    conditional execution, and map. See README.md -- one stage at a time.
    """
    raise NotImplementedError("Stage 1: implement me (see README.md)")
