# Solutions & Thought Process

Read this **after** attempting `MOCK_INTERVIEW.md`. The full runnable engine is in
`reference_solution.py` (`python3 reference_solution.py`). Below is the reasoning stage by stage —
the *how you think* matters more to the interviewer than the final code.

---

## Meta: how to behave in the room

The guide is unusually explicit about what they want. Map your behavior to it:

| What they score | What to actually do |
|---|---|
| Clarify assumptions early | Before Stage 1 code: "I'll assume ids are unique, references point backward, and I return id→value. Sound right?" |
| Model execution flow & data availability | Narrate: "Each step produces one value that later steps can read. So I need a store keyed by id." |
| Extensible structure | Use an **op dispatch table** and a **single recursive block executor** from the start. |
| Tradeoffs | Say them out loud: dict vs list, single traversal vs two passes, eager vs lazy. |
| Edge cases | Missing refs, empty branches, duplicate ids, shadowing. |
| Iterate, don't one-shot | Start with the dumbest correct thing; refactor when Stage 3 forces structure. |

**Biggest trap:** hardcoding an `if/elif` chain for ops and inlining execution so that Stage 3's nested
branches force a rewrite. The move that prevents rewrites: from Stage 1, make execution a function that
takes *a list of steps and a scope*, so nested blocks are just a recursive call with a child scope.

---

## Stage 1 — Linear execution

**Reasoning:** A workflow is an ordered list; execution is a fold over it accumulating an id→value store.
Simplest correct thing:

```python
def run(steps):
    store = {}
    for step in steps:
        if step["op"] == "const":
            store[step["id"]] = step["value"]
    return store
```

**Say this:** "I'm keeping a `store` dict. Even though only `const` exists, I'll route through a
per-op handler so adding ops later doesn't bloat this loop." That single sentence signals extensibility.

---

## Stage 2 — Data propagation

**Reasoning:** "Consuming an earlier output" = look up ids in the store. Introduce a `resolve(name)`
indirection now, because Stage 4 (scoping) will change *how* resolution works but not the call sites.

Refactor the op handling into a **dispatch table** so the executor never grows a giant `if` chain:

```python
BINARY_OPS = {
    "add": lambda a: sum(a),
    "sub": lambda a: a[0] - a[1],
    "mul": lambda a: math.prod(a),   # or a manual loop; no imports needed
}
```

Executor branch:

```python
elif op in BINARY_OPS:
    resolved = [resolve(x) for x in step["args"]]
    value = BINARY_OPS[op](resolved)
```

**Tradeoff to mention:** references point backward, so plain in-order execution works and I *don't*
need a topological sort. If forward refs were allowed, I'd build a dependency graph and topo-sort (or
evaluate lazily), and detect cycles. Don't build that now — that's premature optimization, which the
guide explicitly warns against.

**Edge case to mention:** unknown reference → right now inputs are trusted, but I'd raise a clear
`KeyError`/custom error; Stage 5 makes this a first-class validation.

---

## Stage 3 — Conditional branching

**Reasoning:** This is where naive code breaks. An `if` step *contains more steps*. The clean model:
**a branch body is just another list of steps**, so executing it is the *same* function recursively.

```python
elif op == "if":
    cond = resolve(step["cond"])
    body = step["then"] if cond else step.get("else", [])
    exec_block(body, scope)          # recursion — same executor
    value = trace[-1][1] if body else cond
```

Key decisions to state:
- **Only the taken branch runs.** The untaken branch is never touched — that's the execution-flow /
  state-machine point they care about.
- **The `if` step's own value** — I chose "last value produced in the taken branch." Any defensible
  choice is fine *if you say why*.

If you kept execution inline instead of as a reusable `exec_block(steps, scope)`, this is the moment
you'd be forced to rewrite. Point out that you set it up in Stage 1 precisely to avoid that.

---

## Stage 4 — Scoping

