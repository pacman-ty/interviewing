"""
Task-gated tests for the intake pipeline integration challenge.

Usage:
    python pipeline_tests.py <task> [module] [-v]

    task     0-4: runs the regression suite (task 0) plus tasks 1..N
             (default 0 -- the given code must pass this untouched)
    module   python module to test (default "pipeline";
             use "pipeline_solution" for the reference)
    -v       print full tracebacks on failures

Examples:
    python pipeline_tests.py 0                     # before you change anything
    python pipeline_tests.py 2                     # regression + tasks 1-2
    python pipeline_tests.py 4 pipeline_solution   # verify the reference
"""

import importlib
import sys
import traceback


def expect_error(PipelineError, fn, why):
    try:
        fn()
    except PipelineError:
        return
    except Exception as exc:
        raise AssertionError(
            f"expected PipelineError ({why}), got {type(exc).__name__}: {exc}"
        )
    raise AssertionError(f"expected PipelineError: {why}")


def statuses(result):
    return [entry["status"] for entry in result["trace"]]


# --------------------- Task 0: regressions for the GIVEN code -----------------

def r0_basic_run(m):
    p = m.Pipeline([
        {"kind": "set_field", "field": "department", "value": "radiology"},
        {"kind": "normalize", "field": "patient_name", "mode": "title"},
        {"kind": "tag", "tag": "intake"},
    ])
    out = p.run({"id": "doc-1", "fields": {"patient_name": "jane doe"}})
    assert out["doc"]["fields"]["department"] == "radiology", out
    assert out["doc"]["fields"]["patient_name"] == "Jane Doe", out
    assert out["tags"] == ["intake"], out
    assert out["errors"] == [], out
    assert statuses(out) == ["ok", "ok", "ok"], out
    assert "destination" not in out, "no routes configured -> no destination"


def r0_require_collects_errors_without_stopping(m):
    p = m.Pipeline([
        {"kind": "require", "fields": ["patient_name", "dob"]},
        {"kind": "tag", "tag": "checked"},
    ])
    out = p.run({"fields": {"patient_name": "Jane"}})
    assert out["errors"] == ["missing required field 'dob'"], out
    assert out["tags"] == ["checked"], "later steps still run"


def r0_normalize_missing_field_raises(m):
    p = m.Pipeline([{"kind": "normalize", "field": "dob"}])
    expect_error(m.PipelineError, lambda: p.run({"fields": {}}),
                 "normalizing a missing field")


def r0_unknown_kind_rejected_at_construction(m):
    expect_error(m.PipelineError,
                 lambda: m.Pipeline([{"kind": "zap"}]),
                 "unknown step kind")


def r0_trace_uses_step_name_when_given(m):
    p = m.Pipeline([{"kind": "tag", "tag": "x", "name": "mark-intake"}])
    out = p.run({"fields": {}})
    assert out["trace"] == [{"step": "mark-intake", "status": "ok"}], out


def r0_input_document_is_not_mutated(m):
    doc = {"fields": {"patient_name": "jane"}}
    p = m.Pipeline([{"kind": "set_field", "field": "seen", "value": True}])
    p.run(doc)
    assert doc == {"fields": {"patient_name": "jane"}}, doc


# ------------------- Task 1: new processors (follow the pattern) --------------

def t1_default_field(m):
    p = m.Pipeline([
        {"kind": "default_field", "field": "status", "value": "new"},
        {"kind": "default_field", "field": "source", "value": "unknown"},
        {"kind": "default_field", "field": "priority", "value": "routine"},
    ])
    out = p.run({"fields": {"status": "", "source": "fax"}})
    fields = out["doc"]["fields"]
    assert fields["status"] == "new", "empty string counts as missing"
    assert fields["source"] == "fax", "existing values are kept"
    assert fields["priority"] == "routine", "absent fields get the default"


def t1_rename_field_moves_the_value(m):
    p = m.Pipeline([{"kind": "rename_field", "from": "pt_name", "to": "patient_name"}])
    out = p.run({"fields": {"pt_name": "Jane"}})
    fields = out["doc"]["fields"]
    assert fields.get("patient_name") == "Jane", fields
    assert "pt_name" not in fields, "source field is removed"


