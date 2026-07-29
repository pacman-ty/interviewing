# Intake Pipeline — Integration Round (Tennr Interview Practice #2)

Round 1 had you build an engine from scratch. This round practices the other common interview shape — and the one their guide emphasizes most: **you receive working code, and requirements keep arriving.** The skills being tested shift toward reading unfamiliar code quickly, finding the extension points, and integrating changes **without breaking existing behavior**.

The domain is deliberately Tennr-flavored: an intake pipeline that processes incoming documents (think faxed referrals) through configurable steps.

## Files

- `pipeline.py` — the **given, working codebase**. This is the file you edit.
- `pipeline_tests.py` — task-gated tests. Task 0 is the **regression suite** for the given code.
- `pipeline_solution.py` — the given code with all four tasks integrated. **Don't open it until you've attempted the tasks.** Afterward, `diff pipeline.py pipeline_solution.py` is a great study tool.

## How to practice

1. **First command, before touching anything:**

   ```
   python pipeline_tests.py 0
   ```

   Everything passes. That suite is your safety net — it must *stay* green through every task. Breaking a regression while adding a feature is the classic failure mode this round is designed to expose.

2. **Spend ~8 minutes reading the code before writing any.** Use this ritual, out loud (interviewers often literally open with "walk me through what this code does"):
   - Find the entry point (`Pipeline.run`) and trace one document through it mentally.
   - Name the data shapes: a step config, the `Context`, the result dict.
   - Find the extension mechanism (`@register` + `PROCESSORS`).
   - Note assumptions that might not survive new requirements — e.g., *every step always runs*, and the trace only ever says `"ok"`.
   - Finish with a 30-second spoken summary.

3. Do the tasks in order; after each one run `python pipeline_tests.py <n>` (which includes the regression suite and all earlier tasks).

4. Timebox: reading ≈ 8 min, Task 1 ≈ 7, Task 2 ≈ 15, Task 3 ≈ 20, Task 4 ≈ 10.

## The given system (what you should extract from reading)

A document looks like:

```python
{"id": "doc-1", "source": "fax", "fields": {"patient_name": "jane doe", ...}}
```

A pipeline is an ordered list of step configs, each naming a registered processor by `"kind"`:

```python
Pipeline([
    {"kind": "normalize", "field": "patient_name", "mode": "title"},
    {"kind": "require", "fields": ["patient_name", "dob"]},
    {"kind": "tag", "tag": "intake"},
]).run(doc)
```

`run()` deep-copies the document, applies each step, and returns `{"doc", "errors", "tags", "trace"}`. Registered processors: `set_field`, `normalize` (raises `PipelineError` on a missing field — remember that, it matters in Task 4), `require` (accumulates errors, never stops the run), `tag`.

---

## Task 1 — Follow the pattern (warm-up)

Add two processors by following the existing registry pattern:

- **`default_field`** — `{"kind": "default_field", "field": F, "value": V}`: set `F` to `V` only if it's currently missing **or empty string** (same "empty counts as missing" convention `require` uses).
- **`rename_field`** — `{"kind": "rename_field", "from": A, "to": B}`: move the value from `A` to `B`, removing `A`. If `A` is absent, do nothing — no error.

