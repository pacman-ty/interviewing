# Workflow Engine — Tennr Backend Interview Practice

This challenge mirrors the shape of the interview described in the prep guide: a **workflow-style system**, real working Python, no external libraries, and a problem that **evolves in stages** — each stage introduces a new structural concept (execution flow → data propagation → dependency graphs → scoped data → conditionals → iteration), the way an interviewer layers on requirements.

## Files

- `challenge.py` — your starter file. All your code goes here.
- `tests.py` — stage-gated tests. `python tests.py 3` runs everything for Stages 1–3.
- `solution.py` — a reference implementation. **Don't open it until you've genuinely attempted the stages.** Verify it with `python tests.py 6 solution`.

## How to practice (simulate the real hour)

1. **Read only one stage at a time.** Don't peek ahead — the interview reveals requirements incrementally, and extending your design without a rewrite is exactly what's being evaluated.
2. **Before coding each stage, talk out loud**: state your assumptions, and ask 1–2 clarifying questions (prompts included below — in the real interview, actually ask them).
3. **Timebox it** roughly like the real thing: Stages 1–2 ≈ 15 min, Stage 3 ≈ 10, Stage 4 ≈ 20, Stage 5 ≈ 10. Stage 6 is a stretch goal.
4. **Run `python tests.py <stage>` after each stage** and keep earlier stages green. Regressions while refactoring are the classic failure mode.
5. Start simple. Don't optimize prematurely — narrate the tradeoff instead ("I'll do the O(n²) version first; here's what I'd change for scale").

---

## The system

You're building the execution engine at the core of an automation platform — the thing that takes a workflow definition (plain Python dicts, JSON-shaped) and runs it.

```python
workflow = {"steps": [ <node>, <node>, ... ]}
```

The basic node is a **step**:

```python
{"id": "total", "op": "add", "inputs": {"values": [1, 2, 3]}}
```

`op` names a function in the provided `OPS` registry (see `challenge.py`): `const`, `add`, `concat`, `upper`, `length`, `get`, `gt`, `eq`. Each op takes the resolved `inputs` dict and returns a value.

You implement one entry point:

```python
run_workflow(workflow)  # -> {node_id: output} for every top-level node that ran
```

Raise `WorkflowError` for anything invalid.

---

## Stage 1 — Run a linear workflow

**Requirements**

- Execute steps top-to-bottom in the listed order. Inputs are plain literals.
- Look up each step's `op` in `OPS`, call it with `inputs`, record the result under the step's `id`.
- Return `{id: output}` for every step.
- Raise `WorkflowError` for an unknown op or duplicate ids.

**Example**

```python
{"steps": [
    {"id": "greeting", "op": "const", "inputs": {"value": "hello"}},
    {"id": "total",    "op": "add",   "inputs": {"values": [1, 2, 3]}},
]}
# -> {"greeting": "hello", "total": 6}
```

**Worth clarifying out loud:** What happens with an empty workflow? Should the result include every step's output or only "final" ones? Can outputs be any type?

---

## Stage 2 — Data propagation with references

**New requirement:** an input value may now be a **reference** — a dict with exactly one key:

```python
{"$ref": "<step_id>"}
```

At execution time, replace it with that step's output.

