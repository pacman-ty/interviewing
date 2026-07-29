"""
Stage-by-stage tests for the Workflow Engine challenge.

Usage:
    python tests.py <stage> [module] [-v]

    stage    1-6: runs every test for stages 1..N (default 1)
    module   python module to test (default "challenge";
             use "solution" for the reference implementation -- stage 3+,
             see README)
    -v       print full tracebacks on failures

Example:
    python tests.py 3            # test your challenge.py through Stage 3
    python tests.py 6 solution   # verify the reference solution
"""

import importlib
import sys
import traceback


# ------------------------------- helpers -------------------------------------

def step(id, op, **inputs):
    return {"id": id, "op": op, "inputs": inputs}


def group(id, steps, exports, **extra):
    return {"id": id, "type": "group", "steps": steps, "exports": exports, **extra}


def map_node(id, items, steps, exports, **extra):
    return {"id": id, "type": "map", "items": items, "steps": steps,
            "exports": exports, **extra}


def ref(name):
    return {"$ref": name}


def expect_error(run, WorkflowError, workflow, why):
    try:
        run(workflow)
    except WorkflowError:
        return
    except Exception as exc:
        raise AssertionError(
            f"expected WorkflowError ({why}), got {type(exc).__name__}: {exc}"
        )
    raise AssertionError(f"expected WorkflowError: {why}")


# ------------------------------- Stage 1 --------------------------------------

def s1_linear_execution(run, WE):
    wf = {"steps": [
        step("greeting", "const", value="hello"),
        step("total", "add", values=[1, 2, 3]),
    ]}
    out = run(wf)
    assert out == {"greeting": "hello", "total": 6}, out


def s1_unknown_op(run, WE):
    wf = {"steps": [step("boom", "teleport", value=1)]}
    expect_error(run, WE, wf, "unknown op should raise")


def s1_duplicate_ids(run, WE):
    wf = {"steps": [
        step("a", "const", value=1),
        step("a", "const", value=2),
    ]}
    expect_error(run, WE, wf, "duplicate ids should raise")


# ------------------------------- Stage 2 --------------------------------------

def s2_ref_chain(run, WE):
    wf = {"steps": [
        step("name", "const", value="tennr"),
        step("loud", "upper", value=ref("name")),
        step("cheer", "concat", values=[ref("loud"), "!"]),
    ]}
    out = run(wf)
    assert out == {"name": "tennr", "loud": "TENNR", "cheer": "TENNR!"}, out


def s2_refs_inside_list(run, WE):
    wf = {"steps": [
        step("x", "const", value=2),
        step("y", "const", value=3),
        step("total", "add", values=[ref("x"), ref("y"), 10]),
    ]}
    assert run(wf)["total"] == 15


def s2_refs_inside_dict_literal(run, WE):
    wf = {"steps": [
        step("x", "const", value=42),
        step("report", "const", value={"inner": ref("x"), "label": "score"}),
    ]}
    out = run(wf)
    assert out["report"] == {"inner": 42, "label": "score"}, out


def s2_unknown_ref(run, WE):
    wf = {"steps": [step("a", "upper", value=ref("ghost"))]}
    expect_error(run, WE, wf, "ref to an id that does not exist")


def s2_forward_ref_is_an_error(run, WE):
    # NOTE: this rule is deliberately superseded in Stage 3 (the engine will
    # start reordering steps itself). tests.py skips this test at stage >= 3.
    wf = {"steps": [
        step("shout", "upper", value=ref("word")),
        step("word", "const", value="hi"),
    ]}
    expect_error(run, WE, wf, "ref to a step that has not run yet")


# ------------------------------- Stage 3 --------------------------------------

def s3_any_listed_order(run, WE):
    wf = {"steps": [
        step("cheer", "concat", values=[ref("loud"), "!"]),
        step("loud", "upper", value=ref("name")),
        step("name", "const", value="tennr"),
    ]}
    out = run(wf)
    assert out["cheer"] == "TENNR!", out


def s3_diamond_dependencies(run, WE):
    wf = {"steps": [
        step("d", "add", values=[ref("b"), ref("c")]),
        step("b", "add", values=[ref("a"), 1]),
        step("c", "add", values=[ref("a"), 2]),
        step("a", "const", value=10),
    ]}
    assert run(wf)["d"] == 23


def s3_cycle_detection(run, WE):
    wf = {"steps": [
        step("a", "add", values=[ref("b")]),
        step("b", "add", values=[ref("a")]),
    ]}
    expect_error(run, WE, wf, "a <-> b cycle")