**Reasoning:** "Inner definitions don't leak out; inner can read outer" is textbook **lexical scope**.
Model it with a `Scope` object holding a `parent` pointer:

```python
class Scope:
    def __init__(self, parent=None):
        self.parent, self.vars = parent, {}
    def define(self, name, value):
        self.vars[name] = value
    def resolve(self, name):
        s = self
        while s:
            if name in s.vars: return s.vars[name]
            s = s.parent
        raise KeyError(name)
```

Now the `if` handler creates a **child scope** for the branch body:

```python
child = Scope(parent=scope)
exec_block(body, child)   # child sees parent vars; parent never sees child's
```

- **Shadowing** falls out for free: `resolve` walks from innermost outward, so an inner `x` hides an
  outer `x`.
- **Non-leakage** falls out for free: the child scope is discarded when the branch returns, so `t`/`f`
  never appear in the top-level result. That's why `run()` returns only the *root* scope's vars.

This is the elegant payoff: because Stage 2 routed everything through `resolve()` and Stage 3 made
execution recursive over a scope, Stage 4 is ~10 lines and **zero** changes to existing op handlers.
Call that out — extensibility under evolving requirements is the entire rubric.

---

## Stage 5 — Static validation

**Reasoning:** Same tree walk as execution, but instead of *computing* values you track *which names
are defined* at each point and flag references to undefined names. Collect all errors, don't throw on
the first.

```python
def validate(steps):
    errors = []
    def walk(block, defined_outer):
        defined = set(defined_outer)          # copy: this scope's view
        for step in block:
            refs = refs_of(step)              # arg/args/cond → list of names
            for r in refs:
                if r not in defined:
                    errors.append(f"{step['id']}: {r} not in scope")
            if step["op"] == "if":
                walk(step.get("then", []), defined)   # child scope
                walk(step.get("else", []), defined)
            if step["id"] in defined:
                errors.append(f"duplicate id {step['id']}")
            defined.add(step["id"])
        return defined
    walk(steps, set())
    return errors
```

Scope handling mirrors execution: each branch validates against a *copy* of the parent's defined set,
so names defined in `then` are invisible in `else` and to later top-level steps — catching the
"reference something that only exists in a sibling branch" bug.

**Tradeoff to discuss (the 10-min chat):** execution and validation duplicate the traversal. You could
unify them into one visitor to avoid drift, at the cost of a more abstract codebase. Two passes are
simpler and independently testable. Either answer is fine — the interviewer wants to hear you *weigh*
it.

---

## What "great" looks like vs "just okay"

- **Okay:** working code, `if/elif` chain for ops, execution inlined, scoping bolted on with a stack of dicts.
- **Great:** op dispatch table + recursive `exec_block(steps, scope)` + a `Scope` with parent chaining,
  introduced *incrementally* with each step justified by a stated assumption, and tradeoffs (topo-sort,
  eager vs lazy, unified vs separate validation) named even when you choose *not* to build them.

## Likely follow-up questions (prep answers)

- *"How would you support forward references?"* → Build a dependency graph, topologically sort, detect
  cycles (DFS with a visiting/visited coloring). Or evaluate lazily and memoize, detecting cycles via a
  "currently-resolving" set.
- *"Add a `loop` op."* → Same recursion as `if`: run the body block in a child scope N times, injecting
  the loop index/item as a defined var in that child scope. No executor changes beyond one handler.
- *"Make ops pluggable."* → Register handlers in a dict (or decorator registry); the executor just does
  `HANDLERS[op](step, scope, resolve)`. Adding an op = adding a function, never editing the executor.
- *"How do you test this?"* → Table-driven tests: (workflow, expected store) pairs, plus validation
  cases with expected error lists. Each stage's sample is already a test case.

## TypeScript note

If you pick TypeScript: model a `Step` union type discriminated on `op`, a `Scope` class identical to
the Python one, and a `Record<string, unknown>` store. The structure is 1:1 — the recursion, dispatch
table, and parent-chained scope all translate directly.