def t1_rename_missing_source_is_a_noop(m):
    p = m.Pipeline([{"kind": "rename_field", "from": "ghost", "to": "spirit"}])
    out = p.run({"fields": {"patient_name": "Jane"}})
    assert out["doc"]["fields"] == {"patient_name": "Jane"}, out
    assert out["errors"] == [], out


# --------------------- Task 2: conditional steps ("when") ---------------------

def t2_equals_condition_runs_or_skips(m):
    steps = [{"kind": "tag", "tag": "urgent",
              "when": {"field": "priority", "equals": "stat"}}]
    p = m.Pipeline(steps)

    hit = p.run({"fields": {"priority": "stat"}})
    assert hit["tags"] == ["urgent"], hit
    assert statuses(hit) == ["ok"], hit

    miss = p.run({"fields": {"priority": "routine"}})
    assert miss["tags"] == [], miss
    assert miss["trace"] == [{"step": "tag", "status": "skipped"}], miss


def t2_exists_condition(m):
    steps = [{"kind": "tag", "tag": "has-fax",
              "when": {"field": "fax_number", "exists": True}}]
    p = m.Pipeline(steps)

    assert p.run({"fields": {"fax_number": "555-0101"}})["tags"] == ["has-fax"]
    # Present-but-empty still exists: presence, not truthiness.
    assert p.run({"fields": {"fax_number": ""}})["tags"] == ["has-fax"]
    assert p.run({"fields": {}})["tags"] == []


def t2_nested_all_any_not(m):
    steps = [{"kind": "tag", "tag": "review",
              "when": {"all": [
                  {"field": "source", "equals": "fax"},
                  {"not": {"field": "priority", "equals": "low"}},
              ]}}]
    p = m.Pipeline(steps)

    assert p.run({"fields": {"source": "fax", "priority": "high"}})["tags"] == ["review"]
    assert p.run({"fields": {"source": "fax", "priority": "low"}})["tags"] == []
    assert p.run({"fields": {"source": "email", "priority": "high"}})["tags"] == []


def t2_unrecognized_condition_raises(m):
    p = m.Pipeline([{"kind": "tag", "tag": "x", "when": {"frobnicate": 1}}])
    expect_error(m.PipelineError, lambda: p.run({"fields": {}}),
                 "unrecognized condition shape")


# -------------------------- Task 3: routing rules -----------------------------

def t3_first_matching_route_wins(m):
    p = m.Pipeline(
        [],
        routes=[
            {"when": {"field": "source", "equals": "fax"}, "to": "fax-queue"},
            {"when": {"field": "source", "equals": "email"}, "to": "email-queue"},
            {"to": "general"},
        ],
    )
    assert p.run({"fields": {"source": "fax"}})["destination"] == "fax-queue"
    assert p.run({"fields": {"source": "email"}})["destination"] == "email-queue"
    assert p.run({"fields": {"source": "portal"}})["destination"] == "general"


def t3_nested_route_groups_fall_through(m):
    routes = [
        {"when": {"field": "source", "equals": "fax"},
         "routes": [
             {"when": {"has_tag": "urgent"}, "to": "fax-priority"},
             {"when": {"field": "state", "equals": "NY"}, "to": "fax-ny"},
         ]},
        {"to": "general"},
    ]
    tag_urgent = m.Pipeline([{"kind": "tag", "tag": "urgent"}], routes=routes)
    plain = m.Pipeline([], routes=routes)

    out = tag_urgent.run({"fields": {"source": "fax"}})
    assert out["destination"] == "fax-priority", out

    out = plain.run({"fields": {"source": "fax", "state": "NY"}})
    assert out["destination"] == "fax-ny", out

    # Group matches but no child matches -> falls through to the next rule.
    out = plain.run({"fields": {"source": "fax", "state": "CA"}})
    assert out["destination"] == "general", out


def t3_routes_can_use_errors_and_tags(m):
    routes = [
        {"when": {"has_errors": True}, "to": "manual-review"},
        {"to": "auto-process"},
    ]
    p = m.Pipeline([{"kind": "require", "fields": ["dob"]}], routes=routes)

    assert p.run({"fields": {}})["destination"] == "manual-review"
    assert p.run({"fields": {"dob": "1990-04-02"}})["destination"] == "auto-process"