def s3_self_reference_is_a_cycle(run, WE):
    wf = {"steps": [step("a", "add", values=[ref("a")])]}
    expect_error(run, WE, wf, "self-reference")


# ------------------------------- Stage 4 --------------------------------------

def s4_group_basics(run, WE):
    wf = {"steps": [
        step("base", "const", value=10),
        group("calc",
              steps=[step("doubled", "add", values=[ref("base"), ref("base")])],
              exports=ref("doubled")),
        step("total", "add", values=[ref("calc"), 5]),
    ]}
    out = run(wf)
    assert out == {"base": 10, "calc": 20, "total": 25}, out


def s4_inner_ids_are_hidden(run, WE):
    wf = {"steps": [
        group("g",
              steps=[step("secret", "const", value=1)],
              exports=ref("secret")),
        step("peek", "add", values=[ref("secret")]),
    ]}
    expect_error(run, WE, wf, "inner ids are not visible outside their group")


def s4_shadowing(run, WE):
    wf = {"steps": [
        step("x", "const", value=1),
        group("g",
              steps=[
                  step("x", "const", value=100),
                  step("y", "add", values=[ref("x"), ref("x")]),
              ],
              exports=ref("y")),
    ]}
    out = run(wf)
    assert out == {"x": 1, "g": 200}, out


def s4_exports_can_be_a_dict(run, WE):
    wf = {"steps": [
        group("stats",
              steps=[
                  step("word", "const", value="hello"),
                  step("n", "length", value=ref("word")),
              ],
              exports={"word": ref("word"), "letters": ref("n")}),
        step("picked", "get", obj=ref("stats"), key="letters"),
    ]}
    out = run(wf)
    assert out["stats"] == {"word": "hello", "letters": 5}, out
    assert out["picked"] == 5, out


def s4_nested_groups(run, WE):
    wf = {"steps": [
        step("base", "const", value=2),
        group("outer",
              steps=[
                  group("inner",
                        steps=[step("m", "add", values=[ref("base"), ref("base")])],
                        exports=ref("m")),
                  step("n", "add", values=[ref("inner"), 1]),
              ],
              exports=ref("n")),
    ]}
    assert run(wf)["outer"] == 5


def s4_group_ordered_after_outer_dependency(run, WE):
    # The group is LISTED first, but its inner step references a later
    # top-level sibling -- the engine must schedule "seed" before "g".
    wf = {"steps": [
        group("g",
              steps=[step("twice", "add", values=[ref("seed"), ref("seed")])],
              exports=ref("twice")),
        step("seed", "const", value=7),
    ]}
    out = run(wf)
    assert out == {"g": 14, "seed": 7}, out


# ------------------------------- Stage 5 --------------------------------------

def s5_literal_when(run, WE):
    wf = {"steps": [
        {**step("a", "const", value=1), "when": False},
        {**step("b", "const", value=2), "when": True},
    ]}
    out = run(wf)
    assert out == {"b": 2}, out


def s5_when_from_a_ref(run, WE):
    wf = {"steps": [
        step("flag", "const", value=True),
        {**step("a", "const", value="ran"), "when": ref("flag")},
    ]}
    out = run(wf)
    assert out["a"] == "ran", out


def s5_skip_cascades_downstream(run, WE):
    wf = {"steps": [
        step("flag", "const", value=False),
        {**step("a", "const", value="hi"), "when": ref("flag")},
        step("b", "upper", value=ref("a")),   # depends on skipped "a"
        step("c", "const", value="ok"),        # independent, still runs
    ]}
    out = run(wf)
    assert out == {"flag": False, "c": "ok"}, out


def s5_skipping_a_group_skips_its_contents(run, WE):
    wf = {"steps": [
        group("g",
              steps=[step("inner", "const", value=5)],
              exports=ref("inner"),
              when=False),
        step("after", "const", value="done"),
    ]}
    out = run(wf)
    assert out == {"after": "done"}, out


def s5_condition_computed_by_an_op(run, WE):
    wf = {"steps": [
        step("score", "const", value=85),
        step("passed", "gt", left=ref("score"), right=70),
        step("failed", "eq", left=ref("score"), right=0),
        {**step("award", "const", value="approved"), "when": ref("passed")},
        {**step("reject", "const", value="denied"), "when": ref("failed")},
    ]}
    out = run(wf)
    assert out == {"score": 85, "passed": True, "failed": False,
                   "award": "approved"}, out


# ------------------------------- Stage 6 --------------------------------------

