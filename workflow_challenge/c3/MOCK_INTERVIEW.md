# Mock Backend Interview — Workflow Engine

**Format:** ~1 hour, live-coding (simulate CoderPad: one plain file, no autocomplete magic, run code often).
**Language:** Python or TypeScript — your choice.
**No external libraries.** Standard library only.

> Treat this like the real thing. Don't read `SOLUTIONS.md` until you've made a genuine attempt.
> The problem is delivered in **stages**. Do **not** read ahead — in the real interview you won't
> know what's coming. Finish a stage, get it working, then reveal the next one.

---

## How to run this mock (rules of engagement)

1. Set a timer for **50 minutes** of coding + **10 minutes** of discussion.
2. Before writing code on each stage, **say your assumptions and your plan out loud** (or type them as comments). This is scored as heavily as the code.
3. Ask "clarifying questions" — the answers you'd get are in the `> Interviewer answer:` blocks. Only read the answer for a question you actually thought to ask.
4. Run your code after every stage. Working-but-simple beats clever-but-broken.
5. You will be interrupted with new requirements (that's Stages 2–5). Expect it. Structure Stage 1 so the later stages don't force a rewrite — that's the whole point of the exercise.

**What your interviewer is scoring** (straight from the guide):
- Modeling execution flow & data availability
- Clarifying assumptions about state & scope
- Clean, extensible structure (no massive rewrites as requirements grow)
- Explaining tradeoffs in data structures & control flow
- Handling edge cases confidently
- Communicating while you work

---

## The Domain

You're building a tiny **workflow engine**. A workflow is an ordered list of **steps**. Each step has a
unique `id` and an operation `op`, and it produces a single value. Later steps can consume the values
produced by earlier steps. Think of it as a mini spreadsheet / build graph / no-code automation runtime.

A step is a plain dict/object. Example:

```json
{ "id": "a", "op": "const", "value": 5 }
```

---

## Stage 1 — Execute a linear workflow

Given an ordered list of steps, execute them in order and return a mapping of `step id -> produced value`.

Only one op exists so far:
- `const` → produces its literal `"value"`.

Sample input:

```json
[
  { "id": "a", "op": "const", "value": 5 },
  { "id": "b", "op": "const", "value": 3 }
]
```

Expected output: `{ "a": 5, "b": 3 }`

**Clarifying questions you might ask:**
> **Q: Are ids guaranteed unique?**
> Interviewer answer: For now, assume yes. (This changes later — good instinct to ask.)
>
> **Q: What should the return type be?**
> Interviewer answer: A dict/map of id → value is fine.

---

## Stage 2 — Data propagation (steps reference other steps)

Steps can now consume earlier steps' outputs by referencing their `id`. New ops:
- `ref`   → `{ "id": "x", "op": "ref", "arg": "a" }` produces the value of step `a`.
- `add`   → `{ "id": "s", "op": "add", "args": ["a", "b"] }` sums referenced values.
- `sub`   → `args[0] - args[1]`
- `mul`   → product of all referenced values.

References always point to steps that appear **earlier** in the list.

Sample input (appended to Stage 1):

```json
{ "id": "sum",  "op": "add", "args": ["a", "b"] },
{ "id": "prod", "op": "mul", "args": ["a", "b", "sum"] }
```

Expected: `sum = 8`, `prod = 5 * 3 * 8 = 120`.

**Clarifying questions you might ask:**
> **Q: What if a step references an id that doesn't exist?**
> Interviewer answer: For now assume inputs are valid; we'll add validation later. But mention how you'd handle it.
>
> **Q: Can a step reference something defined *after* it?**
> Interviewer answer: No — references are always to earlier steps. (Don't over-build a topological sort yet.)

---

## Stage 3 — Conditional branching (execution flow / state machine)

Add comparison + branching. New ops:
- `gt` → `{ "op": "gt", "args": ["prod", "sum"] }` → boolean `args[0] > args[1]`
- `eq` → boolean equality
- `if` → has a `cond` (id of a boolean value), a `then` list of steps, and an optional `else` list of steps.
  Only the taken branch executes. The steps in the untaken branch must **not** run.

```json
{ "id": "big", "op": "gt", "args": ["prod", "sum"] },
{
  "id": "branch",
  "op": "if",
  "cond": "big",
  "then": [ { "id": "t", "op": "add", "args": ["prod", "sum"] } ],
  "else": [ { "id": "f", "op": "sub", "args": ["sum", "prod"] } ]
}
```

**Clarifying questions you might ask:**
> **Q: What value does the `if` step itself produce?**
> Interviewer answer: Your call — pick something defensible and state it. (E.g. the last value produced inside the taken branch.)
>
> **Q: Do steps inside a branch become referenceable by later top-level steps?**
> Interviewer answer: Great question — that's exactly Stage 4. Make an assumption now and be ready to revise.

---

## Stage 4 — Scoping (variable visibility / nested contexts)

Steps inside a branch's `then`/`else` run in a **child scope**:
- A branch step **can** read variables from any enclosing (parent) scope.
- Variables defined **inside** a branch **do not** leak back out to the parent scope after the branch finishes.
- Branches can be nested arbitrarily deep.

So after the whole workflow runs, top-level `t`/`f` from Stage 3 should **not** appear in the top-level result map — they lived and died inside the branch scope.

**Clarifying questions you might ask:**
> **Q: If an inner step and an outer step share a name, which wins inside the branch?**
> Interviewer answer: The innermost definition shadows the outer one (lexical scoping). State your rule.
>
> **Q: What's the cleanest way to model this?**
> Interviewer answer: (You lead.) A scope object with a `parent` pointer and a `resolve()` that walks up the chain is one clean approach.

---

## Stage 5 — Static validation (traversal + derived state)

Before executing anything, write a `validate(steps)` that walks the entire (possibly nested) structure and
returns a **list of all problems** (not just the first). Detect:
1. A reference/`cond` pointing at a name that isn't in scope at that point.
2. Duplicate step ids within the same scope.
3. (Stretch) A branch step referencing a name that only exists in a *sibling* branch — i.e. respect scope during validation.

Return an empty list when the workflow is clean.

**Clarifying questions you might ask:**
> **Q: Should validation stop at the first error or collect them all?**
> Interviewer answer: Collect them all — more useful to the user.
>
> **Q: Should validation and execution share the traversal logic?**
> Interviewer answer: Discuss the tradeoff. Sharing avoids drift; separate passes are simpler to reason about.

---

## Stretch goals (only if time remains — likely the "10 min discussion")

- **Cycle / forward-reference detection** if references were allowed to point anywhere.
- A `loop`/`foreach` op that runs a sub-block N times with an injected loop variable.
- Lazy evaluation: only compute a step if something downstream actually needs it.
- How would you make ops **pluggable** so adding an op requires zero changes to the executor?

---

When you're done (or stuck for 5+ minutes), open `SOLUTIONS.md` and compare. `reference_solution.py`
is a complete, runnable implementation — run `python3 reference_solution.py`.