def t3_no_matching_route_raises(m):
    p = m.Pipeline([], routes=[{"when": {"field": "source", "equals": "fax"},
                                "to": "fax-queue"}])
    expect_error(m.PipelineError, lambda: p.run({"fields": {"source": "email"}}),
                 "no route matched and no catch-all")


def t3_route_rules_are_validated(m):
    expect_error(m.PipelineError,
                 lambda: m.Pipeline([], routes=[{"when": {"has_errors": True}}]),
                 "rule with neither 'to' nor 'routes'")
    expect_error(m.PipelineError,
                 lambda: m.Pipeline([], routes=[{"to": "a", "routes": []}]),
                 "rule with both 'to' and 'routes'")


# ------------------------ Task 4: per-step error policy -----------------------

def t4_on_error_skip_records_and_continues(m):
    p = m.Pipeline(
        [
            {"kind": "normalize", "field": "dob", "on_error": "skip"},
            {"kind": "tag", "tag": "done"},
        ],
        routes=[{"to": "general"}],
    )
    out = p.run({"fields": {}})  # normalize will fail: dob is missing
    assert statuses(out) == ["error", "ok"], out
    assert "message" in out["trace"][0], "error entries carry a message"
    assert out["tags"] == ["done"], "later steps still run"
    assert out["destination"] == "general", "routing still happens"


def t4_on_error_quarantine_stops_and_reroutes(m):
    p = m.Pipeline(
        [
            {"kind": "normalize", "field": "dob", "on_error": "quarantine"},
            {"kind": "tag", "tag": "done"},
        ],
        routes=[{"to": "general"}],
    )
    out = p.run({"fields": {}})
    assert out["destination"] == "quarantine", out
    assert out["tags"] == [], "remaining steps do not run"
    assert statuses(out) == ["error"], out


def t4_default_policy_still_fails(m):
    p = m.Pipeline([{"kind": "normalize", "field": "dob"},
                    {"kind": "tag", "tag": "done"}])
    expect_error(m.PipelineError, lambda: p.run({"fields": {}}),
                 "default on_error is 'fail'")


# ------------------------------- registry -------------------------------------

CASES = [
    (0, r0_basic_run),
    (0, r0_require_collects_errors_without_stopping),
    (0, r0_normalize_missing_field_raises),
    (0, r0_unknown_kind_rejected_at_construction),
    (0, r0_trace_uses_step_name_when_given),
    (0, r0_input_document_is_not_mutated),

    (1, t1_default_field),
    (1, t1_rename_field_moves_the_value),
    (1, t1_rename_missing_source_is_a_noop),

    (2, t2_equals_condition_runs_or_skips),
    (2, t2_exists_condition),
    (2, t2_nested_all_any_not),
    (2, t2_unrecognized_condition_raises),

    (3, t3_first_matching_route_wins),
    (3, t3_nested_route_groups_fall_through),
    (3, t3_routes_can_use_errors_and_tags),
    (3, t3_no_matching_route_raises),
    (3, t3_route_rules_are_validated),

    (4, t4_on_error_skip_records_and_continues),
    (4, t4_on_error_quarantine_stops_and_reroutes),
    (4, t4_default_policy_still_fails),
]

LABELS = {0: "Given code (regression suite)", 1: "Task 1", 2: "Task 2",
          3: "Task 3", 4: "Task 4"}


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if a != "-v"]

    task = 0
    if len(args) > 1:
        try:
            task = int(args[1])
        except ValueError:
            print(__doc__)
            return 2
    if not 0 <= task <= 4:
        print("task must be between 0 and 4")
        return 2

    module_name = args[2] if len(args) > 2 else "pipeline"
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        print(f"could not import module '{module_name}': "
              f"{type(exc).__name__}: {exc}")
        return 2

    passed = failed = 0
    current = None
    for stage, fn in CASES:
        if stage > task:
            continue
        if stage != current:
            print(f"\n{LABELS[stage]}")
            current = stage
        try:
            fn(mod)
        except Exception as exc:
            failed += 1
            print(f"  FAIL {fn.__name__} -- {type(exc).__name__}: {exc}")
            if verbose:
                traceback.print_exc()
        else:
            passed += 1
            print(f"  ok   {fn.__name__}")

    print(f"\n{passed} passed, {failed} failed"
          f"  (through task {task}, module '{module_name}')")
    if failed and not verbose:
        print("tip: re-run with -v for full tracebacks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