def s6_map_basics(run, WE):
    wf = {"steps": [
        step("nums", "const", value=[1, 2, 3]),
        map_node("doubled", items=ref("nums"),
                 steps=[step("twice", "add", values=[ref("item"), ref("item")])],
                 exports=ref("twice")),
        step("total", "add", values=ref("doubled")),
    ]}
    out = run(wf)
    assert out["doubled"] == [2, 4, 6], out
    assert out["total"] == 12, out


def s6_map_sees_the_outer_scope(run, WE):
    wf = {"steps": [
        step("factor", "const", value=100),
        map_node("shifted", items=[1, 2],
                 steps=[step("s", "add", values=[ref("item"), ref("factor")])],
                 exports=ref("s")),
    ]}
    assert run(wf)["shifted"] == [101, 102]


def s6_map_over_empty_list(run, WE):
    wf = {"steps": [
        map_node("m", items=[],
                 steps=[step("s", "add", values=[ref("item")])],
                 exports=ref("s")),
    ]}
    assert run(wf)["m"] == []


def s6_map_items_must_be_a_list(run, WE):
    wf = {"steps": [
        map_node("m", items=42,
                 steps=[step("s", "add", values=[ref("item")])],
                 exports=ref("s")),
    ]}
    expect_error(run, WE, wf, "map items must resolve to a list")


# ------------------------------- registry -------------------------------------

# (stage, test_fn, max_stage) -- max_stage marks tests whose rule is
# superseded by a later stage (an evolving requirement, like the real thing).
CASES = [
    (1, s1_linear_execution, None),
    (1, s1_unknown_op, None),
    (1, s1_duplicate_ids, None),

    (2, s2_ref_chain, None),
    (2, s2_refs_inside_list, None),
    (2, s2_refs_inside_dict_literal, None),
    (2, s2_unknown_ref, None),
    (2, s2_forward_ref_is_an_error, 2),   # superseded by Stage 3

    (3, s3_any_listed_order, None),
    (3, s3_diamond_dependencies, None),
    (3, s3_cycle_detection, None),
    (3, s3_self_reference_is_a_cycle, None),

    (4, s4_group_basics, None),
    (4, s4_inner_ids_are_hidden, None),
    (4, s4_shadowing, None),
    (4, s4_exports_can_be_a_dict, None),
    (4, s4_nested_groups, None),
    (4, s4_group_ordered_after_outer_dependency, None),

    (5, s5_literal_when, None),
    (5, s5_when_from_a_ref, None),
    (5, s5_skip_cascades_downstream, None),
    (5, s5_skipping_a_group_skips_its_contents, None),
    (5, s5_condition_computed_by_an_op, None),

    (6, s6_map_basics, None),
    (6, s6_map_sees_the_outer_scope, None),
    (6, s6_map_over_empty_list, None),
    (6, s6_map_items_must_be_a_list, None),
]


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if a != "-v"]

    stage = 1
    if len(args) > 1:
        try:
            stage = int(args[1])
        except ValueError:
            print(__doc__)
            return 2
    if not 1 <= stage <= 6:
        print("stage must be between 1 and 6")
        return 2

    module_name = args[2] if len(args) > 2 else "challenge"
    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"could not import module '{module_name}': {exc}")
        return 2

    run = getattr(mod, "run_workflow", None)
    WE = getattr(mod, "WorkflowError", None)
    if run is None or WE is None:
        print(f"'{module_name}' must define run_workflow() and WorkflowError")
        return 2

    selected, superseded = [], 0
    for st, fn, max_stage in CASES:
        if st > stage:
            continue
        if max_stage is not None and stage > max_stage:
            superseded += 1
            continue
        selected.append((st, fn))

    passed = failed = 0
    current = None
    for st, fn in selected:
        if st != current:
            print(f"\nStage {st}")
            current = st
        try:
            fn(run, WE)
        except NotImplementedError:
            failed += 1
            print(f"  FAIL {fn.__name__} -- run_workflow not implemented yet")
        except Exception as exc:
            failed += 1
            print(f"  FAIL {fn.__name__} -- {type(exc).__name__}: {exc}")
            if verbose:
                traceback.print_exc()
        else:
            passed += 1
            print(f"  ok   {fn.__name__}")

    print(f"\n{passed} passed, {failed} failed"
          f"  (stages 1-{stage}, module '{module_name}')")
    if superseded:
        print(f"note: {superseded} Stage 2 test(s) whose rule is superseded "
              f"at Stage >= 3 were skipped.")
    if failed and not verbose:
        print("tip: re-run with -v for full tracebacks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