**Worth clarifying out loud:** should rename overwrite an existing `to` field? (Tests don't pin this down — state your assumption.) Purely additive: if you touched `Pipeline.run` for this task, reconsider.

---

## Task 2 — Conditional steps

Any step may now carry a `"when"` condition, evaluated against the current state of the run:

```python
{"kind": "tag", "tag": "urgent", "when": {"field": "priority", "equals": "stat"}}
```

**Condition grammar** (recursive — this is the tree-traversal muscle):

- `{"field": F, "equals": V}` — field value equals `V`
- `{"field": F, "exists": true|false}` — *presence*, not truthiness: an empty string still exists
- `{"all": [conds]}`, `{"any": [conds]}`, `{"not": cond}`
- An unrecognized condition shape → `PipelineError`

**Behavior:** falsy condition → the step is **skipped**: the processor never runs, and the trace records `{"step": <name>, "status": "skipped"}`.

**Integration questions to narrate:**
- Where does evaluation live — inside each processor, inside `Pipeline.run`, or in a standalone `evaluate_condition(cond, ...)` function? (One of these makes Task 3 nearly free.)
- What does the evaluator need access to — just the document's fields, or more of the run's state? Choose the signature carefully; Task 3 will judge it.

---

## Task 3 — Routing rules

After the steps finish, the document must be routed to a destination. Extend the constructor — **backward compatibly**:

```python
Pipeline(steps, routes=[
    {"when": {"field": "source", "equals": "fax"},
     "routes": [                                  # nested group
         {"when": {"has_tag": "urgent"}, "to": "fax-priority"},
         {"when": {"field": "state", "equals": "NY"}, "to": "fax-ny"},
     ]},
    {"when": {"has_errors": True}, "to": "manual-review"},
    {"to": "general"},                            # no "when" = always matches
])
```

**Requirements**

- Each rule has a `"when"` (optional — absent means always matches) and **exactly one of** `"to"` (a destination string) or `"routes"` (a nested group). Validate this at construction time.
- Evaluation is **first match wins, top to bottom, depth-first**. A nested group whose condition matches but whose children all miss **falls through** to the next rule at the outer level.
- Conditions are the **same grammar as Task 2**, extended with two forms that read the run's state, not the document: `{"has_tag": T}` and `{"has_errors": true|false}`. (If your Task 2 evaluator only received `doc["fields"]`, here's your refactor — that friction is the lesson, not a mistake.)
- The result dict gains a `"destination"` key **only when routes are configured**. Routes configured but nothing matched → `PipelineError("no route matched")`.

---

## Task 4 — Per-step error policy

Processors can raise (you've known since reading: `normalize` on a missing field). Right now that exception escapes `run()` raw. Add a per-step policy:

```python
{"kind": "normalize", "field": "dob", "on_error": "skip"}
```

- **`"fail"`** (the default) — the exception propagates, exactly as today. The regression suite is watching.
- **`"skip"`** — record `{"step": <name>, "status": "error", "message": <str(exc)>}` in the trace and continue with the next step.
- **`"quarantine"`** — record the error entry, run **no further steps**, and set `"destination"` to `"quarantine"` — bypassing the routing table entirely, and even when no routes are configured.
- Unknown policy value → `PipelineError` at construction time.

**Design point to narrate:** after this task, `Pipeline.run` is the single owner of a step's lifecycle — skipped / ok / error — and processors know nothing about conditions or error policy. If your processors are catching their own exceptions or checking their own `when`, the responsibilities have leaked.

---

## The last 10 minutes (discussion prompts)

- What in the *given* code would you refactor if you owned it? (The module-global `PROCESSORS` registry? The result dict vs. a result class? `apply(ctx, config)` receiving the raw step dict?)
- How would you unit-test a single processor in isolation, without building a `Pipeline`?
- Two pipelines run concurrently on different documents — is anything shared that shouldn't be?
- Is re-running a document through the pipeline safe? Which of your processors are idempotent?
- Where would schema validation of step configs belong — construction time or run time — and what did you actually choose task by task?
- 10,000 documents arrive at once. What changes first?

## What this round trains, mapped to their guide

Extending an initial solution as constraints are introduced → all four tasks. Refactoring thoughtfully as requirements evolve → the Task 2→3 evaluator-signature squeeze, and the run-loop restructuring in Tasks 2 and 4. Modeling scoped data and traversal → the recursive condition grammar and nested routes. Clean, extensible structure → whether each task landed in one place or leaked across five. And keeping the regression suite green the whole way is the habit that reads as "reliable, structured code" in the room.