- References can appear **anywhere** inside inputs: as a top-level input value, inside lists, inside dict literals — resolution is recursive.
- A ref must point to a step that has **already executed** (i.e., earlier in the list). Unknown id or not-yet-run → `WorkflowError`. *(This ordering rule gets replaced in Stage 3 — that's intentional.)*

**Example**

```python
{"steps": [
    {"id": "name",  "op": "const",  "inputs": {"value": "tennr"}},
    {"id": "loud",  "op": "upper",  "inputs": {"value": {"$ref": "name"}}},
    {"id": "cheer", "op": "concat", "inputs": {"values": [{"$ref": "loud"}, "!"]}},
]}
# -> {"name": "tennr", "loud": "TENNR", "cheer": "TENNR!"}
```

**Edge cases:** a ref buried two levels deep in a literal dict; a list mixing refs and literals; telling a reference apart from a literal dict (exactly one key, `"$ref"`).

**Design note to narrate:** a small recursive `resolve(value)` helper keeps step execution clean — and it will get reused constantly in later stages.

---

## Stage 3 — Steps arrive in any order

**New requirement (replaces Stage 2's ordering rule):** workflows now list steps in **arbitrary order**. The engine must figure out a valid execution order itself.

- Derive dependencies from the `$ref`s. Execute so that every reference is satisfied when it's needed.
- A cycle (including a self-reference) → `WorkflowError`.
- A ref to an id that exists nowhere → `WorkflowError`.

**Tradeoff to be ready to defend:** topological sort up front vs. lazy recursive evaluation with memoization and a "currently visiting" set for cycle detection. Both are legitimate — talk about validation timing, error message quality, and which one parallelizes later.

**Edge cases:** self-reference; diamond dependencies (`a` feeds `b` and `c`, both feed `d`).

---

## Stage 4 — Groups and scope

**New node type:**

```python
{"id": "calc", "type": "group",
 "steps": [ ...nodes... ],
 "exports": {"$ref": "some_inner_step"}}
```

(Nodes without a `"type"` are plain steps.)

**Requirements**

- A group runs its own steps; Stage 3 ordering applies among the siblings *inside* it.
- **Scoping is lexical.** A ref inside a group resolves against the group's own steps first, then the enclosing scope, outward to the top level. Inner ids may **shadow** outer ids.
- The group's output is its resolved `exports` — any input-like value, often a dict of refs. Siblings reference the group by its id.
- Inner ids are **not visible outside** the group. Referencing one from outside → `WorkflowError`.
- Ordering crosses the boundary: a group runs after any outer sibling its contents reference, and siblings that reference the group run after it.

**Example**

```python
{"steps": [
    {"id": "base", "op": "const", "inputs": {"value": 10}},
    {"id": "calc", "type": "group",
     "steps": [
         {"id": "doubled", "op": "add",
          "inputs": {"values": [{"$ref": "base"}, {"$ref": "base"}]}},
     ],
     "exports": {"$ref": "doubled"}},
    {"id": "total", "op": "add", "inputs": {"values": [{"$ref": "calc"}, 5]}},
]}
# -> {"base": 10, "calc": 20, "total": 25}   (note: no "doubled" key)
```

**Edge cases:** shadowing; groups nested inside groups; a group *listed before* the top-level sibling it depends on.

**Design note to narrate:** a `Scope` object with a parent pointer (a scope chain) maps directly onto how you'd explain variable scope, and makes nesting free. Flattening ids with prefixes also works — say why you chose yours.

---

## Stage 5 — Conditional execution

**New requirement:** any node may carry a condition:

```python
{"id": "award", "op": "const", "inputs": {"value": "approved"},
 "when": {"$ref": "passed"}}
```

- `when` is an input-like value (literal or ref), resolved in the node's enclosing scope. **Falsy → the node is skipped**: it produces no output and is absent from the results.
- **Skips cascade:** a node whose inputs (or `when`) reference a skipped node is itself skipped — not an error.
- Skipping a group skips everything inside it.
- Conditions are usually computed by earlier steps using the comparison ops (`gt`, `eq`).

**Open design question — pick a rule and defend it, like you would live:** what should a group's `exports` do if they reference a skipped inner step? Error? Resolve to `None`? Drop the key? The reference solution resolves them to `None`; reasonable people differ. The win is stating your rule *before* coding it.

---

## Stage 6 (stretch) — Map over a list

**New node type:**

```python
{"id": "doubled", "type": "map",
 "items": {"$ref": "nums"},        # must resolve to a list
 "steps": [
     {"id": "twice", "op": "add",
      "inputs": {"values": [{"$ref": "item"}, {"$ref": "item"}]}},
 ],
 "exports": {"$ref": "twice"}}
```

- For each element of `items`: run the child steps in a **fresh scope** (chained to the enclosing one) where `item` is bound — referencable as `{"$ref": "item"}`.
- The map's output is the list of resolved `exports`, in item order. Empty list → `[]`. Non-list `items` → `WorkflowError`.

If Stage 4 was built cleanly, this stage is mostly reuse — which is the point. If it forces a rewrite, that's useful information about the Stage 4 design.

---

## The last 10 minutes (discussion prompts)

Practice answering these out loud — this simulates the wrap-up conversation:

- How would you run independent steps **in parallel**? What in your design already supports that, and what breaks?
- Where would you add **validation before executing anything** (unknown refs, cycles, unknown ops), and what's the tradeoff vs. failing at runtime?
- How would you **persist and resume** a half-finished run?
- Retries and idempotency: which ops are safe to re-run?
- What's the **complexity** of your ordering approach?
- If a new node type landed tomorrow, how many places in your code does it touch? One is great; five is a smell.

## How this maps to what they say they evaluate

Execution flow and data availability → Stages 1–3. Modeling scoped data ("what's available where and why") → Stage 4. Anticipating edge cases → Stage 5's skip semantics and every error case. Extensible structure → whether Stages 4 and 6 slotted into your design or forced rewrites. And the communication half of the rubric is the parts you say out loud: clarifying questions early, assumptions stated before coding, starting simple and iterating.
